# app/infra/queue/jobs.py
import asyncio
import time
from datetime import datetime
from typing import Any, Dict

from app.core.config import settings
from app.domain.schemas.chat import ChatTurnRequest, ChatTurnResponse
from app.domain.services.chat_service import handle_heavy_turn

def run_async(coro):
    """Async fonksiyonu sync worker içinde çalıştırmak için helper."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

def process_llm_turn(
    request_data: Dict[str, Any],
    user_id: int | None,
    enqueue_time: float
) -> Dict[str, Any]:
    """
    Worker tarafından çalıştırılacak sync wrapper.
    """
    # 1. TTL / Deadline kontrolü
    elapsed = time.time() - enqueue_time
    if elapsed > settings.LLM_JOB_MAX_WAIT_SEC:
        return {
            "status": "expired",
            "error": "System overloaded, job waited too long.",
            "waited_ms": int(elapsed * 1000)
        }

    # 2. Pydantic modelini geri yükle
    try:
        req = ChatTurnRequest(**request_data)
    except Exception as e:
        return {"status": "failed", "error": f"Invalid request data: {e}"}

    # 3. Async fonksiyonu çalıştır
    try:
        response: ChatTurnResponse = run_async(handle_heavy_turn(req, user_id))
        
        # Pydantic modelini dict'e çevirip döndür (Redis serialize edebilsin diye)
        return {
            "status": "completed",
            "result": response.model_dump(),
            "waited_ms": int(elapsed * 1000)
        }
    except Exception as e:
        print(f"Job failed: {e}") # Loglama
        return {
            "status": "failed",
            "error": str(e),
            "waited_ms": int(elapsed * 1000)
        }
