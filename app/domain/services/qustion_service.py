import requests, json, hashlib
from typing import List, Literal, Optional
from app.core.config import settings
from app.domain.schemas.question import Question
from app.domain.repositories.quesitons_repo import add_question

QuestionType = Literal["mcq","true_false","short_answer","scenario"]

def _hash_payload(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

def _ollama(prompt: str, model: str = "llama3.1") -> str:
    r = requests.post(f"{settings.OLLAMA_URL}/api/generate",
                      json={"model": model, "prompt": prompt, "stream": False},
                      timeout=120)
    r.raise_for_status()
    return r.json().get("response", "")

def generate_question(topic: str, level: str, qtype: QuestionType = "mcq", model: str = "llama3.1") -> Question:
    sys = (
        "You are a quiz generator. Return a single JSON with fields: "
        "type, topic, level, stem, choices (array for mcq only), answer_index, rationale."
    )
    user = f"Generate a {qtype} question for topic '{topic}' with level '{level}'. Use Turkish."
    prompt = f"{sys}\n\n{user}\n\nReturn ONLY JSON."
    raw = _ollama(prompt, model=model).strip()
    try:
        data = json.loads(_find_json(raw))
    except Exception:
        # basit tamir
        start = raw.find("{"); end = raw.rfind("}")
        data = json.loads(raw[start:end+1])

    q = Question(**data, source_model=model)
    q.hash = _hash_payload(q.model_dump(exclude_none=True, exclude={"id"}))
    add_question(q)
    return q

def _find_json(s: str) -> str:
    i, j = s.find("{"), s.rfind("}")
    if i >= 0 and j >= 0 and j > i: return s[i:j+1]
    raise ValueError("no-json")
