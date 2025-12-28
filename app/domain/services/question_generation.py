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

import time
from app.domain.repositories.llm_run_repo import add_llm_run

def _ollama_generate(prompt: str, model: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Ollama ile sync generate çağrısı.
    Returns: (content, usage_dict)
    """
    base = str(settings.OLLAMA_URL).rstrip("/")
    model = model or settings.OLLAMA_MODEL

    url = f"{base}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    start = time.perf_counter()
    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    duration_ms = int((time.perf_counter() - start) * 1000)

    data = r.json()
    usage = {
        "latency_ms": duration_ms,
        "token_input": data.get("prompt_eval_count"),
        "token_output": data.get("eval_count")
    }
    return data["response"], usage

def _gemini_generate(prompt: str, model: str) -> Tuple[str, Dict[str, Any]]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")

    url = f"{GEMINI_API_BASE}/models/{model}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    start = time.perf_counter()
    r = requests.post(url, json=payload, timeout=60)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("[GEMINI ERROR]", r.status_code, r.text)
        raise
    duration_ms = int((time.perf_counter() - start) * 1000)

    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        
        usage_meta = data.get("usageMetadata", {})
        usage = {
            "latency_ms": duration_ms,
            "token_input": usage_meta.get("promptTokenCount"),
            "token_output": usage_meta.get("candidatesTokenCount")
        }
    except Exception:
        raise RuntimeError(f"Gemini cevabı beklenen formatta değil: {data}")

    return text, usage

def _groq_chat(prompt: str, model: str) -> Tuple[str, Dict[str, Any]]:
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
            {"role": "system", "content": "You are a quiz generator. Return ONLY JSON."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }

    start = time.perf_counter()
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    duration_ms = int((time.perf_counter() - start) * 1000)
    
    data = r.json()
    content = data["choices"][0]["message"]["content"]

    usage_meta = data.get("usage", {})
    usage = {
        "latency_ms": duration_ms,
        "token_input": usage_meta.get("prompt_tokens"),
        "token_output": usage_meta.get("completion_tokens")
    }
    return content, usage


def _mock_generate(prompt: str) -> Tuple[str, Dict[str, Any]]:
    """
    Yük testi için sahte JSON üretir.
    """
    # Basit bir fake response
    fake_json = """
    {
        "question_type": "mcq",
        "topic": "mock_topic",
        "difficulty": "medium",
        "stem": "Bu bir mock sorudur (Yük testi). Aşağıdakilerden hangisi doğrudur?",
        "options": ["Seçenek A", "Seçenek B", "Seçenek C", "Seçenek D"],
        "correct_option_indexes": [0],
        "explanation": "Bu otomatik üretilmiş bir mock cevaptır.",
        "tags": ["mock", "test"],
        "max_score": 1
    }
    """
    time.sleep(0.1)  # Biraz gecikme simülasyonu
    usage = {
        "latency_ms": 100,
        "token_input": 50,
        "token_output": 50
    }
    return fake_json, usage

def _call_text_llm(model_name: str, prompt: str) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (raw_content, usage_dict)
    """
    # 0) Mock
    if model_name == "mock" or model_name.startswith("mock"):
         return _mock_generate(prompt)

    # 1) Ollama
    if model_name.startswith("ollama:"):
        real_model = model_name.replace("ollama:", "", 1)
        if not real_model:
             real_model = settings.OLLAMA_MODEL
        return _ollama_generate(prompt, model=real_model)

    # 2) Groq LLaMA3
    if model_name == LLMModel.GROQ_LLAMA3.value:
        return _groq_chat(prompt, model=model_name)

    # 3) Gemini Flash
    if model_name == LLMModel.GEMINI_FLASH.value:
        return _gemini_generate(prompt, model=model_name)

    # 4) Fallback: Assume it is an Ollama model (e.g. "qwen2.5:32b", "mistral", etc.)
    # This allows any new model pulled via `ollama pull` to work immediately.
    return _ollama_generate(prompt, model=model_name)


# --- Yardımcılar ------------------------------------------------------


def _find_json(s: str) -> str:
    """
    LLM cevabı içindeki ilk {...} bloğunu bulup döndürür.
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
    # ... (Prompt logic is fine, keeping it same if possible, but tool requires chunk replacement)
    # I will define _build_prompt in a separate tool call if this chunk is too big, 
    # but currently I am replacing lines 42-401 roughly. The prompt logic was edited in previous turn.
    # To be safe, I will NOT replace _build_prompt here.
    # I will target lines 42-188 and 352-401 separately.
    pass

# THIS REPLACEMENT IS FOR LLM CALLS (lines 42-188)
pass


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
    context = extra_params.get("context")

    base_instr = (
        "You are a quiz generator. Return ONLY one JSON object. "
        "Do NOT include explanations outside JSON. "
        "IMPORTANT: The entire content (stem, options, explanation, etc.) MUST be in TURKISH language. "
        "Translate if necessary."
    )

    if question_type == "mcq":
        schema_desc = (
            "The JSON MUST have fields: "
            "question_type='mcq', topic, difficulty, stem, options (array of strings), "
            "correct_option_indexes (array of integers), explanation (string), "
            "tags (array of strings), max_score (number)."
        )
        user = (
            f"Generate a multiple choice question in TURKISH for topic '{topic}' "
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
            f"Generate a true/false question in TURKISH for topic '{topic}' "
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
            f"Generate a short answer question in TURKISH for topic '{topic}' "
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
            f"Generate an open ended question in TURKISH for topic '{topic}' "
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
            f"Generate a scenario-based multi-step question (2-3 steps) in TURKISH for topic '{topic}' "
            f"with difficulty '{diff_str}'."
        )

    else:
        raise ValueError(f"Unsupported question_type: {question_type}")

    difficulty_instruction = ""
    if difficulty == DifficultyLevel.HARD:
        if question_type == "mcq":
            difficulty_instruction = (
                "IMPORTANT: This is a HARD level question. "
                "Do NOT ask simple recall questions. "
                "Create a complex scenario or problem-solving situation. "
                "The options should be very close to each other (distractors must be plausible). "
                "Require deep understanding and analysis of the context."
            )
        elif question_type == "short_answer":
            difficulty_instruction = (
                "IMPORTANT: This is a HARD level question. "
                "The question must describe a specific scenario, ritual, or distinct mechanism "
                "(e.g., 'Daily Standup', 'Burn-down chart') that uniquely identifies the answer. "
                "Do NOT ask generic definition questions like 'What is a methodology...'. "
                "The answer must be the specific term for that mechanism. "
                "Include common synonyms in 'accepted_answers'."
            )
        else:
            difficulty_instruction = (
                "IMPORTANT: This is a HARD level question. "
                "Requires deep understanding and analysis. "
                "Do NOT ask simple recall questions."
            )

    elif difficulty == DifficultyLevel.MEDIUM:
        difficulty_instruction = (
            "This is a MEDIUM level question. "
            "Ask questions that require connecting concepts. "
            "Avoid trivial facts."
        )
    else:
        difficulty_instruction = "This is a BEGINNER level question. Focus on fundamental concepts."

    if context:
        user = (
            f"CONTEXT:\n{context}\n\nUSER:\n{user}\n"
            f"{difficulty_instruction}\n"
            "Generate the question based EXCLUSIVELY on the CONTEXT provided above. "
            "OUTPUT MUST BE IN TURKISH."
        )
    else:
        # No context provided (Random generation or topic-based)
        no_context_instruction = (
            "You are generating a question based on your general knowledge. "
            "Ensure the question follows the difficulty level precisely. "
            "For HARD questions, use industry-standard scenarios (e.g., CISSP, PMP style) if applicable. "
            "Do NOT ask generic definitions. OUTPUT MUST BE IN TURKISH."
        )
        user = f"{user}\n{difficulty_instruction}\n{no_context_instruction}"

    prompt = f"{base_instr}\n\n{schema_desc}\n\nUSER:\n{user}\n\nReturn ONLY JSON."
    return prompt


# --- Ana fonksiyon ----------------------------------------------------


async def generate_question_from_llm(
    model_name: str,
    params: Dict[str, Any],
    save: bool = True,
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

    usage = {}
    is_success = False
    
    try:
        # Call LLM (now returns tuple)
        raw, usage = _call_text_llm(model_name, prompt)
        raw = raw.strip()

        try:
            data = json.loads(_find_json(raw))
        except Exception:
            # Fallback if _find_json fails or json.loads fails
            start = raw.find("{")
            end = raw.rfind("}")
            if start < 0 or end < 0:
                 raise ValueError("JSON not found in response")
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
            
        # RAG Context injection
        if "context" in params and isinstance(params["context"], str):
             q.source_context = params["context"]

        # DB'ye kaydet
        if save:
            qid = add_question(q)
            if hasattr(q, "id"):
                q.id = qid
        else:
            # Dry run: fake ID
            if hasattr(q, "id"):
                q.id = 0

        is_success = True
        return q

    except Exception as e:
        print(f"[GEN ERROR] {e}")
        raise e
    
    finally:
        # Log stats regardless of success/failure
        try:
            add_llm_run(
                model_name=model_name,
                prompt_hash=None, # could hash prompt
                latency_ms=usage.get("latency_ms", 0),
                token_input=usage.get("token_input"),
                token_output=usage.get("token_output"),
                is_success=is_success
            )
        except Exception as log_err:
            print(f"[LOG ERROR] {log_err}")



def pick_random_topic_and_level() -> Tuple[str, DifficultyLevel]:
    """
    Admin panelindeki 'Rastgele Soru Üret' için
    rastgele bir (topic, difficulty) çifti seçer.
    """
    topic = random.choice(TOPICS)
    difficulty = random.choice(LEVELS)
    return topic, difficulty
