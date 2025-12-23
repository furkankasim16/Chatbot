import time
from typing import List, Dict, Any, Optional

from app.domain.schemas.chat import (
    ChatTurnRequest,
    ChatTurnResponse,
    ChatMessage,
    ChatMessageRole,
    ChatMode,
)
from app.domain.services.chat_modes import get_mode_config
from app.domain.services.chat_system_prompts import (
    get_system_prompt,
    get_retry_system_prompt,
)
from app.domain.services.chat_llm import generate_chat_completion
from app.domain.services.quiz_build_service import build_quiz_from_db
from fastapi import HTTPException
from app.domain.services.llm_service import ollama_slot, OllamaOverloadedError

# Import new utils
from app.domain.services.chat_utils import (
    parse_quiz_intent,
    parse_action,
    extract_question_from_text,
    find_last_question_from_history,
    is_answer_only,
    try_parse_json,
    normalize_review_payload,
    list_of_str,
)


async def _execute_llm_with_retry(
    cfg: Any,
    messages: List[ChatMessage],
    retry_system_prompt: str = None,
) -> Dict[str, Any]:
    """
    LLM call wrapper with integrated retry logic for JSON parsing issues.
    Reusable for both initial call and retry attempts.
    """
    provider = str(cfg.provider).lower()
    
    # 1. Initial Call
    t0 = time.perf_counter()
    try:
        if provider.startswith("ollama"):
            async with ollama_slot():
                result = await generate_chat_completion(
                    provider=cfg.provider,
                    model=cfg.model,
                    messages=messages,
                    temperature=cfg.temperature,
                )
        else:
            result = await generate_chat_completion(
                provider=cfg.provider,
                model=cfg.model,
                messages=messages,
                temperature=cfg.temperature,
            )
    except OllamaOverloadedError as e:
        raise HTTPException(status_code=429, detail=str(e))
    
    latency = int((time.perf_counter() - t0) * 1000)
    content = (result.get("content") or "").strip()
    usage = result.get("usage") or {}
    
    # Check if we need retry (only if retry_prompt provided AND json parse failed)
    if retry_system_prompt and try_parse_json(content) is None:
        # Prepare retry messages
        retry_msgs = list(messages)
        retry_msgs.append(
            ChatMessage(role=ChatMessageRole.SYSTEM, content=retry_system_prompt)
        )
        
        # 2. Retry Call (Temp 0.0 for stability)
        t_retry = time.perf_counter()
        try:
            if provider.startswith("ollama"):
                async with ollama_slot():
                    retry_res = await generate_chat_completion(
                        provider=cfg.provider,
                        model=cfg.model,
                        messages=retry_msgs,
                        temperature=0.0,
                    )
            else:
                retry_res = await generate_chat_completion(
                    provider=cfg.provider,
                    model=cfg.model,
                    messages=retry_msgs,
                    temperature=0.0,
                )
        except OllamaOverloadedError as e:
            raise HTTPException(status_code=429, detail=str(e))

        retry_latency = int((time.perf_counter() - t_retry) * 1000)
        
        # Merge results
        final_content = (retry_res.get("content") or "").strip()
        final_usage = {
            **usage,
            "retry": True,
            "latency_ms": latency,
            "retry_latency_ms": retry_latency,
            "latency_ms_total": latency + retry_latency,
        }
        return {"content": final_content, "usage": final_usage}

    # No retry needed
    final_usage = {
        **usage,
        "retry": False,
        "latency_ms": latency,
        "latency_ms_total": latency,
    }
    return {"content": content, "usage": final_usage}


async def handle_fast_turn(req: ChatTurnRequest) -> ChatTurnResponse | None:
    """
    Handles requests that don't need LLM (e.g., direct quiz intents).
    """
    # A) Quiz Intent
    n_intent = parse_quiz_intent(req.message)
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

        return ChatTurnResponse(
            mode=req.mode,
            topic=req.topic,
            level=req.level,
            reply=reply,
            suggestions=["Evet başlat", "5 soru", "10 soru", "Topic değiştir"],
            raw_model="local:intent-parser",
            session_id=req.session_id,
        )

    # B) Review Mode Actions
    if req.mode == ChatMode.REVIEW:
        action_type, action_input = parse_action(req.message)

        if action_type == "new_question":
            return ChatTurnResponse(
                mode=req.mode,
                topic=req.topic,
                level=req.level,
                reply="Tamam. Bu konudan yeni bir soru hazırlıyorum.",
                suggestions=["Quiz’i başlat", "Soru sayısını 5 yap", "Topic değiştir"],
                actions=[{
                    "type": "start_quiz",
                    "payload": {
                        "topic": req.topic, "level": req.level, "n": 1,
                        "qtype": "mixed", "use_ollama": True
                    }
                }],
                raw_model="local:review-new_question-bypass",
                session_id=req.session_id,
            )

        if action_type == "quiz_from_gaps":
            data = try_parse_json(action_input) or {}
            n = max(1, min(20, int(data.get("n", 5) or 5)))
            gaps = data.get("gaps") if isinstance(data.get("gaps"), list) else []
            
            return ChatTurnResponse(
                mode=req.mode,
                topic=req.topic,
                level=req.level,
                reply=f"Tamam. Eksiklerine odaklı {n} soruluk quiz hazırlıyorum.",
                suggestions=["Quiz’i başlat", "Soru sayısını 10 yap"],
                actions=[{
                    "type": "start_quiz",
                    "payload": {
                        "topic": req.topic, "level": req.level, "n": n,
                        "qtype": "mixed", "use_ollama": True, "focus_gaps": gaps[:5]
                    }
                }],
                raw_model="local:review-quiz_from_gaps-bypass",
                session_id=req.session_id,
            )

        if action_type == "quiz_topic":
            data = try_parse_json(action_input) or {}
            n = max(1, min(20, int(data.get("n", 5) or 5)))
            
            return ChatTurnResponse(
                mode=req.mode,
                topic=req.topic,
                level=req.level,
                reply=f"Tamam. Bu konudan {n} soruluk quiz hazırlıyorum.",
                suggestions=["Quiz’i başlat", "Soru sayısını 10 yap"],
                actions=[{
                    "type": "start_quiz",
                    "payload": {
                        "topic": req.topic, "level": req.level, "n": n,
                        "qtype": "mixed", "use_ollama": True
                    }
                }],
                raw_model="local:review-quiz_topic-bypass",
                session_id=req.session_id,
            )

    return None


async def handle_heavy_turn(req: ChatTurnRequest, user_id: int | None = None) -> ChatTurnResponse:
    """
    Handles complex turns requiring LLM or RAG.
    """
    action_type, action_input = parse_action(req.message)
    mode_cfg = get_mode_config(req.mode)
    
    # 1. Prepare System Prompt
    system_prompt = get_system_prompt(
        mode=req.mode,
        topic=req.topic,
        level=req.level,
        language=req.language or "tr",
    )

    # 2. Add RAG Context (if eligible)
    if req.use_rag and (req.mode != ChatMode.REVIEW or (req.mode == ChatMode.REVIEW and not action_type)):
        from app.domain.services.rag_service import rag_service
        kb_context = rag_service.retrieve_context(req.message, collection_name="knowledge-base", n_results=2)
        if kb_context:
            system_prompt += f"\n\nBİLGİ BANKASI (Bağlam):\n{kb_context}\n\nLütfen cevap verirken yukarıdaki bilgileri öncelikli olarak dikkate al."

    # 3. Add Review-specific format instructions
    if req.mode == ChatMode.REVIEW and action_type:
        if action_type == "improve":
            system_prompt += '\n\nÇIKTI FORMATI: Şema: {"answer": "2-8 cümle..."}. SADECE JSON.'
        elif action_type == "ask_gaps":
            system_prompt += '\n\nÇIKTI FORMATI: Şema: {"questions": ["..."]}. SADECE JSON.'

    # 4. Construct Messages
    messages = [ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt)]
    if req.history:
        messages.extend(req.history[-mode_cfg.max_history :])

    # 5. Determine User Content (Logic for Review 'Answer Only' format)
    user_content = action_input if (req.mode == ChatMode.REVIEW and action_type) else req.message
    if req.mode == ChatMode.REVIEW and not action_type and is_answer_only(user_content):
        last_q = find_last_question_from_history(req.history)
        if last_q:
            user_content = f"SORU: {last_q}\nCEVAP: {user_content}"
        else:
            user_content = f"SORU: (bulunamadı)\nCEVAP: {user_content}\n(Soru bulunamadı, lütfen SORU: ... CEVAP: ... formatında yaz)"

    messages.append(ChatMessage(role=ChatMessageRole.USER, content=user_content))
    
    # 6. Determine Retry Prompt Strategy
    retry_prompt = None
    if req.mode == ChatMode.REVIEW and action_type in (None, "improve", "ask_gaps"):
        retry_prompt = get_retry_system_prompt(action_type)

    # 7. Execute LLM Logic
    result = await _execute_llm_with_retry(mode_cfg, messages, retry_prompt)
    
    reply_text = result["content"]
    usage = {
        **result["usage"],
        "provider": mode_cfg.provider,
        "model": mode_cfg.model,
        "mode": str(req.mode),
    }

    # 8. Post-Process Response (Actions/Suggestions)
    actions = None
    suggestions = None

    if req.mode == ChatMode.REVIEW:
        if action_type == "improve":
            data = try_parse_json(reply_text) or {}
            answer = (data.get("answer") or "").strip() or reply_text
            actions = [{"type": "improved_answer", "payload": {"answer": answer}}]
            reply_text = "Tamam. Cevabını daha iyi hale getirdim."
            suggestions = ["Input’a uygula", "Tekrar değerlendir"]
        elif action_type == "ask_gaps":
            data = try_parse_json(reply_text) or {}
            questions = list_of_str(data.get("questions"))
            actions = [{"type": "clarifying_questions", "payload": {"questions": questions[:7]}}]
            reply_text = "Eksiklerini netleştirmek için birkaç soru çıkardım."
            suggestions = ["Seçilenleri input’a ekle", "Tekrar değerlendir"]
        else:
            # Assessment Result
            data = try_parse_json(reply_text)
            if data:
                payload = normalize_review_payload(data)
                score = payload["score"]
                label = "Geçer" if score >= 6 else "Geliştirilmeli"
                hint = payload["gaps"][0] if payload["gaps"] else ""
                reply_text = f"{label}. Puanın {score}/10. {hint}".strip()
                actions = [{"type": "review_result", "payload": payload}]
                suggestions = ["Cevabımı geliştir", "Eksiklerimi sor", "Bu konudan yeni soru sor"]
            else:
                reply_text = "JSON formatı geçerli değil. Lütfen tekrar dene."
                suggestions = ["Sadece cevabını yaz"]

    elif req.mode == ChatMode.TUTOR:
        suggestions = ["Örnek soru ver", "Detaylandır", "Özetle", "5 soru"]
        if req.message.strip().lower() in {"evet başlat", "başlat", "start", "quiz başlat"}:
            actions = [{
                "type": "start_quiz",
                "payload": {
                    "topic": req.topic, "level": req.level, "n": 5,
                    "qtype": "mixed", "use_ollama": False
                }
            }]

    return ChatTurnResponse(
        mode=req.mode,
        topic=req.topic,
        level=req.level,
        reply=reply_text,
        suggestions=suggestions,
        actions=actions,
        raw_model=f"{mode_cfg.provider}:{mode_cfg.model}",
        usage=usage,
        session_id=req.session_id,
    )
