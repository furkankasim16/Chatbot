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
  # LLM ayarları
  provider: str          # "ollama" | "grok" | vs.
  model: str
  temperature: float = 0.3
  max_history: int = 8   # kaç mesaj geri gideceğiz (ileride kullanırız)

CHAT_MODES: Dict[ChatMode, ChatModeConfig] = {
    ChatMode.TUTOR: ChatModeConfig(
        id=ChatMode.TUTOR,
        title="Eğitmen Modu",
        description="Seçtiğin topic üzerinde adım adım, seviyene uygun anlatım ve soru cevap.",
        provider="ollama",
        model=settings.OLLAMA_MODEL,   # ✅ tek kaynak burası
        temperature=0.25,
        max_history=8,
    ),
    ChatMode.PLAYGROUND: ChatModeConfig(
        id=ChatMode.PLAYGROUND,
        title="Playground",
        description="Serbest teknik sohbet ve denemeler için kullanılabilecek mod.",
        provider="ollama",
        model=settings.OLLAMA_MODEL,   # ✅
        temperature=0.5,
        max_history=12,
    ),
    ChatMode.REVIEW: ChatModeConfig(
        id=ChatMode.REVIEW,
        title="Review / Çözüm Analizi",
        description="Öğrencinin verdiği cevapları analiz edip geri bildirim üretir.",
        provider="ollama",
        model=settings.OLLAMA_MODEL,   # ✅
        temperature=0.2,
        max_history=4,
    ),
}


def get_mode_config(mode: ChatMode) -> ChatModeConfig:
  if mode not in CHAT_MODES:
    # Çok düşük ihtimal ama yine de fallback
    return CHAT_MODES[ChatMode.PLAYGROUND]
  return CHAT_MODES[mode]
