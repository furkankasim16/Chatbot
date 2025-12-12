# app/domain/services/chat_llm.py

from typing import Any, Dict, List

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.domain.schemas.chat import ChatMessage, ChatMessageRole


class ChatLlmError(Exception):
    """LLM ile ilgili hatalar için basit custom exception."""
    pass


def _normalize_messages(messages: List[ChatMessage]) -> List[Dict[str, str]]:
    """
    ChatMessage -> Ollama / Groq formatı.
    """
    out: List[Dict[str, str]] = []
    for m in messages:
        role = m.role.value if isinstance(m.role, ChatMessageRole) else m.role
        out.append({"role": role, "content": m.content})
    return out


async def _call_ollama_chat(
    model: str,
    messages: List[ChatMessage],
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    Ollama'nın native /api/chat endpoint'ine istek atar.
    301 hatasını da çözecek şekilde URL düzgün kuruluyor.
    """
    base = str(settings.OLLAMA_URL).rstrip("/")  # örn: http://localhost:11434
    url = f"{base}/api/chat"

    payload = {
        "model": model,
        "messages": _normalize_messages(messages),
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
    except Exception as exc:
        raise ChatLlmError(f"Ollama bağlantı hatası: {exc}") from exc

    # Ollama genelde 200 döner. Farklı status code'ları hata sayıyoruz.
    try:
        data = resp.json()
    except Exception:
        text = resp.text
        raise ChatLlmError(
            f"Ollama geçersiz JSON döndürdü: {resp.status_code} {text}"
        )

    if resp.status_code != 200:
        # Örn: 301 / 404 / 500 gibi
        raise ChatLlmError(f"Ollama hata döndürdü: {resp.status_code} {data}")

    # Beklenen format:
    # {
    #   "model": "...",
    #   "created_at": "...",
    #   "message": {"role": "assistant", "content": "..."},
    #   ...
    # }
    msg = data.get("message") or {}
    if isinstance(msg, dict):
        content = msg.get("content", "")
    else:
        content = ""

    return {
        "content": content,
        "usage": {
            "model": model,
        },
        "error": None,
    }


async def _call_groq_chat(
    model: str,
    messages: List[ChatMessage],
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    Groq OpenAI-compatible chat completion.
    (Şu an chat_modlarda provider=ollama kullandığımız için zorunlu değil ama
     ileride tekrar kullanmak isteyebilirsin diye düzgün bırakalım.)
    """
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise ChatLlmError("Groq API anahtarı tanımlı değil.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": _normalize_messages(messages),
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except Exception as exc:
        raise ChatLlmError(f"Groq bağlantı hatası: {exc}") from exc

    try:
        data = resp.json()
    except Exception:
        text = resp.text
        raise ChatLlmError(
            f"Groq geçersiz JSON döndürdü: {resp.status_code} {text}"
        )

    if resp.status_code != 200:
        raise ChatLlmError(f"Groq hata döndürdü: {resp.status_code} {data}")

    choices = data.get("choices") or []
    if not choices:
        return {"content": "", "usage": data.get("usage"), "error": None}

    content = (
        choices[0]
        .get("message", {})
        .get("content", "")
    )

    return {
        "content": content,
        "usage": data.get("usage"),
        "error": None,
    }


async def generate_chat_completion(
    provider: str,
    model: str,
    messages: List[ChatMessage],
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    Tek entry point: chat_service burayı çağırıyor.
    Hata olursa HTTPException(502, ...) fırlatıyoruz ki frontend 502 görebilsin.
    """
    try:
        if provider == "ollama":
            return await _call_ollama_chat(
                model=model,
                messages=messages,
                temperature=temperature,
            )
        elif provider in ("groq", "grok"):
            # "grok" yazsa bile tolerant ol
            return await _call_groq_chat(
                model=model,
                messages=messages,
                temperature=temperature,
            )
        else:
            raise ChatLlmError(f"Bilinmeyen provider: {provider}")
    except ChatLlmError as e:
        # FastAPI üzerinden 502 olarak döndür
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
