from datetime import datetime, timezone

from fastapi import Depends, HTTPException

from app.auth import verify_api_key
from app.config import settings
from app.rate_limiter import get_redis_client


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _cost_key(user_id: str) -> str:
    return f"cost:{_month_key()}:{user_id}"


def current_spend(user_id: str) -> float:
    client = get_redis_client()
    raw_value = client.get(_cost_key(user_id))
    return float(raw_value or 0.0)


def check_budget(user_id: str = Depends(verify_api_key)) -> None:
    spent = current_spend(user_id)
    if spent >= settings.monthly_budget_usd:
        raise HTTPException(status_code=402, detail="Monthly budget exceeded")


def record_cost(user_id: str, amount_usd: float) -> float:
    client = get_redis_client()
    key = _cost_key(user_id)
    updated = client.incrbyfloat(key, amount_usd)
    client.expire(key, 35 * 24 * 3600)
    return float(updated)