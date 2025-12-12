# app/api/routers/chat.py

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.domain.schemas.chat import ChatTurnRequest, ChatTurnResponse
from app.domain.services.chat_llm import ChatLlmError
from app.domain.services.chat_service import handle_chat_turn
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


@router.post("/turn", response_model=ChatTurnResponse)
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

    try:
        resp = await handle_chat_turn(data, user_id=user_id)
        return resp
    except ChatLlmError as e:
        # LLM kaynaklı hataları 502 ile dön
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )