# app/api/routers/chat.py

from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.domain.schemas.chat import ChatTurnRequest, ChatTurnResponse, ChatJobResponse
from app.domain.services.chat_llm import ChatLlmError
from app.domain.services.chat_service import handle_fast_turn
from app.infra.queue.enqueue import enqueue_chat_job, get_job_status, QueueFullError
from app.domain.services.evaluate_service import chat_with_context
from app.domain.services.rag_service import index_folder, clear_collection
from app.core.paths import CORPUS_DIR
from app.core.chat_prompts import CHAT_MODE_CONFIG

router = APIRouter()


class ChatIn(BaseModel):
    question: str


# 🔹 Eski RAG tabanlı chat endpoint'in (istersen ileride kaldırırız)
@router.post("/")
def chat(in_: ChatIn):
  return chat_with_context(in_.question)


@router.post("/index")
def build_index(collection: str = "default"):
    n = index_folder(str(CORPUS_DIR), collection=collection)
    return {"indexed": n}


@router.post("/clear-index")
def clear_index(collection: str = "default"):
    clear_collection(collection)
    return {"ok": True}


@router.get("/modes", response_model=Dict[str, Dict[str, Any]])
def list_chat_modes():
    """
    Frontend’de drop-down / butonlar için mod listesi.
    { "tutor": {title, description, ...}, ... } şeklinde döner.
    """
    out: Dict[str, Dict[str, Any]] = {}

    for key, cfg in CHAT_MODE_CONFIG.items():
        # key: "tutor", "playground", "review" ...
        out[key] = {
            "id": key,
            "title": key.capitalize(),
            "description": getattr(cfg, "description", ""),
            "provider": cfg.provider,
            "model": cfg.model,
            "max_history": cfg.max_history,
            # temperature alanını ChatModeConfig’e eklediysen:
            "temperature": getattr(cfg, "temperature", 0.4),
        }

    return out


@router.post("/turn", response_model=Union[ChatTurnResponse, ChatJobResponse])
async def chat_turn(
    data: ChatTurnRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_id = current_user.get("id") or current_user.get("user_id")

    # 1. Hızlı yanıt kontrolü (LLM bypass)
    try:
        fast_resp = await handle_fast_turn(data)
        if fast_resp:
            return fast_resp
    except Exception as e:
        # Hızlı yolda hata olursa logla, ama main flow bozulmasın diye devam edebilirsin
        # veya direkt hata dönebilirsin. Şimdilik raise.
        raise HTTPException(status_code=500, detail=str(e))

    # 2. Kuyruğa ekle (Slow Path)
    try:
        # Request verisini dict'e çevirip kuyruğa atıyoruz
        job_id = enqueue_chat_job(data.model_dump(), user_id=user_id)
        return ChatJobResponse(job_id=job_id, status="queued")

    except QueueFullError:
        raise HTTPException(
            status_code=429,
            detail="System is currently overloaded. Please try again later.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Queue error: {str(e)}",
        )


@router.get("/result/{job_id}", response_model=ChatJobResponse)
def get_turn_result(job_id: str):
    """
    Job durumunu ve varsa sonucunu döner.
    """
    status_data = get_job_status(job_id)
    
    # Status data: {status, result, error, waited_ms}
    # Eğer result varsa, içinde ChatTurnResponse dict'i var demektir.
    
    # status_data'yı ChatJobResponse modeline map etmeliyiz
    return ChatJobResponse(
        job_id=job_id,
        status=status_data.get("status", "not_found"),
        result=status_data.get("result"), # Pydantic otomatik parse eder
        waited_ms=status_data.get("waited_ms"),
        error=status_data.get("error")
    )