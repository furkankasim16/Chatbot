# app/domain/schemas/chat.py

from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel


class ChatMode(str, Enum):
    TUTOR = "tutor"          # öğretici mod
    PLAYGROUND = "playground"  # serbest sohbet / deneme
    REVIEW = "review"        # quiz / cevap analizi
    LOADTEST = "loadtest"    # yük testi (mock)


class ChatMessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: ChatMessageRole
    content: str


class ChatTurnRequest(BaseModel):
    """
    Frontend'den gelecek ana payload.

    - mode: hangi chat modu? (tutor / playground / review)
    - topic, level: opsiyonel bağlam
    - message: kullanıcının son mesajı
    - history: önceki konuşma mesajları (UI tarafında tutuluyorsa)
    """
    mode: ChatMode
    message: str
    topic: Optional[str] = None
    level: Optional[str] = None
    language: Optional[str] = "tr"
    use_rag: bool = False

    # İstersen UI'den de geçmiş mesajları gönderebilirsin
    history: Optional[List[ChatMessage]] = None

    # Review modu için ekstra alanlar gerekirse buraya ekleriz
    extra: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None  

class ChatTurnResponse(BaseModel):
    """
    Backend'in frontend'e döndüğü cevap.
    """
    mode: ChatMode
    topic: Optional[str] = None
    level: Optional[str] = None

    reply: str                          # model cevabı
    suggestions: Optional[List[str]] = None  # UI'de buton olarak gösterilebilecek öneriler
    actions: Optional[List[Dict[str, Any]]] = None

    # Model / maliyet / debug bilgisi (şimdilik basit tuttum)
    raw_model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None

    # Hata olduğunda doldurulabilir
    error: Optional[str] = None
    session_id: Optional[str] = None  

class ChatJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "completed", "failed", "started", "deferred", "scheduled", "not_found", "expired"]
    result: Optional[ChatTurnResponse] = None
    waited_ms: Optional[int] = None
    error: Optional[str] = None
