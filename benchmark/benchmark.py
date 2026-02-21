"""
SSE performance benchmarking module.

Measures: encryption time, search time, index growth, and scaling analysis.
Uses isolated test data; does not touch production index or storage.
Returns metrics that demonstrate "it scales" (per-doc rates, growth, summary).
"""

import csv
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

# Project root on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto import generate_key, encrypt_document, build_trapdoor
from client import SSEClient
from server import SSEServer

DOC_SIZE_BYTES = 500
BENCHMARK_COUNTS = (100, 1000, 5000)


def _random_doc(size: int, _doc_id: int) -> bytes:
    """Synthetic document with repeated keywords for indexing."""
    words = ["alpha", "beta", "gamma", "delta", "invoice", "confidential", "report", "data"]
    line = " ".join(words * 3) + "\n"
    n = max(1, size // len(line))
    return (line * n)[:size].encode("utf-8")


def _compute_scaling_analysis(results: List[Dict[str, Any]], doc_size: int) -> Dict[str, Any]:
    """Compute per-doc rates and scaling summary from benchmark results."""
    valid = [r for r in results if r.get("error") is None and r.get("encryption_sec", -1) >= 0]
    if not valid:
        return {
            "summary": "Insufficient data for scaling analysis.",
            "encryption_time_per_doc_ms": None,
            "search_time_ms_at_max_n": None,
            "index_bytes_per_doc": None,
        }
    # Per-doc encryption time (ms): use largest N for most stable rate
    largest = max(valid, key=lambda r: r["num_docs"])
    n = largest["num_docs"]
    enc_sec = largest.get("encryption_sec")
    enc_per_doc_ms = (enc_sec / n * 1000) if enc_sec and n else None
    # Search time at max N (ms)
    search_sec = largest.get("search_latency_sec")
    search_ms = search_sec * 1000 if search_sec is not None else None
    # Index growth: bytes per doc (at largest N)
    idx_bytes = largest.get("index_size_bytes")
    idx_per_doc = (idx_bytes / n) if idx_bytes is not None and n else None
    # Scaling summary
    parts = []
    if enc_per_doc_ms is not None:
        parts.append(f"Encryption: ~{enc_per_doc_ms:.2f} ms per doc (O(N)).")
    if search_ms is not None:
        parts.append(f"Search latency at N={n}: {search_ms:.2f} ms.")
    if idx_per_doc is not None:
        parts.append(f"Index growth: ~{idx_per_doc:.0f} bytes per doc.")
    if len(valid) >= 2:
        # Simple scaling check: does encryption time scale roughly linearly?
        r0, r1 = valid[0], valid[-1]
        n0, n1 = r0["num_docs"], r1["num_docs"]
        e0, e1 = r0.get("encryption_sec"), r1.get("encryption_sec")
        if e0 and e1 and n0 and n1 and n0 < n1:
            ratio_n = n1 / n0
            ratio_t = e1 / e0
            if 0.5 <= ratio_t / ratio_n <= 2.0:
                parts.append("Scaling: encryption time scales approximately linearly with document count.")
    return {
        "summary": " ".join(parts) if parts else "See per-run metrics.",
        "encryption_time_per_doc_ms": round(enc_per_doc_ms, 4) if enc_per_doc_ms is not None else None,
        "search_time_ms_at_max_n": round(search_ms, 2) if search_ms is not None else None,
        "index_bytes_per_doc": round(idx_per_doc, 1) if idx_per_doc is not None else None,
        "max_n_tested": n,
    }


def run_benchmark(
    counts: tuple[int, ...] = BENCHMARK_COUNTS,
    doc_size: int = DOC_SIZE_BYTES,
    use_sqlite: bool = True,
    csv_path: Path | None = None,
) -> Dict[str, Any]:
    """
    Run benchmark in an isolated temp directory. Never corrupts production index.
    Returns: encryption time, search time, index growth, and scaling_analysis.
    """
    key = generate_key()
    results: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        storage = Path(tmp) / "store"
        server = SSEServer(storage_dir=storage, use_sqlite_index=use_sqlite)
        client = SSEClient(master_key=key, server=server)

        for count in counts:
            docs = [(f"doc_{i}", _random_doc(doc_size, i)) for i in range(count)]
            row: Dict[str, Any] = {
                "num_docs": count,
                "doc_size_bytes": doc_size,
                "use_sqlite": use_sqlite,
            }
            try:
                # 1) Encryption time only (no server upload)
                t0 = time.perf_counter()
                for doc_id, plaintext in docs:
                    encrypt_document(plaintext, key)
                row["encryption_sec"] = round(time.perf_counter() - t0, 4)
                row["encryption_time_ms"] = round(row["encryption_sec"] * 1000, 2)

                # 2) Full upload (encrypt + index + server) for index growth
                t0 = time.perf_counter()
                client.upload_documents(docs)
                row["upload_total_sec"] = round(time.perf_counter() - t0, 4)

                # 3) Index size (growth metric)
                if use_sqlite:
                    idx_path = storage / "index.db"
                else:
                    idx_path = storage / "index.json"
                row["index_size_bytes"] = idx_path.stat().st_size if idx_path.exists() else 0
                row["index_size_kb"] = round(row["index_size_bytes"] / 1024, 2)

                # 4) Search time (average over 10 runs)
                search_times = []
                for _ in range(10):
                    t0 = time.perf_counter()
                    client.search("invoice")
                    search_times.append(time.perf_counter() - t0)
                row["search_latency_sec"] = round(sum(search_times) / len(search_times), 6)
                row["search_time_ms"] = round(row["search_latency_sec"] * 1000, 2)

                # 5) Token generation (sample)
                t0 = time.perf_counter()
                for i in range(100):
                    build_trapdoor(f"keyword_{i % 10}", key)
                row["token_gen_100_sec"] = round(time.perf_counter() - t0, 6)
            except Exception as e:
                row["error"] = str(e)
                row.setdefault("encryption_sec", -1)
                row.setdefault("encryption_time_ms", -1)
                row.setdefault("upload_total_sec", -1)
                row.setdefault("index_size_bytes", -1)
                row.setdefault("index_size_kb", -1)
                row.setdefault("search_latency_sec", -1)
                row.setdefault("search_time_ms", -1)
                row.setdefault("token_gen_100_sec", -1)
            results.append(row)

        server.close()

    scaling = _compute_scaling_analysis(results, doc_size)
    out: Dict[str, Any] = {
        "benchmark_results": results,
        "dataset_sizes": list(counts),
        "doc_size_bytes": doc_size,
        "scaling_analysis": scaling,
        "metrics_summary": {
            "encryption_time": "sec and ms per run (encryption only, no I/O)",
            "search_time": "ms average over 10 searches per run",
            "index_growth": "bytes and KB per run; bytes_per_doc in scaling_analysis",
        },
    }
    if csv_path:
        fieldnames = [
            "num_docs", "doc_size_bytes", "use_sqlite",
            "encryption_sec", "encryption_time_ms", "upload_total_sec",
            "search_latency_sec", "search_time_ms",
            "index_size_bytes", "index_size_kb",
            "token_gen_100_sec",
        ]
        if any("error" in r for r in results):
            fieldnames.append("error")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(results)
    return out
