"""Simple in-memory rate limiter per user (by user id)."""
import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException

# (user_id, key) -> list of timestamps in window
_store: defaultdict[str, list[float]] = defaultdict(list)


def check_rate_limit(
    user_id: str,
    key: str,
    max_per_window: int,
    window_seconds: float = 60,
) -> None:
    """Raise 429 if user has exceeded max_per_window requests in the last window_seconds."""
    now = time.monotonic()
    cutoff = now - window_seconds
    k = f"{user_id}:{key}"
    _store[k] = [t for t in _store[k] if t > cutoff]
    if len(_store[k]) >= max_per_window:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again in a minute.",
        )
    _store[k].append(now)
