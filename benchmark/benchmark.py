"""
SSE performance benchmarking module.

Measures: file encryption time, token generation time, index update time,
search latency, index size growth. Uses isolated test data; does not touch
production index or storage.
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


def run_benchmark(
    counts: tuple[int, ...] = BENCHMARK_COUNTS,
    doc_size: int = DOC_SIZE_BYTES,
    use_sqlite: bool = True,
    csv_path: Path | None = None,
) -> Dict[str, Any]:
    """
    Run benchmark in an isolated temp directory. Never corrupts production index.
    Returns metrics suitable for JSON (e.g. frontend graph rendering).
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
                # Upload (encryption + index update) time
                t0 = time.perf_counter()
                client.upload_documents(docs)
                row["upload_sec"] = round(time.perf_counter() - t0, 4)

                # Token generation time (sample: 100 tokens)
                t0 = time.perf_counter()
                for i in range(100):
                    build_trapdoor(f"keyword_{i % 10}", key)
                row["token_gen_100_sec"] = round(time.perf_counter() - t0, 6)

                # Index size
                if use_sqlite:
                    idx_path = storage / "index.db"
                else:
                    idx_path = storage / "index.json"
                row["index_size_bytes"] = idx_path.stat().st_size if idx_path.exists() else 0

                # Search latency (average over 10 runs)
                search_times = []
                for _ in range(10):
                    t0 = time.perf_counter()
                    client.search("invoice")
                    search_times.append(time.perf_counter() - t0)
                row["search_latency_sec"] = round(sum(search_times) / len(search_times), 6)
            except Exception as e:
                row["error"] = str(e)
                row.setdefault("upload_sec", -1)
                row.setdefault("token_gen_100_sec", -1)
                row.setdefault("index_size_bytes", -1)
                row.setdefault("search_latency_sec", -1)
            results.append(row)

        server.close()

    out: Dict[str, Any] = {
        "benchmark_results": results,
        "dataset_sizes": list(counts),
        "doc_size_bytes": doc_size,
    }
    if csv_path:
        fieldnames = ["num_docs", "doc_size_bytes", "use_sqlite", "upload_sec", "token_gen_100_sec", "search_latency_sec", "index_size_bytes"]
        if any("error" in r for r in results):
            fieldnames.append("error")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(results)
    return out
