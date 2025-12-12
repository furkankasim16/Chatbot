# app/domain/services/chat_service.py

import json
import re
from typing import List

from app.domain.schemas.chat import (
    ChatTurnRequest,
    ChatTurnResponse,
    ChatMessage,
    ChatMessageRole,
    ChatMode,
)
from app.domain.services.chat_modes import get_mode_config
from app.domain.services.chat_system_prompts import get_system_prompt
from app.domain.services.chat_llm import generate_chat_completion
from app.domain.services.quiz_build_service import build_quiz_from_db


def _parse_quiz_intent(text: str) -> int | None:
    """
    Çok basit intent:
    - '5 soru', '10 soru' gibi mesajlarda sayı yakalayıp quiz hazırlamaya yönlendirir.
    """
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


def _try_parse_json(text: str) -> dict | None:
    """
    LLM bazen JSON'u string olarak, bazen markdown fence ile döndürebilir.
    Burada robust şekilde dict parse etmeye çalışıyoruz.
    """
    if not text:
        return None

    t = text.strip()

    # ```json ... ``` varsa ayıkla
    m = re.search(r"```json\s*(\{.*?\})\s*```", t, flags=re.S)
    if m:
        t = m.group(1).strip()

    # direkt dict parse
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # metin içinde ilk { ... } bloğunu yakala (fallback)
    m2 = re.search(r"(\{.*\})", t, flags=re.S)
    if m2:
        try:
            obj = json.loads(m2.group(1))
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None

    return None


async def handle_chat_turn(
    req: ChatTurnRequest,
    user_id: int | None = None,
) -> ChatTurnResponse:
    """
    - quiz intent yakala (LLM'e gitmeden)
    - mode config çek
    - sistem prompt üret
    - history + mesaj ile LLM'e git
    - response dön
    """

    # A) Quiz intent → LLM çağırmadan hızlı cevap
    n_intent = _parse_quiz_intent(req.message)
    if n_intent:
        quiz_topic = req.topic or "security_policy"
        quiz_level = req.level or "beginner"

        items = build_quiz_from_db(
            topic=quiz_topic,
            level=quiz_level,
            n=n_intent,
        )

        reply = (
            "✅ Quiz hazır!\n"
            f"- Topic: {quiz_topic}\n"
            f"- Level: {quiz_level}\n"
            f"- Soru sayısı: {len(items)}\n\n"
            "Başlatmak ister misin?"
        )

        suggestions = ["Evet başlat", "5 soru", "10 soru", "Topic değiştir"]

        return ChatTurnResponse(
            mode=req.mode,
            topic=req.topic,
            level=req.level,
            reply=reply,
            suggestions=suggestions,
            actions=None,
            raw_model="local:intent-parser",
            usage=None,
            error=None,
            session_id=req.session_id,
        )

    # B) Normal chat akışı
    mode_cfg = get_mode_config(req.mode)

    system_prompt = get_system_prompt(
        mode=req.mode,
        topic=req.topic,
        level=req.level,
        language=req.language or "tr",
    )

    messages: List[ChatMessage] = []
    messages.append(ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt))

    if req.history:
        history_trimmed = req.history[-mode_cfg.max_history :]
        messages.extend(history_trimmed)

    messages.append(ChatMessage(role=ChatMessageRole.USER, content=req.message))

    llm_result = await generate_chat_completion(
        provider=mode_cfg.provider,
        model=mode_cfg.model,
        messages=messages,
        temperature=mode_cfg.temperature,
    )

    reply_text: str = (llm_result.get("content") or "").strip()

    actions: list[dict] | None = None
    suggestions: list[str] | None = None

    # ---------------------------
    # REVIEW MODE: JSON'u normalize et + action üret
    # ---------------------------
    if req.mode == ChatMode.REVIEW:
        data = _try_parse_json(reply_text)

        if data:
            score = int(data.get("score", 0) or 0)
            score = max(0, min(10, score))

            # ✅ tek kaynak: score
            is_correct = score >= 6

            feedback = (data.get("feedback") or "").strip()
            feedback_lower = feedback.lower()
            if score <= 3 and ("doğru" in feedback_lower or "harika" in feedback_lower):
                feedback = "Cevabın kısmen doğru bir noktaya değiniyor ama eksik. Daha kapsamlı açıklama gerekli."
            improvement = (data.get("improvement") or "").strip()
            sugg = data.get("suggestions") or []
            if not isinstance(sugg, list):
                sugg = []

            reply_text = (
                f"Sonuç: {'✅ Doğru' if is_correct else '❌ Yanlış/Kısmen'}\n"
                f"Puan: {score}/10\n"
                f"Geri bildirim: {feedback or '—'}\n"
                f"Geliştirme: {improvement or '—'}\n"
                f"Öneriler: {', '.join(sugg) if sugg else '—'}"
            )

            actions = [
                {
                    "type": "review_result",
                    "payload": {
                        "score": score,
                        "is_correct": is_correct,
                        "feedback": feedback,
                        "improvement": improvement,
                        "suggestions": sugg,
                    },
                }
            ]

            # review modunda yardımcı hızlı butonlar (opsiyonel)
            suggestions = [
                "Cevabımı geliştir",
                "Daha iyi örnek cevap ver",
                "Bu konudan yeni soru sor",
            ]
        else:
            # JSON parse edilemezse en azından kullanıcıyı yönlendir
            suggestions = [
                "Şu formatta dene: SORU: ... BENİM CEVABIM: ...",
                "Örnek cevap ver",
            ]

    # ---------------------------
    # TUTOR MODE: suggestions + start_quiz action
    # ---------------------------
    if req.mode == ChatMode.TUTOR:
        suggestions = [
            "Bu konuyla ilgili örnek soru ver",
            "Biraz daha detaylı açıklar mısın?",
            "Basit bir özet yap",
            "5 soru",
        ]

        if req.message.strip().lower() in {"evet başlat", "başlat", "start", "quiz başlat"}:
            actions = [
                {
                    "type": "start_quiz",
                    "payload": {
                        "topic": req.topic,
                        "level": req.level,
                        "n": 5,
                        "qtype": "mixed",
                        "use_ollama": False,
                    },
                }
            ]

    return ChatTurnResponse(
        mode=req.mode,
        topic=req.topic,
        level=req.level,
        reply=reply_text,
        suggestions=suggestions,
        actions=actions,
        raw_model=f"{mode_cfg.provider}:{mode_cfg.model}",
        usage=None,
        error=None,
        session_id=req.session_id,
    )
