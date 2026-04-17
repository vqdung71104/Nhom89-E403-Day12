import json
import logging
import signal
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, current_spend, record_cost
from app.mock_llm import ask as llm_ask
from app.rate_limiter import check_rate_limit, get_redis_client


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(payload)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("agent")
    logger.setLevel(settings.log_level.upper())

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = configure_logging()
START_TIME = time.time()
APP_READY = False
SHUTTING_DOWN = False


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    user_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    session_id: str
    turn: int
    served_by: str
    monthly_spend_usd: float


@asynccontextmanager
async def lifespan(_: FastAPI):
    global APP_READY

    logger.info(json.dumps({"event": "startup"}))

    try:
        get_redis_client().ping()
        APP_READY = True
        logger.info(json.dumps({"event": "ready"}))
    except Exception as exc:
        APP_READY = False
        logger.exception(json.dumps({"event": "startup_failed", "error": str(exc)}))

    yield

    APP_READY = False
    logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(title="Production AI Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key", "X-User-Id"],
)


# Middleware logic
@app.middleware("http")
async def request_logging(request: Request, call_next):
    # Skip logging for health checks to avoid noise
    if request.url.path in ["/health", "/ready", "/metrics"]:
        return await call_next(request)

    started = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - started) * 1000, 2)
    logger.info(
        json.dumps(
            {
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }
        )
    )
    return response


@app.get("/health", tags=["Infrastructure"])
def health():
    """Liveness probe: Checks if the process is alive."""
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "environment": settings.environment,
        "shutting_down": SHUTTING_DOWN,
    }


@app.get("/ready", tags=["Infrastructure"])
def ready():
    """Readiness probe: Checks if all dependencies are available."""
    if SHUTTING_DOWN:
        raise HTTPException(status_code=503, detail="Service shutting down")

    if not APP_READY:
        raise HTTPException(status_code=503, detail="App still warming up")

    try:
        # Check connection to Redis
        get_redis_client().ping()
    except Exception as exc:
        logger.error(json.dumps({"event": "readiness_failed", "component": "redis", "error": str(exc)}))
        raise HTTPException(status_code=503, detail="Dependency check failed: Redis")

    return {
        "ready": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    header_user_id: str = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit),
    _budget: None = Depends(check_budget),
):
    user_id = (body.user_id or header_user_id or "anonymous").strip() or "anonymous"
    session_id = body.session_id or str(uuid.uuid4())

    redis_client = get_redis_client()
    conv_key = f"conversation:{user_id}:{session_id}"

    history_raw = redis_client.lrange(conv_key, 0, -1)
    history = [json.loads(item) for item in history_raw]

    answer = llm_ask(question=body.question, history=history)

    user_turn = {
        "role": "user",
        "content": body.question,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    assistant_turn = {
        "role": "assistant",
        "content": answer,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    redis_client.rpush(conv_key, json.dumps(user_turn), json.dumps(assistant_turn))
    redis_client.ltrim(conv_key, -2 * settings.max_history_turns, -1)
    redis_client.expire(conv_key, settings.conversation_ttl_seconds)

    estimated_cost = max(0.001, 0.00005 * (len(body.question) + len(answer)))
    updated_spend = record_cost(user_id=user_id, amount_usd=estimated_cost)

    if updated_spend > settings.monthly_budget_usd:
        raise HTTPException(status_code=402, detail="Monthly budget exceeded")

    logger.info(
        json.dumps(
            {
                "event": "agent_reply",
                "user_id": user_id,
                "session_id": session_id,
                "history_messages": len(history) + 2,
                "estimated_cost": round(estimated_cost, 6),
                "monthly_spend_usd": round(updated_spend, 4),
            }
        )
    )

    return AskResponse(
        answer=answer,
        session_id=session_id,
        turn=(len(history) // 2) + 1,
        served_by="agent",
        monthly_spend_usd=round(current_spend(user_id), 4),
    )


def _handle_sigterm(signum, _frame):
    global SHUTTING_DOWN, APP_READY
    SHUTTING_DOWN = True
    APP_READY = False
    logger.info(json.dumps({"event": "signal", "signal": signum, "type": "SIGTERM"}))


signal.signal(signal.SIGTERM, _handle_sigterm)
