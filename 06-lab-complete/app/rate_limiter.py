from datetime import datetime, timezone
from functools import lru_cache

import redis
from fastapi import Depends, HTTPException

from app.auth import verify_api_key
from app.config import settings


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def check_rate_limit(user_id: str = Depends(verify_api_key)) -> None:
    now = datetime.now(timezone.utc)
    minute_bucket = now.strftime("%Y%m%d%H%M")
    key = f"rate:{user_id}:{minute_bucket}"

    client = get_redis_client()
    current = client.incr(key)
    if current == 1:
        client.expire(key, 61)

    if current > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({settings.rate_limit_per_minute} req/min)",
            headers={"Retry-After": "60"},
        )