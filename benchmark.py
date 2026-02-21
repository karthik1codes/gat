#!/usr/bin/env python3
"""
Benchmark SSE: encryption time, index build time, search latency, index growth.
Runs for 100, 1000, 5000 documents; writes results to benchmark_results.csv.
"""

import csv
import os
import sys
import tempfile
import time
from pathlib import Path

# Project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crypto import generate_key, encrypt_document, build_trapdoor
from client import SSEClient
from server import SSEServer

# Document counts (spec: 100, 1000, 5000); single doc size for comparable index growth
DOC_SIZE_BYTES = 500
COUNTS = (100, 1000, 5000)


def _random_doc(size: int, doc_id: int) -> bytes:
    """Synthetic document: repeated words so we have keywords to search."""
    words = ["alpha", "beta", "gamma", "delta", "invoice", "confidential", "report", "data"]
    line = " ".join(words * 3) + "\n"
    n = max(1, size // len(line))
    return (line * n)[:size].encode("utf-8")


def _run_one(count: int, doc_size: int, use_sqlite: bool) -> dict:
    key = generate_key()
    with tempfile.TemporaryDirectory() as tmp:
        storage = Path(tmp) / "store"
        server = SSEServer(storage_dir=storage, use_sqlite_index=use_sqlite)
        client = SSEClient(master_key=key, server=server)
        docs = [(f"doc_{i}", _random_doc(doc_size, i)) for i in range(count)]

        # Encryption + upload time
        t0 = time.perf_counter()
        client.upload_documents(docs)
        t_upload = time.perf_counter() - t0

        # Index size (approximate: count of index entries)
        if use_sqlite:
            index_path = storage / "index.db"
            index_size = index_path.stat().st_size if index_path.exists() else 0
        else:
            index_path = storage / "index.json"
            index_size = index_path.stat().st_size if index_path.exists() else 0

        # Search latency (single keyword, average over 10 runs)
        search_times = []
        for _ in range(10):
            t0 = time.perf_counter()
            client.search("invoice")
            search_times.append(time.perf_counter() - t0)
        t_search = sum(search_times) / len(search_times)

        server.close()
        return {
            "num_docs": count,
            "doc_size_bytes": doc_size,
            "use_sqlite": use_sqlite,
            "upload_sec": round(t_upload, 4),
            "search_latency_sec": round(t_search, 6),
            "index_size_bytes": index_size,
        }


def main() -> None:
    out_path = Path(__file__).parent / "benchmark_results.csv"
    rows = []
    for count in COUNTS:
        for use_sqlite in (False, True):
            name = f"n={count} size={DOC_SIZE_BYTES} sqlite={use_sqlite}"
            print(f"Running {name}...", flush=True)
            try:
                row = _run_one(count, DOC_SIZE_BYTES, use_sqlite)
                rows.append(row)
            except Exception as e:
                print(f"  Error: {e}", flush=True)
                rows.append({
                        "num_docs": count,
                        "doc_size_bytes": DOC_SIZE_BYTES,
                        "use_sqlite": use_sqlite,
                        "upload_sec": -1,
                        "search_latency_sec": -1,
                        "index_size_bytes": -1,
                    "error": str(e),
                })
    fieldnames = ["num_docs", "doc_size_bytes", "use_sqlite", "upload_sec", "search_latency_sec", "index_size_bytes"]
    if any("error" in r for r in rows):
        fieldnames.append("error")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
