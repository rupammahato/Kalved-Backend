"""Lightweight per-IP per-path rate limiter for sensitive endpoints."""
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status
from app.core.config import settings

# In-memory sliding window buckets: key -> deque[timestamps]
_buckets = defaultdict(deque)


async def rate_limit(request: Request):
    if not settings.RATE_LIMIT_ENABLED:
        return True

    now = time.time()
    window = settings.RATE_LIMIT_PERIOD_SECONDS
    limit = settings.RATE_LIMIT_REQUESTS

    client = getattr(request, "client", None)
    client_ip = client.host if client and getattr(client, "host", None) else "unknown"
    key = f"{client_ip}:{request.url.path}"

    bucket = _buckets[key]
    window_start = now - window

    # Drop old entries outside the window
    while bucket and bucket[0] <= window_start:
        bucket.popleft()

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down.",
        )

    bucket.append(now)
    return True
