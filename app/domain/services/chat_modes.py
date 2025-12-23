# app/domain/services/chat_modes.py

from dataclasses import dataclass
from typing import Dict

from app.domain.schemas.chat import ChatMode
from app.core.config import settings


@dataclass
class ChatModeConfig:
    id: ChatMode
    title: str
    description: str
    provider: str
    model: str
    temperature: float = 0.3
    max_history: int = 8


def _setting(name: str, default: str) -> str:
    """
    Settings içinde opsiyonel alan okumak için güvenli helper.
    Örn: OLLAMA_MODEL_REVIEW yoksa settings.OLLAMA_MODEL'a düşer.
    """
    return getattr(settings, name, None) or default


BASE_MODEL = settings.OLLAMA_MODEL

TUTOR_MODEL = _setting("OLLAMA_MODEL_TUTOR", BASE_MODEL)
PLAYGROUND_MODEL = _setting("OLLAMA_MODEL_PLAYGROUND", BASE_MODEL)
REVIEW_MODEL = _setting("OLLAMA_MODEL_REVIEW", BASE_MODEL)

CHAT_MODES: Dict[ChatMode, ChatModeConfig] = {
    ChatMode.TUTOR: ChatModeConfig(
        id=ChatMode.TUTOR,
        title="Eğitmen Modu",
        description="Seçtiğin topic üzerinde adım adım, seviyene uygun anlatım ve soru cevap.",
        provider="ollama",
        model=TUTOR_MODEL,
        temperature=0.6,
        max_history=16,
    ),
    ChatMode.PLAYGROUND: ChatModeConfig(
        id=ChatMode.PLAYGROUND,
        title="Playground",
        description="Serbest teknik sohbet ve denemeler için kullanılabilecek mod.",
        provider="ollama",
        model=PLAYGROUND_MODEL,
        temperature=0.8,
        max_history=12,
    ),
    ChatMode.REVIEW: ChatModeConfig(
        id=ChatMode.REVIEW,
        title="Review / Çözüm Analizi",
        description="Öğrencinin verdiği cevapları analiz edip geri bildirim üretir.",
        provider="ollama",
        model=REVIEW_MODEL,
        temperature=0.0,   # ✅ JSON stabilitesi
        max_history=8,
    ),
    ChatMode.LOADTEST: ChatModeConfig(
        id=ChatMode.LOADTEST,
        title="Yük Testi",
        description="Sistem performansını ölçmek için Mock LLM kullanır.",
        provider="mock",
        model="mock-v1",
        temperature=0.0,
        max_history=0,
    ),
}


def get_mode_config(mode: ChatMode) -> ChatModeConfig:
    if mode not in CHAT_MODES:
        return CHAT_MODES[ChatMode.PLAYGROUND]
    return CHAT_MODES[mode]
