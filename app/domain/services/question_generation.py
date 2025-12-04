# app/domain/services/question_generation.py

import json
import random
from typing import Any, Dict, Literal, Optional, Tuple, List

import requests

from app.core.config import settings
from app.domain.repositories.quesitons_repo import add_question
from app.domain.schemas.question import QuestionModel, QuestionType, DifficultyLevel
from app.domain.services.llm_service import LLMModel
from app.domain.services.question_parser import parse_llm_question_payload

# Groq ayarları (.env / settings içinde tanımlı olmalı)
GROQ_API_KEY = getattr(settings, "GROQ_API_KEY", None)
GROQ_API_BASE = getattr(settings, "GROQ_API_BASE", "https://api.groq.com/openai/v1")
GEMINI_API_KEY = getattr(settings, "GEMINI_API_KEY", None)
GEMINI_API_BASE = getattr(
    settings,
    "GEMINI_API_BASE",
    "https://generativelanguage.googleapis.com/v1beta",
)
# LLM tarafında beklediğimiz question_type stringleri
QuestionTypeLiteral = Literal["mcq", "true_false", "short_answer", "open_ended", "scenario"]

# Örnek topic/difficulty listeleri (istersen Admin panel vs. ile senkron gidebilir)
TOPICS: List[str] = [
    "product_basics",
    "security_policy",
    "support_flow",
]

# Artık "beginner/intermediate/advanced" yerine enum ile uyumlu olacak:
LEVELS: List[DifficultyLevel] = [
    DifficultyLevel.EASY,
    DifficultyLevel.MEDIUM,
    DifficultyLevel.HARD,
]


# --- LLM çağrıları ----------------------------------------------------


def _ollama_generate(prompt: str, model: Optional[str] = None) -> str:
    """
    Ollama ile sync generate çağrısı.
    model_name: sadece model ismi (örn: 'llama3', 'qwen:7b' vb.)
    """
    base = str(settings.OLLAMA_URL).rstrip("/")
    model = model or settings.OLLAMA_MODEL

    url = f"{base}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    # Ollama generate cevabı: {"model": "...", "response": "...", ...}
    return data["response"]

def _gemini_generate(prompt: str, model: str) -> str:
    """
    Gemini generateContent çağrısı.
    Biz unified şema JSON'unu prompt'ta tarif ediyoruz,
    Gemini'den dönen text'i direkt parse edeceğiz.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")

    url = f"{GEMINI_API_BASE}/models/{model}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    r = requests.post(url, json=payload, timeout=60)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("[GEMINI ERROR]", r.status_code, r.text)
        raise

    data = r.json()
    try:
        # Google Generative Language formatı
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise RuntimeError(f"Gemini cevabı beklenen formatta değil: {data}")

    return text

def _groq_chat(prompt: str, model: str) -> str:
    """
    Groq OpenAI-compatible chat completions endpoint'i.
    model: Groq model ID'si (örn: 'llama-3.1-8b-instant')
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    url = f"{GROQ_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a quiz generator assistant that returns ONLY JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        # JSON dönmesi için:
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def _call_text_llm(model_name: str, prompt: str) -> str:
    """
    model_name'e göre doğru backend'e gider:
    - 'ollama:xxx' → Ollama
    - 'llama-3.1-8b-instant' → Groq
    - 'gemini-2.0-flash' → Gemini
    """
    # 1) Ollama
    if model_name.startswith("ollama:"):
        ollama_model = settings.OLLAMA_MODEL
        return _ollama_generate(prompt, model=ollama_model)

    # 2) Groq LLaMA3
    if model_name == LLMModel.GROQ_LLAMA3.value:
        return _groq_chat(prompt, model=model_name)

    # 3) Gemini Flash
    if model_name == LLMModel.GEMINI_FLASH.value:
        return _gemini_generate(prompt, model=model_name)

    # 4) Şimdilik diğerleri desteklenmiyor
    raise RuntimeError(f"Unsupported model in question_generation: {model_name}")


# --- Yardımcılar ------------------------------------------------------


def _find_json(s: str) -> str:
    """
    LLM cevabı içindeki ilk {...} bloğunu bulup döndürür.
    JSON_OBJECT response_format'ta buna gerek kalmamalı ama
    ekstra güvenlik için bırakıyoruz.
    """
    i, j = s.find("{"), s.rfind("}")
    if i >= 0 and j >= 0 and j > i:
        return s[i : j + 1]
    raise ValueError("no-json")


def _build_prompt(
    question_type: QuestionTypeLiteral,
    topic: str,
    difficulty: DifficultyLevel,
    extra_params: Dict[str, Any] | None = None,
) -> str:
    """
    LLM'den beklediğimiz JSON şemasına göre prompt üretir.
    """
    extra_params = extra_params or {}
    diff_str = difficulty.value

    base_instr = (
        "You are a quiz generator. Return ONLY one JSON object. "
        "Do NOT include explanations outside JSON. "
        "Use Turkish for all human-readable texts."
    )

    if question_type == "mcq":
        schema_desc = (
            "The JSON MUST have fields: "
            "question_type='mcq', topic, difficulty, stem, options (array of strings), "
            "correct_option_indexes (array of integers), explanation (string), "
            "tags (array of strings), max_score (number)."
        )
        user = (
            f"Generate a multiple choice question for topic '{topic}' "
            f"with difficulty '{diff_str}'."
        )

    elif question_type == "true_false":
        schema_desc = (
            "The JSON MUST have fields: "
            "question_type='true_false', topic, difficulty, stem, "
            "correct_answer (boolean), explanation (string), "
            "tags (array of strings), max_score (number)."
        )
        user = (
            f"Generate a true/false question for topic '{topic}' "
            f"with difficulty '{diff_str}'."
        )

    elif question_type == "short_answer":
        schema_desc = (
            "The JSON MUST have fields: "
            "question_type='short_answer', topic, difficulty, stem, "
            "accepted_answers (array of short strings), "
            "matching_type (one of: 'exact','case_insensitive','contains','regex'), "
            "explanation (string), tags (array of strings), max_score (number)."
        )
        user = (
            f"Generate a short answer question for topic '{topic}' "
            f"with difficulty '{diff_str}'."
        )

    elif question_type == "open_ended":
        schema_desc = (
            "The JSON MUST have fields: "
            "question_type='open_ended', topic, difficulty, stem, "
            "rubric (string explaining how to evaluate), "
            "explanation (string, optional), tags (array of strings), max_score (number)."
        )
        user = (
            f"Generate an open ended question for topic '{topic}' "
            f"with difficulty '{diff_str}'."
        )

    elif question_type == "scenario":
        schema_desc = (
            "The JSON MUST have fields: "
            "question_type='scenario', topic, difficulty, stem, scenario (long text), "
            "steps (array of step objects), total_score (number), explanation (string). "
            "Each step object MUST have fields: "
            "step_id (int), step_type (one of: 'mcq','true_false','short_answer','open_ended'), "
            "stem (string), max_score (number), "
            "and depending on step_type: "
            "- for 'mcq': options (array of strings), correct_option_indexes (array of integers) "
            "- for 'true_false': correct_answer_bool (boolean) "
            "- for 'short_answer': accepted_answers (array of strings), matching_type (string) "
            "- for 'open_ended': rubric (string)."
        )
        user = (
            f"Generate a scenario-based multi-step question (2-3 steps) for topic '{topic}' "
            f"with difficulty '{diff_str}'."
        )

    else:
        raise ValueError(f"Unsupported question_type: {question_type}")

    prompt = f"{base_instr}\n\n{schema_desc}\n\nUSER:\n{user}\n\nReturn ONLY JSON."
    return prompt


# --- Ana fonksiyon ----------------------------------------------------


async def generate_question_from_llm(
    model_name: str,
    params: Dict[str, Any],
) -> QuestionModel:
    question_type: QuestionTypeLiteral = params.get("question_type", "mcq")
    input_topic: str = params.get("topic", "general")
    difficulty_raw: str = (params.get("difficulty") or "medium").lower()

    # Difficulty enum
    try:
        difficulty = DifficultyLevel(difficulty_raw)
    except ValueError:
        difficulty = DifficultyLevel.MEDIUM

    # Prompt her zamanki gibi canonical topic ile kurulsun
    prompt = _build_prompt(
        question_type=question_type,
        topic=input_topic,
        difficulty=difficulty,
        extra_params=params,
    )

    raw = _call_text_llm(model_name, prompt).strip()

    try:
        data = json.loads(_find_json(raw))
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        data = json.loads(raw[start : end + 1])

    # JSON -> QuestionModel
    q: QuestionModel = parse_llm_question_payload(data)

    # 🔴 BURASI KRİTİK: topic ve difficulty'yi input'a zorla
    q.topic = input_topic
    q.difficulty = difficulty

    # Tag'leri zenginleştir: canonical topic her zaman tags içinde de olsun
    if q.tags is None:
        q.tags = []
    if input_topic not in q.tags:
        q.tags.insert(0, input_topic)

    # DB'ye kaydet
    qid = add_question(q)
    if hasattr(q, "id"):
        q.id = qid

    return q



def pick_random_topic_and_level() -> Tuple[str, DifficultyLevel]:
    """
    Admin panelindeki 'Rastgele Soru Üret' için
    rastgele bir (topic, difficulty) çifti seçer.
    """
    topic = random.choice(TOPICS)
    difficulty = random.choice(LEVELS)
    return topic, difficulty
