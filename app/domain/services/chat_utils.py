import re
import json
import ast
from typing import List

from app.domain.schemas.chat import ChatMessage

def extract_question_from_text(text: str) -> str | None:
    if not text:
        return None
    t = text.strip()

    m = re.search(r"\bSORU\s*:\s*(.+)", t, flags=re.I)
    if m:
        q = m.group(1).strip()
        return q if q else None

    if "?" in t:
        first_line = t.split("\n", 1)[0].strip()
        cand = first_line if "?" in first_line else t
        cand = cand.strip()
        if 5 <= len(cand) <= 400:
            return cand

    return None


def find_last_question_from_history(history: list[ChatMessage] | None) -> str | None:
    if not history:
        return None

    for m in reversed(history):
        q = extract_question_from_text(m.content)
        if q:
            return q
    return None


def is_answer_only(message: str) -> bool:
    t = (message or "").strip()
    if not t:
        return False
    if re.search(r"\bSORU\s*:", t, flags=re.I):
        return False
    if re.search(r"\bCEVAP\s*:", t, flags=re.I):
        return False
    return True


def parse_quiz_intent(text: str) -> int | None:
    if not text:
        return None

    t = text.lower()
    m = re.search(r"(\d+)\s*soru", t)
    if m:
        try:
            n = int(m.group(1))
            if 1 <= n <= 20:
                return n
        except Exception:
            return None

    if t.strip() in {"quiz", "test", "soru sor"}:
        return 5

    return None


def try_parse_json(text: str) -> dict | None:
    if not text:
        return None

    t = text.strip()

    m = re.search(r"```json\s*(\{.*?\})\s*```", t, flags=re.S)
    if m:
        t = m.group(1).strip()

    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Fallback: find first '{' and last '}'
    first_brace = t.find("{")
    last_brace = t.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = t[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except Exception:
            try:
                # Fallback: Try parsing as Python dict (single quotes support)
                obj = ast.literal_eval(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

    return None


def parse_action(message: str) -> tuple[str | None, str]:
    if not message:
        return None, ""

    m = re.match(
        r"^\s*ACTION\s*:\s*([a-z_]+)\s*\n\s*INPUT\s*:\s*([\s\S]+)$",
        message,
        flags=re.I,
    )
    if not m:
        return None, message.strip()

    return m.group(1).lower().strip(), (m.group(2) or "").strip()


def clamp_score(x) -> int:
    try:
        v = int(x)
    except Exception:
        v = 0
    return max(0, min(10, v))


def list_of_str(x) -> list[str]:
    if not isinstance(x, list):
        return []
    out: list[str] = []
    for item in x:
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def fallback_strengths_gaps(score: int) -> tuple[list[str], list[str]]:
    if score >= 8:
        return (
            ["Kavramı doğru çerçevede açıklıyorsun.", "Yanıtın genel olarak tutarlı."],
            ["Bir örnek/mini senaryo ile destekleyebilirsin."],
        )
    if score >= 6:
        return (
            ["Ana fikre değiniyorsun."],
            ["Önemli bir-iki detayı daha netleştir.", "Kısa bir örnek ekle."],
        )
    if score >= 4:
        return (
            ["Bazı doğru noktalar var."],
            ["Tanımı daha net yap.", "Temel adımları/terimleri ekle.", "Bir örnekle güçlendir."],
        )
    return (
        ["Kısmen doğru bir başlangıç var."],
        ["Önce temel tanımı kur.", "Kritik terimleri doğru kullan.", "Basit bir örnek ekle."],
    )


def normalize_review_payload(data: dict) -> dict:
    score = clamp_score(data.get("score", 0))
    strengths = list_of_str(data.get("strengths"))
    gaps = list_of_str(data.get("gaps"))
    better_answer = (data.get("better_answer") or "").strip() or None

    if not strengths or not gaps:
        fs, fg = fallback_strengths_gaps(score)
        if not strengths:
            strengths = fs
        if not gaps:
            gaps = fg

    if not better_answer:
        better_answer = (
            "Kısa tanımı net yap, ardından 1 örnek ekle. "
            "Son olarak önemli bir ayrıntı (neden/sonuç) ile bitir."
        )

    return {
        "score": score,
        "strengths": strengths[:5],
        "gaps": gaps[:5],
        "better_answer": better_answer,
    }
