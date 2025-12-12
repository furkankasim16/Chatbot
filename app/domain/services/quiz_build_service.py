# app/domain/services/quiz_build_service.py

from typing import Any, Dict, List, Optional

from app.domain.repositories.quesitons_repo import get_random, map_level_to_db_difficulty


def _get_id_safe(q: Any) -> Optional[int]:
    val = None
    if isinstance(q, dict):
        val = q.get("id")
    else:
        val = getattr(q, "id", None)

    if val is None:
        return None

    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def normalize_question(q: Any) -> Dict[str, Any]:
    """
    Senin quiz router'daki _normalize_q mantığını tek kaynağa taşıyoruz.
    DB modeli / dict / pydantic model fark etmeden frontend'in beklediği yapıya yaklaştırır.
    """
    # 1) dict
    if isinstance(q, dict):
        y = dict(q)

        # type alanı
        if "type" not in y:
            if "question_type" in y:
                y["type"] = y["question_type"]
            elif "qtype" in y:
                y["type"] = y["qtype"]

        # stem
        if not y.get("stem") and y.get("question"):
            y["stem"] = y["question"]

        # options
        if not y.get("options") and y.get("choices"):
            y["options"] = y["choices"]

        # answer derivation
        answer = y.get("answer")
        options = y.get("options")

        if answer is None and isinstance(options, list):
            ans_idx = y.get("answer_index")
            if isinstance(ans_idx, int) and 0 <= ans_idx < len(options):
                answer = options[ans_idx]

        if answer is None and isinstance(options, list):
            idxs = y.get("correct_option_indexes")
            if isinstance(idxs, list) and idxs:
                idx = idxs[0]
                if isinstance(idx, int) and 0 <= idx < len(options):
                    answer = options[idx]

        if answer is not None:
            y["answer"] = answer

        meta = y.get("meta") or {}
        meta.setdefault("lang", "tr")
        y["meta"] = meta

        if not y.get("question"):
            y["question"] = y.get("stem") or "—"

        return y

    # 2) Pydantic model
    if hasattr(q, "model_dump"):
        y = q.model_dump()

        if "type" not in y:
            if "question_type" in y:
                y["type"] = y["question_type"]
            elif "qtype" in y:
                y["type"] = y["qtype"]

        if not y.get("stem") and y.get("question"):
            y["stem"] = y["question"]

        if not y.get("options") and y.get("choices"):
            y["options"] = y["choices"]

        options = y.get("options")
        answer = y.get("answer")

        if answer is None and isinstance(options, list):
            ans_idx = y.get("answer_index")
            if isinstance(ans_idx, int) and 0 <= ans_idx < len(options):
                answer = options[ans_idx]

        if answer is None and isinstance(options, list):
            idxs = y.get("correct_option_indexes")
            if isinstance(idxs, list) and idxs:
                idx = idxs[0]
                if isinstance(idx, int) and 0 <= idx < len(options):
                    answer = options[idx]

        if answer is not None:
            y["answer"] = answer

        y.setdefault("meta", {"lang": "tr"})
        if not y.get("question"):
            y["question"] = y.get("stem") or "—"
        return y

    # 3) fallback object
    y = {
        "id": getattr(q, "id", None),
        "topic": getattr(q, "topic", None),
        "level": getattr(q, "level", None),
        "type": getattr(q, "type", None) or getattr(q, "question_type", None),
        "stem": getattr(q, "stem", None) or getattr(q, "question", None),
        "options": getattr(q, "options", None) or getattr(q, "choices", None),
        "answer": getattr(q, "answer", None),
        "meta": getattr(q, "meta", None) or {"lang": "tr"},
    }

    options = y.get("options")
    ans_idx = getattr(q, "answer_index", None)
    if y.get("answer") is None and isinstance(ans_idx, int) and isinstance(options, list):
        if 0 <= ans_idx < len(options):
            y["answer"] = options[ans_idx]

    if not y.get("stem"):
        y["stem"] = "—"

    if not y.get("question"):
        y["question"] = y.get("stem") or "—"

    return y


def build_quiz_from_db(
    topic: str,
    level: str = "beginner",
    n: int = 5,
) -> List[Dict[str, Any]]:
    """
    DB'den n adet soru çeker, exclude ile tekrarları engeller,
    normalize edilmiş dict listesi döner.
    """
    exclude: List[int] = []
    out: List[Dict[str, Any]] = []

    db_difficulty = map_level_to_db_difficulty(level)

    for _ in range(n):
        q = get_random(
            topic=topic,
            difficulty=db_difficulty,
            exclude_ids=exclude,
        )
        if not q:
            break

        qid = _get_id_safe(q)
        if qid is not None:
            exclude.append(qid)

        out.append(normalize_question(q))

    return out
