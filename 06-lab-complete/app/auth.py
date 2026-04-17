from fastapi import Header, HTTPException

from app.config import settings


def verify_api_key(
    x_api_key: str = Header(default="", alias="X-API-Key"),
    x_user_id: str = Header(default="anonymous", alias="X-User-Id"),
) -> str:
    if not x_api_key or x_api_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_user_id