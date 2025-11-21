# app/domain/services/llm_service.py

import os
import time
import hashlib
import requests
from enum import Enum
from typing import Dict, Any

from app.core.config import settings
from app.domain.repositories.llm_run_repo import add_llm_run


# ------------------------------
# Model Enum — tek noktadan seçim
# ------------------------------
class LLMModel(str, Enum):
    GEMINI_FLASH = "gemini-1.5-flash"
    GROQ_LLAMA3 = "llama3-70b-groq"
    QWEN_14B = "qwen2.5-14b"
    OLLAMA_LOCAL = "ollama:llama3"


# ------------------------------
# Ortak Prompt Üretimi
# ------------------------------
def build_prompt(topic: str, level: str, qtype: str) -> str:
    return f"""
Sen bir eğitim içerik üreticisisin. Aşağıdaki formatta sıkı Türkçe soru üret:

Konu: {topic}
Seviye: {level}
Tip: {qtype}

Format:
{{
  "question": "...",
  "options": ["A", "B", "C", "D"],
  "answer_index": 0,
  "rationale": "..."
}}
""".strip()


def hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


# ------------------------------
# Model Çağrılarına Genel Wrapper
# ------------------------------
def call_model(model: LLMModel, topic: str, level: str, qtype: str) -> Dict[str, Any]:
    prompt = build_prompt(topic, level, qtype)
    p_hash = hash_prompt(prompt)

    start = time.perf_counter()

    # 1) Model seçme
    if model == LLMModel.GEMINI_FLASH:
        result = call_gemini(prompt)

    elif model == LLMModel.GROQ_LLAMA3:
        result = call_groq_llama3(prompt)

    elif model == LLMModel.QWEN_14B:
        result = call_hf_qwen(prompt)

    elif model == LLMModel.OLLAMA_LOCAL:
        result = call_ollama_local(prompt)

    else:
        raise ValueError(f"Desteklenmeyen model: {model}")

    duration_ms = int((time.perf_counter() - start) * 1000)

    # 2) Performans ölçümünü DB'ye yaz
    add_llm_run(
        model_name=model.value,
        prompt_hash=p_hash,
        latency_ms=duration_ms,
        token_input=result.get("token_input"),
        token_output=result.get("token_output"),
    )

    # 3) Normalize edilip geri dönen soru JSON
    return result["question"]


# ------------------------------
# Model Çağrılarının Gerçek İmplemantasyonu
# ------------------------------

# 1) Google Gemini (AI Studio, ücretsiz)
def call_gemini(prompt: str) -> Dict[str, Any]:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": settings.GEMINI_API_KEY}

    body = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    r = requests.post(url, headers=headers, params=params, json=body, timeout=60)
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]

    # Metni normalize edip JSON’a dönüştür
    return {
        "question": parse_question(text),
        "token_input": None,
        "token_output": None,
    }


# 2) Groq Llama3
def call_groq_llama3(prompt: str) -> Dict[str, Any]:
    url = "https://api.groq.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

    body = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    r = requests.post(url, headers=headers, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()

    content = data["choices"][0]["message"]["content"]
    return {
        "question": parse_question(content),
        "token_input": data.get("usage", {}).get("prompt_tokens"),
        "token_output": data.get("usage", {}).get("completion_tokens"),
    }


# 3) HuggingFace Inference API (Qwen2.5)
def call_hf_qwen(prompt: str) -> Dict[str, Any]:
    url = f"https://api-inference.huggingface.co/models/Qwen/Qwen2.5-14B-Instruct"
    headers = {"Authorization": f"Bearer {settings.HF_API_KEY}"}

    r = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=60)
    r.raise_for_status()
    text = r.json()[0]["generated_text"]

    return {
        "question": parse_question(text),
        "token_input": None,
        "token_output": None,
    }


# Settings'te yoksa env'den ya da default'tan al
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
    r.raise_for_status()
    text = r.json().get("response", "")

    return {
        "question": parse_question(text),
        "token_input": None,
        "token_output": None,
    }


# ------------------------------
# Üretilen metni JSON soruya dönüştür
# ------------------------------
def parse_question(text: str) -> Dict[str, Any]:
    """
    Model çıktısını normalize eder ve algoritmanın anlayacağı formata çevirir.
    """
    import json
    import re

    # Kod bloklarını temizle
    cleaned = re.sub(r"```.*?```", "", text, flags=re.S)

    # Tek tırnaklar -> çift tırnak
    cleaned = cleaned.replace("'", '"')

    try:
        return json.loads(cleaned)
    except:
        # Model bazen saf text üretirse fallback
        return {
            "question": cleaned.strip(),
            "options": [],
            "answer_index": 0,
            "rationale": ""
        }
