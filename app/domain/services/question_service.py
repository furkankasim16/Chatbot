import random
import requests, json, hashlib
from typing import List, Literal, Optional
from app.core.config import settings
from app.domain.schemas.question import Question
from app.domain.repositories.quesitons_repo import add_question

QuestionType = Literal["mcq","true_false","short_answer","scenario"]

TOPICS = [
    "product_basics",
    "security_policy",
    "support_flow",
]

LEVELS = [
    "beginner",
    "intermediate",
    "advanced",
]

def _hash_payload(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

def _ollama(prompt: str, model: str | None = None) -> str:
    base = str(settings.OLLAMA_URL).rstrip("/")   # ← ÇOK ÖNEMLİ
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

from typing import Optional
import json
from app.core.config import settings
from app.domain.schemas.question import Question
from app.domain.repositories.quesitons_repo import add_question

def generate_question(
    topic: str,
    level: str,
    qtype: QuestionType = "mcq",
    model: Optional[str] = None,
) -> Question:

    sys = (
        "You are a quiz generator. Return a single JSON with fields: "
        "type, topic, level, stem, choices (array of STRING for mcq only), "
        "answer_index (integer), rationale. "
        "The 'choices' field MUST be a JSON array of pure strings, NOT objects."
    )
    user = f"Generate a {qtype} question for topic '{topic}' with level '{level}'. Use Turkish."
    prompt = f"{sys}\n\n{user}\n\nReturn ONLY JSON."

    raw = _ollama(prompt, model=model).strip()

    # JSON'a çevir
    try:
        data = json.loads(_find_json(raw))
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        data = json.loads(raw[start:end+1])

    # ---- choices fix ----
    if isinstance(data.get("choices"), list):
        fixed: list[str] = []
        for item in data["choices"]:
            if isinstance(item, dict):
                text = item.get("text") or item.get("label") or item.get("value")
                text = text or str(item)
                fixed.append(text)
            else:
                fixed.append(str(item))
        data["choices"] = fixed

    # Question objesi oluştur
    q = Question(**data, source_model=model or settings.OLLAMA_MODEL)
    q.hash = _hash_payload(q.model_dump(exclude_none=True, exclude={"id"}))

    # DB'ye kaydet
    add_question(q)

    # ❗ En önemli satır:
    return q



def _find_json(s: str) -> str:
    i, j = s.find("{"), s.rfind("}")
    if i >= 0 and j >= 0 and j > i: return s[i:j+1]
    raise ValueError("no-json")

def pick_random_topic_and_level() -> tuple[str, str]:
    """
    Admin panelindeki 'Rastgele Soru Üret' için
    rastgele bir (topic, level) çifti seçer.
    """
    topic = random.choice(TOPICS)
    level = random.choice(LEVELS)
    return topic, level