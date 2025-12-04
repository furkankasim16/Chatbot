# app/domain/services/llm_service.py

import os
import time
import hashlib
import requests
from enum import Enum
from typing import Dict, Any, Optional

from app.core.config import settings
from app.domain.repositories.llm_run_repo import add_llm_run
from app.domain.services.llm.prompts import build_gemini_mcq_prompt
from app.domain.services.llm.normalizers import (
    parse_and_normalize_mcq,
    LLMParseError,
    validate_question_schema,
    QuestionValidationError,
)


class LLMModel(str, Enum):
    GEMINI_FLASH = "gemini-2.0-flash"
    GROQ_LLAMA3 = "llama-3.1-8b-instant"
    QWEN_14B = "qwen2.5-14b"
    OLLAMA_LOCAL = "ollama:llama3"


def hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def build_prompt(topic: str, level: str, qtype: str) -> str:
    # Groq / HF / Ollama için ortak temel prompt
    return f"""
Sen bir eğitim içerik üreticisisin.

Görevin: SADECE *TEK BİR SORU* üretmek.
Kesinlikle birden fazla soru üretme.
Kesinlikle liste üretme.
Kesinlikle açıklama yazma.
Kesinlikle ``` veya markdown kullanma.
SADECE aşağıdaki JSON formatında TEK bir object üret:

{{
  "question": "string",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "answer_index": 0,
  "explanation": "string"
}}

Konu: {topic}
Zorluk: {level}
Tip: {qtype}

Yalnızca *TEK BİR JSON OBJECT* döndür.
""".strip()


# ------------------------------------------------
# Ortak post-process
# ------------------------------------------------
def _post_process_llm_text(raw_text: str) -> Dict[str, Any]:
    """
    Tüm modeller için ortak pipeline:
    - parse_and_normalize_mcq
    - validate_question_schema
    """
    try:
        mcq = parse_and_normalize_mcq(raw_text)
        validate_question_schema(mcq)
        return mcq
    except (LLMParseError, ValueError, QuestionValidationError) as e:
        # Burada log yazmak istersen ekleyebilirsin
        raise RuntimeError(f"LLM çıktısı geçersiz: {e}")


# ------------------------------------------------
# Ortak entrypoint
# ------------------------------------------------
def call_model(model: LLMModel, topic: str, level: str, qtype: str) -> Dict[str, Any]:
    """
    Ortak LLM çağrı wrapper'ı.
    Tüm modeller için DÖNÜŞ formatı:

    {
      "question": {
        "question": str,
        "options": list[str],
        "correct_option_index": int,
        "explanation": str,
      },
      "token_input": Optional[int],
      "token_output": Optional[int],
    }
    """

    base_prompt = build_prompt(topic, level, qtype)
    p_hash = hash_prompt(base_prompt)
    start = time.perf_counter()

    if model == LLMModel.GEMINI_FLASH:
        result = call_gemini(
            prompt=build_gemini_mcq_prompt(topic, level),
            model_name=model.value,
        )

    elif model == LLMModel.GROQ_LLAMA3:
        result = call_groq_llama3(prompt=base_prompt, model_name=model.value)

    elif model == LLMModel.QWEN_14B:
        result = call_hf_qwen(prompt=base_prompt)

    elif model == LLMModel.OLLAMA_LOCAL:
        result = call_ollama_local(prompt=base_prompt)

    else:
        raise ValueError(f"Desteklenmeyen model: {model}")

    duration_ms = int((time.perf_counter() - start) * 1000)

    add_llm_run(
        model_name=model.value,
        prompt_hash=p_hash,
        latency_ms=duration_ms,
        token_input=result.get("token_input"),
        token_output=result.get("token_output"),
    )

    return result


# ------------------------------------------------
# Model Çağrıları
# ------------------------------------------------

def call_gemini(prompt: str, model_name: str = "gemini-2.0-flash") -> Dict[str, Any]:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY tanımlı değil")

    base = "https://generativelanguage.googleapis.com/v1beta"
    url = f"{base}/models/{model_name}:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    r = requests.post(url, json=payload, timeout=40)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("[GEMINI ERROR]", r.status_code, r.text)
        raise

    data = r.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise RuntimeError(f"Gemini cevabı beklenen formatta değil: {data}")

    mcq = _post_process_llm_text(text)

    usage = data.get("usageMetadata", {}) or {}

    return {
        "question": mcq,
        "token_input": usage.get("promptTokenCount"),
        "token_output": usage.get("candidatesTokenCount"),
    }


def call_groq_llama3(prompt: str, model_name: str) -> Dict[str, Any]:
    # Groq artık OpenAI uyumlu endpoint kullanıyor
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

    body = {
        "model": model_name,  # "llama-3.1-8b-instant"
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    r = requests.post(url, headers=headers, json=body, timeout=60)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("[GROQ ERROR]", r.status_code, r.text)
        raise

    data = r.json()
    content = data["choices"][0]["message"]["content"]

    mcq = _post_process_llm_text(content)

    usage = data.get("usage", {}) or {}

    return {
        "question": mcq,
        "token_input": usage.get("prompt_tokens"),
        "token_output": usage.get("completion_tokens"),
    }


def call_hf_qwen(prompt: str) -> Dict[str, Any]:
    url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-14B-Instruct"
    headers = {"Authorization": f"Bearer {settings.HF_API_KEY}"}

    r = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=60)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("[HF QWEN ERROR]", r.status_code, r.text)
        raise

    data = r.json()

    if isinstance(data, list) and data:
        text = data[0].get("generated_text", "")
    else:
        text = str(data)

    mcq = _post_process_llm_text(text)

    return {
        "question": mcq,
        "token_input": None,
        "token_output": None,
    }


OLLAMA_HOST = getattr(settings, "OLLAMA_HOST", None) or os.getenv(
    "OLLAMA_HOST", "http://localhost:11434"
)
OLLAMA_MODEL = getattr(settings, "OLLAMA_MODEL", None) or os.getenv(
    "OLLAMA_MODEL", "llama3:instruct"
)


def call_ollama_local(prompt: str) -> Dict[str, Any]:
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    r = requests.post(url, json=payload, timeout=260)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("[OLLAMA ERROR]", r.status_code, r.text)
        raise

    text = r.json().get("response", "")
    mcq = _post_process_llm_text(text)

    return {
        "question": mcq,
        "token_input": None,
        "token_output": None,
    }