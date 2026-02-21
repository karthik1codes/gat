"""
Benchmark API: run SSE performance benchmark in isolation.
Does not touch production index or user data.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import APIRouter, Depends

from ..routes.auth import get_current_user_id
from ..models import User

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])


@router.post("/run")
def run_benchmark_endpoint(user: User = Depends(get_current_user_id)):
    """
    Run performance benchmark with isolated test data (100, 1000, 5000 documents).
    Does not corrupt production index; uses temp directory only.
    Returns metrics JSON for frontend graph rendering.
    """
    from benchmark.benchmark import run_benchmark, BENCHMARK_COUNTS
    result = run_benchmark(counts=BENCHMARK_COUNTS, use_sqlite=True)
    return result
