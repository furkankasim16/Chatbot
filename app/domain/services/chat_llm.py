# app/domain/services/chat_llm.py

from typing import Any, Dict, List
import asyncio

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.domain.schemas.chat import ChatMessage, ChatMessageRole


class ChatLlmError(Exception):
    """LLM ile ilgili hatalar için basit custom exception."""
    pass


# -----------------------------
# Perf / Stability knobs
# -----------------------------
def _int_setting(name: str, default: int) -> int:
    try:
        return int(getattr(settings, name, default))
    except Exception:
        return default


# İstersen settings'e ekleyebilirsin:
# OLLAMA_TIMEOUT_CONNECT, OLLAMA_TIMEOUT_READ, OLLAMA_TIMEOUT_WRITE, OLLAMA_TIMEOUT_POOL
_CONNECT_TIMEOUT = float(getattr(settings, "OLLAMA_TIMEOUT_CONNECT", 5.0))
_READ_TIMEOUT = float(getattr(settings, "OLLAMA_TIMEOUT_READ", 30.0))
_WRITE_TIMEOUT = float(getattr(settings, "OLLAMA_TIMEOUT_WRITE", 30.0))
_POOL_TIMEOUT = float(getattr(settings, "OLLAMA_TIMEOUT_POOL", 5.0))

_HTTP_TIMEOUT = httpx.Timeout(
    connect=_CONNECT_TIMEOUT,
    read=_READ_TIMEOUT,
    write=_WRITE_TIMEOUT,
    pool=_POOL_TIMEOUT,
)

# Aynı anda kaç LLM request? (tek makinede p99’u stabilize eder)
_LLM_CONCURRENCY = _int_setting("LLM_CONCURRENCY", 4)
_llm_sem = asyncio.Semaphore(_LLM_CONCURRENCY)


def _normalize_messages(messages: List[ChatMessage]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for m in messages:
        role = m.role.value if isinstance(m.role, ChatMessageRole) else m.role
        out.append({"role": role, "content": m.content})
    return out


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str] | None = None,
) -> httpx.Response:
    """
    Sadece network/timeout hatalarında 1 kez retry.
    (Model hatası / 4xx / 5xx için retry yapmıyoruz.)
    """
    try:
        return await client.post(url, json=payload, headers=headers)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout, httpx.RemoteProtocolError) as exc:
        # 1 retry
        try:
            return await client.post(url, json=payload, headers=headers)
        except Exception as exc2:
            raise ChatLlmError(f"Bağlantı/timeout hatası (retry sonrası): {exc2}") from exc
    except httpx.RequestError as exc:
        # Genel network hatası
        raise ChatLlmError(f"Bağlantı hatası: {exc}") from exc


async def _call_ollama_chat(
    model: str,
    messages: List[ChatMessage],
    temperature: float = 0.3,
) -> Dict[str, Any]:
    base = str(settings.OLLAMA_URL).rstrip("/")
    url = f"{base}/api/chat"

    payload = {
        "model": model,
        "messages": _normalize_messages(messages),
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    async with _llm_sem:
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await _post_with_retry(client, url, payload)
        except ChatLlmError:
            raise
        except Exception as exc:
            raise ChatLlmError(f"Ollama bağlantı hatası: {exc}") from exc

    # JSON parse
    try:
        data = resp.json()
    except Exception:
        text = resp.text
        raise ChatLlmError(f"Ollama geçersiz JSON döndürdü: {resp.status_code} {text}")

    if resp.status_code != 200:
        raise ChatLlmError(f"Ollama hata döndürdü: {resp.status_code} {data}")

    msg = data.get("message") or {}
    content = msg.get("content", "") if isinstance(msg, dict) else ""

    return {
        "content": content,
        "usage": {"model": model},
        "error": None,
    }


async def _call_groq_chat(
    model: str,
    messages: List[ChatMessage],
    temperature: float = 0.3,
) -> Dict[str, Any]:
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

    async with _llm_sem:
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await _post_with_retry(client, url, payload, headers=headers)
        except ChatLlmError:
            raise
        except Exception as exc:
            raise ChatLlmError(f"Groq bağlantı hatası: {exc}") from exc

    try:
        data = resp.json()
    except Exception:
        text = resp.text
        raise ChatLlmError(f"Groq geçersiz JSON döndürdü: {resp.status_code} {text}")

    if resp.status_code != 200:
        raise ChatLlmError(f"Groq hata döndürdü: {resp.status_code} {data}")

    choices = data.get("choices") or []
    if not choices:
        return {"content": "", "usage": data.get("usage"), "error": None}

    content = (choices[0].get("message", {}) or {}).get("content", "")

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
            return await _call_groq_chat(
                model=model,
                messages=messages,
                temperature=temperature,
            )
        elif provider == "mock":
            await asyncio.sleep(2.0) # 2 saniye bekle (işlem simülasyonu)
            return {
                "content": "Bu bir MOCK (sahte) cevaptır. Sistem yük testindedir.",
                "usage": {"model": "mock-test"},
                "error": None
            }
        else:
            raise ChatLlmError(f"Bilinmeyen provider: {provider}")
    except ChatLlmError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
