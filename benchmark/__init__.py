"""SSE performance benchmarking: encryption, token generation, index update, search latency."""

from .benchmark import run_benchmark, BENCHMARK_COUNTS

__all__ = ["run_benchmark", "BENCHMARK_COUNTS"]
