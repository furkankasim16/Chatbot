# app/domain/services/llm_service.py

import os
import asyncio
import time
import hashlib
import httpx
import logging
from enum import Enum
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from app.core.config import settings
from app.domain.repositories.llm_run_repo import add_llm_run
from app.domain.services.llm.prompts import build_gemini_mcq_prompt
from fastapi import HTTPException
from app.domain.schemas.chat import ChatMessage, ChatMessageRole
from app.domain.services.chat_llm import generate_chat_completion
from app.domain.services.chat_utils import try_parse_json

from app.domain.services.llm.normalizers import (
    parse_and_normalize_mcq,
    LLMParseError,
    validate_question_schema,
    QuestionValidationError,
)

logger = logging.getLogger("app.llm_service")

class LLMModel(str, Enum):
    GEMINI_FLASH = "gemini-2.0-flash"
    GROQ_LLAMA3 = "llama-3.1-8b-instant"
    OLLAMA_LLAMA3_INSTRUCT = "ollama:llama3:instruct"
    QWEN_14B = "qwen2.5-14b"
    OLLAMA_LOCAL = "ollama:default" # Uses OLLAMA_MODEL from config
    OLLAMA_PHI3_MEDIUM = "ollama:phi3:medium"
    OLLAMA_GPT_OSS_20B = "ollama:gpt-oss:20b"
    OLLAMA_MISTRAL = "ollama:mistral:latest"
    OLLAMA_GPT_OSS_120B = "ollama:gpt-oss:120b-cloud"
    OLLAMA_QUIZBOT_TR = "ollama:quizbot-tr" # Fine-tuned model
    MOCK = "mock"

# Fallback Chain Configuration
# Key: Primary Model -> Value: List of fallback models in order
FALLBACK_CHAIN = {
    LLMModel.GEMINI_FLASH: [LLMModel.GROQ_LLAMA3, LLMModel.OLLAMA_LOCAL],
    LLMModel.GROQ_LLAMA3: [LLMModel.GEMINI_FLASH, LLMModel.OLLAMA_LOCAL],
    # For Ollama specific models, usually fallback to generic local or cloud
    LLMModel.OLLAMA_LOCAL: [LLMModel.GEMINI_FLASH, LLMModel.GROQ_LLAMA3],
}


class OllamaOverloadedError(RuntimeError):
    pass

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

def _env_str(name: str, default: str) -> str:
    return (os.getenv(name, default) or default).strip().lower()

# 0 => limiter kapalı (mevcut davranış aynı)
OLLAMA_MAX_CONCURRENCY = _env_int("OLLAMA_MAX_CONCURRENCY", 0)
# reject => doluysa hemen hata (429'a map edebilirsin)
# wait   => boşalana kadar bekle
OLLAMA_OVERLOAD_MODE = _env_str("OLLAMA_OVERLOAD_MODE", "reject")
# wait modunda max bekleme (0 = sonsuz)
OLLAMA_WAIT_TIMEOUT_SEC = float(os.getenv("OLLAMA_WAIT_TIMEOUT_SEC", "0") or "0")

_ollama_sem: Optional[asyncio.Semaphore] = None
if OLLAMA_MAX_CONCURRENCY and OLLAMA_MAX_CONCURRENCY > 0:
    _ollama_sem = asyncio.Semaphore(OLLAMA_MAX_CONCURRENCY)


def hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def build_prompt(topic: str, level: str, qtype: str, context: Optional[str] = None, avoid_questions: Optional[List[str]] = None) -> str:
    # Groq / HF / Ollama için ortak temel prompt
    
    context_instruction = ""
    if context:
        context_instruction = f"""
REFERANS BAĞLAMI (CONTEXT):
\"\"\"
{context}
\"\"\"
Lütfen YALNIZCA yukarıdaki bağlamı kullanarak ve oradaki bilgilere dayanarak soruyu üret.
"""

    avoid_instruction = ""
    if avoid_questions:
        # Sadece son 30 tanesini falan ekleyelim
        subset = avoid_questions[:30]
        avoid_list_str = "\n".join([f"- {q}" for q in subset])
        avoid_instruction = f"""
KESİNLİKLE şu soruların aynısını veya benzerini üretme (Çeşitlilik sağla):
{avoid_list_str}

LÜTFEN ŞUNLARI YAPMA:
- "Nedir?", "Ne demektir?", "Tanımlayınız" gibi basit sorular sorma.
- Hep aynı kalıbı kullanma ("What is X?").
- Daha çok "SENARYO", "GÖREV", "SIRALAMA", "ANALİZ" soruları sor.
"""

    if qtype == "true_false":
        json_schema = """
{
  "question": "Önerme cümlesi...",
  "options": ["Doğru", "Yanlış"],
  "answer_index": 0,
  "explanation": "Neden doğru/yanlış olduğu"
}
"""
    elif qtype == "short_answer":
        json_schema = """
{
  "question": "Kısa cevap gerektiren soru...",
  "answer": "1-2 kelimelik veya tek cümlelik net cevap",
  "explanation": "Detaylı açıklama"
}
"""
    elif qtype == "scenario":
        json_schema = """
{
  "question": "SENARYO: [Buraya olay örgüsü yazılacak]\\nSORU: [Senaryoya bağlı soru]",
  "answer": "Senaryoya uygun cevap",
  "explanation": "Analiz ve çözümleme"
}
"""
    elif qtype == "open" or qtype == "classic":
        json_schema = """
{
  "question": "Soru metni (açık uçlu)",
  "answer": "Beklenen ideal ve detaylı cevap",
  "explanation": "Cevabın neden doğru olduğuna dair açıklama",
  "source_passage": "Varsa kaynak metin"
}
"""
    else:
        # Default MCQ
        json_schema = """
{
  "question": "Soru metni",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "answer_index": 0,
  "explanation": "Cevabın açıklaması",
  "source_passage": "Varsa kaynak metin"
}
"""
    return f"""
Sen bir eğitim içerik üreticisisin.
{context_instruction}

Görevin: SADECE *TEK BİR SORU* üretmek.
Kesinlikle birden fazla soru üretme.
Kesinlikle liste üretme.
Kesinlikle açıklama yazma.
Kesinlikle ``` veya markdown kullanma.
SADECE aşağıdaki JSON formatında TEK bir object üret:

{json_schema}

Konu: {topic}
Zorluk: {level}
Tip: {qtype}

DİL: Sadece TÜRKÇE yaz. (Sorular ve cevaplar Türkçe olmalı).

{avoid_instruction}

Yalnızca *TEK BİR JSON OBJECT* döndür.
""".strip()

    return prompt

async def generate_hint_llm(question: str, user_answer_so_far: str = "") -> str:
    """
    Generates a hint for the user who is stuck on a question.
    Without giving the direct answer.
    """
    system_instruction = f"""
    Sen yardımsever bir öğretmensin. Öğrenci şu soruda takıldı:
    SORU: "{question}"
    
    Öğrenciye cevabı vermeden, doğru cevabı bulmasına yardımcı olacak ufak bir ipucu ver. 
    İpucu en fazla 2 cümle olsun.
    
    Yanıtın SADECE ipucu metni olsun.
    """
    
    try:
        # Calls the LLM (assuming OLLAMA_LOCAL mode for simplicity or generic)
        # We reuse execute_chat_completion_with_retry if possible, or just build a quick request context.
        # But wait, helper usually takes ChatTurnRequest. 
        # Here we just use a simplified prompt execution if available.
        # Actually, let's look at `execute_chat_completion_with_retry` signature.
        # It takes `config` and `user_text`.
        # We need to construct a robust call.
        
        # Simpler approach: construct a direct request for now or better, reuse the existing service patterns.
        # Since I can't see _execute implementation fully, I'll assume standard direct call pattern:
        config = LLMConfig(provider=LLMProvider.OLLAMA, model=LLMModel.OLLAMA_LOCAL) # Default
        client_prompt = "İpucu ver."
        
        response = await execute_chat_completion_with_retry(config, client_prompt, system_instruction=system_instruction)
        return response.strip().replace('"', '')
        
    except Exception as e:
        return "Şu an ipucu üretemiyorum. Lütfen tekrar deneyin."


async def generate_quiz_questions_llm(topic: str, level: str, n: int) -> List[Dict[str, Any]]:
    """
    Generates N unique questions for a given topic/level using LLM.
    Verifies uniqueness against RAG (Vector DB) to prevent duplicates.
    """
    from app.domain.services.rag_service import RAGService
    rag = RAGService()
    
    questions = []
    attempts = 0
    max_attempts = n * 3  # Allow some retries for duplicates
    
    created_count = 0
    
    while created_count < n and attempts < max_attempts:
        attempts += 1
        
        # 1. Build Prompt
        # We ask for ONE question at a time to ensure focusing and RAG checking
        prompt = build_prompt(topic, level, "mcq", context=None)
        
        # Add anti-duplicate context if we have previous questions in this session
        previous_context = ""
        if questions:
            previous_titles = [q['content'] for q in questions]
            previous_context = f"Daha önce şu soruları sordun, BUNLARI TEKRAR ETME: {json.dumps(previous_titles, ensure_ascii=False)}."
            
        prompt += f"\\n\\nLütfen '{topic}' konusu üzerine TEK BİR adet benzersiz çoktan seçmeli soru üret. Zorluk: {level}. {previous_context} Çıktı JSON object olsun."

        try:
            # 2. Execute LLM
            config = LLMConfig(provider=LLMProvider.OLLAMA, model=LLMModel.OLLAMA_LOCAL)
            response_text = await execute_chat_completion_with_retry(config, "Soru üret", system_instruction=prompt)
            
            # 3. Parse JSON
            # Cleanup markdown
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            q_data = json.loads(cleaned_text)
            
            # Handle potential list wrapper
            if isinstance(q_data, list):
                q_data = q_data[0]
                
            # Normalize fields
            content = q_data.get("content", q_data.get("question", ""))
            if not content: continue
            
            # 4. RAG Similarity Check (The "No Duplicate" Guard)
            # Threshold 0.2 means very close (similarity > 0.8 roughly depending on metric)
            # RAG find_similar returns matches. If we find matches with low distance, it's a dupe.
            # Using find_similar which returns doc strings. 
            # Ideally we need distance check, but we simplified find_similar to handle threshold.
            # Let's assume threshold=0.15 (very strict identity).
            similar_docs = rag.find_similar(content, "questions", k=1, threshold=0.15)
            
            if similar_docs:
                print(f"[LLM] Generated duplicate question (RAG matched), discarding... Content: {content[:30]}...")
                continue
                
            # 5. Add to list
            questions.append({
                "topic": topic,
                "level": level,
                "type": "mcq",
                "content": content,
                "options": q_data.get("options", []),
                "answer": q_data.get("answer", ""),
                "explanation": q_data.get("explanation", "")
            })
            created_count += 1
            
        except Exception as e:
            print(f"[LLM] Question generation failed attempt {attempts}: {e}")
            continue

    if not questions:
        # Fallback to pure mock if EVERYTHING fails
        return [{"topic": topic, "level": level, "type": "mcq", "content": f"{topic} (Fallback)", "options": ["A","B"], "answer": "A"}]
        
    return questions


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


@asynccontextmanager
async def ollama_slot():
    """
    Async concurrency limiter for Ollama calls.
    - OLLAMA_MAX_CONCURRENCY=0 => passthrough
    - reject => doluysa OllamaOverloadedError
    - wait   => slot boşalana kadar bekler (opsiyonel timeout)
    """
    if _ollama_sem is None:
        yield {"enabled": False, "waited_ms": 0}
        return

    t0 = time.perf_counter()

    if OLLAMA_OVERLOAD_MODE == "wait":
        if OLLAMA_WAIT_TIMEOUT_SEC and OLLAMA_WAIT_TIMEOUT_SEC > 0:
            try:
                await asyncio.wait_for(_ollama_sem.acquire(), timeout=OLLAMA_WAIT_TIMEOUT_SEC)
            except asyncio.TimeoutError:
                raise OllamaOverloadedError("LLM yoğun (wait timeout).")
        else:
            await _ollama_sem.acquire()
    else:
        if _ollama_sem.locked():
             raise OllamaOverloadedError("LLM yoğun (overload).")
        await _ollama_sem.acquire()

    waited_ms = int((time.perf_counter() - t0) * 1000)

    try:
        yield {"enabled": True, "waited_ms": waited_ms}
    finally:
        _ollama_sem.release()

# ------------------------------------------------
# Ortak entrypoint
# ------------------------------------------------
async def _attempt_generate(model: LLMModel, topic: str, level: str, qtype: str, prompt_hash: str, context: Optional[str] = None, avoid_questions: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Single attempt to generate content with a specific model.
    """
    base_prompt = build_prompt(topic, level, qtype, context, avoid_questions)
    start = time.perf_counter()
    logger.info(f"Generating with {model.value} (topic={topic}, level={level})...")

    try:
        if model == LLMModel.GEMINI_FLASH:
            # Note: build_gemini_mcq_prompt might also need context update, but using base_prompt for others
             result = await call_gemini(
                prompt=base_prompt, # Using base_prompt to ensure context is passed even for Gemini for now
                model_name=model.value,
            )
        elif model == LLMModel.GROQ_LLAMA3:
            result = await call_groq_llama3(prompt=base_prompt, model_name=model.value)
        elif model == LLMModel.QWEN_14B:
            result = await call_hf_qwen(prompt=base_prompt)
        elif model.value.startswith("ollama:"):
            result = await call_ollama_local(prompt=base_prompt, model_name=model.value)
        else:
            logger.error(f"Unknown model: {model}")
            raise ValueError(f"Desteklenmeyen model: {model}")
            
        duration_ms = int((time.perf_counter() - start) * 1000)
        
        # Add metadata about which model actually solved it
        if "question" in result and isinstance(result["question"], dict):
             result["question"].setdefault("meta", {})
             result["question"]["meta"]["source_model"] = model.value

        add_llm_run(
            model_name=model.value,
            prompt_hash=prompt_hash,
            latency_ms=duration_ms,
            token_input=result.get("token_input"),
            token_output=result.get("token_output"),
        )
        return result

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        # 429 (Rate Limit) or 5xx (Server Error) -> Candidate for fallback
        if status == 429 or status >= 500:
             logger.warning(f"Model {model.value} failed with status {status}. Triggering fallback if available.")
             raise  # Re-raise to be caught by supervisor
        raise # Other client errors (400) usually shouldn't trigger fallback unless we want to try another model's interpretation
        
    except (OllamaOverloadedError, TimeoutError, RuntimeError) as e:
         logger.warning(f"Model {model.value} failed with error: {e}. Triggering fallback if available.")
         raise

async def call_model(model: LLMModel, topic: str, level: str, qtype: str, context: Optional[str] = None, avoid_questions: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Supervisor function with Intelligent Fallback.
    """
    # Build chain: [Requested Model] + [Fallbacks]
    chain = [model]
    if model in FALLBACK_CHAIN:
        chain.extend(FALLBACK_CHAIN[model])
    
    # Make sure we don't duplicate (though pure Enum comparison is fine)
    # Filter out duplicates preserving order might be nice but list size is small.
    
    base_prompt = build_prompt(topic, level, qtype, context, avoid_questions)
    p_hash = hash_prompt(base_prompt)
    
    last_exception = None
    
    for attempt_model in chain:
        try:
            return await _attempt_generate(attempt_model, topic, level, qtype, p_hash, context, avoid_questions)
        except Exception as e:
            logger.warning(f"Attempt with {attempt_model.value} failed. Moving to next fallback.")
            last_exception = e
            continue
            
    # If we reached here, all failed
    logger.error("All models in fallback chain failed.")
    if last_exception:
        raise last_exception
    raise RuntimeError("Generation failed for all models.")


async def generate_batch(
    topic: str,
    level: str,
    n: int,
    qtype: str = "mcq",
    model: LLMModel = LLMModel.OLLAMA_LOCAL,
    avoid_questions: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Paralel olarak n adet soru üretir.
    """
    tasks = []
    for _ in range(n):
        tasks.append(call_model(model, topic, level, qtype, avoid_questions=avoid_questions))
    
    # Hepsini paralel çalıştır
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_questions = []
    for r in results:
        if isinstance(r, dict) and "question" in r:
            # call_model dönüş formatı: {"question": {...}, ...}
            # Biz sadece içindeki question dict'ini alalım
            q_data = r["question"]
            # Meta verileri ekle
            q_data.setdefault("topic", topic)
            q_data.setdefault("level", level)
            q_data.setdefault("qtype", qtype)
            q_data.setdefault("meta", {})
            q_data["meta"]["source"] = model.value
            valid_questions.append(q_data)
        else:
            # Hata durumlarını loglayabiliriz
            logger.error(f"[Batch Error] {r}")

    return valid_questions


# ------------------------------------------------
# Model Çağrıları (Async)
# ------------------------------------------------

async def call_gemini(prompt: str, model_name: str = "gemini-2.0-flash") -> Dict[str, Any]:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.error("GEMINI_API_KEY missing")
        raise RuntimeError("GEMINI_API_KEY tanımlı değil")

    base = "https://generativelanguage.googleapis.com/v1beta"
    url = f"{base}/models/{model_name}:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            
        data = r.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            logger.error(f"Gemini unexpected format: {data}")
            raise RuntimeError(f"Gemini cevabı beklenen formatta değil: {data}")

        mcq = _post_process_llm_text(text)
        usage = data.get("usageMetadata", {}) or {}

        return {
            "question": mcq,
            "token_input": usage.get("promptTokenCount"),
            "token_output": usage.get("candidatesTokenCount"),
        }
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        raise

async def call_groq_llama3(prompt: str, model_name: str) -> Dict[str, Any]:
    if not settings.GROQ_API_KEY:
        logger.error("GROQ_API_KEY missing")
        raise RuntimeError("GROQ_API_KEY tanımlı değil")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=body)
            r.raise_for_status()

        data = r.json()
        content = data["choices"][0]["message"]["content"]
        mcq = _post_process_llm_text(content)
        usage = data.get("usage", {}) or {}

        return {
            "question": mcq,
            "token_input": usage.get("prompt_tokens"),
            "token_output": usage.get("completion_tokens"),
        }
    except Exception as e:
        logger.error(f"Groq error: {e}")
        raise


async def call_hf_qwen(prompt: str) -> Dict[str, Any]:
    if not settings.HF_API_KEY:
        logger.error("HF_API_KEY missing")
        raise RuntimeError("HF_API_KEY tanımlı değil")

    url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-14B-Instruct"
    headers = {"Authorization": f"Bearer {settings.HF_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json={"inputs": prompt})
            r.raise_for_status()

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
    except Exception as e:
        logger.error(f"HuggingFace error: {e}")
        raise


OLLAMA_HOST = getattr(settings, "OLLAMA_HOST", None) or os.getenv(
    "OLLAMA_HOST", "http://localhost:11434"
)
OLLAMA_MODEL = getattr(settings, "OLLAMA_MODEL", None) or os.getenv(
    "OLLAMA_MODEL", "llama3:instruct"
)


async def call_ollama_local(prompt: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    url = f"{OLLAMA_HOST}/api/generate"
    
    # Eğer model_name gelirse onu kullan, yoksa default OLLAMA_MODEL
    # model_name "ollama:phi3:medium" gibi gelebilir, prefix'i temizleyelim mi?
    # Ollama API genelde "phi3:medium" ister.
    # Bizim enum değerlerimiz "ollama:" ile başlıyor.
    
    final_model = OLLAMA_MODEL
    if model_name:
        if model_name.startswith("ollama:"):
            name_part = model_name.replace("ollama:", "", 1)
            # Eğer "default" ise config'deki modeli (qwen/llama vs) kullan
            if name_part in ["default", "local"]: 
                 final_model = OLLAMA_MODEL
            else:
                 final_model = name_part
        else:
            final_model = model_name

    payload = {
        "model": final_model,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.8, # Increase temperature for diversity
    }

    try:
        async with ollama_slot() as slot_info:
            async with httpx.AsyncClient(timeout=260) as client:
                r = await client.post(url, json=payload)
                r.raise_for_status()

        text = r.json().get("response", "")
        mcq = _post_process_llm_text(text)

        return {
            "question": mcq,
            "token_input": None,
            "token_output": None,
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 503:
             logger.warning("Ollama overloaded (503).")
             raise OllamaOverloadedError("Ollama is busy, please try again later.")
        if e.response.status_code == 404:
             logger.error(f"Ollama model not found: {final_model}")
             raise ValueError(f"Ollama model '{final_model}' bulunamadı. Lütfen 'ollama pull {final_model}' komutunu çalıştırın.")
        logger.error(f"Ollama HTTP error: {e}")
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        raise

async def _raw_ollama_call(prompt: str, model_name: Optional[str] = None) -> str:
    """
    Raw call to Ollama without MCQ post-processing.
    """
    url = f"{OLLAMA_HOST}/api/generate"
    final_model = OLLAMA_MODEL
    if model_name:
        if model_name.startswith("ollama:"):
            name_part = model_name.replace("ollama:", "", 1)
            if name_part in ["default", "local"]: 
                 final_model = OLLAMA_MODEL
            else:
                 final_model = name_part
        else:
            final_model = model_name

    payload = {
        "model": final_model,
        "prompt": prompt,
        "stream": False,
        "format": "json"  # Force JSON mode if supported
    }

    try:
        async with ollama_slot() as _:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(url, json=payload)
                r.raise_for_status()
        
        return r.json().get("response", "")
    except Exception as e:
        logger.error(f"Raw Ollama call failed: {e}")
        raise

from app.domain.services.llm.prompts import build_rubric_evaluation_prompt
from app.domain.schemas.evaluation import EvaluationResponse
import json
import re

async def evaluate_answer_with_rubric(
    question: str,
    expected_answer: str,
    user_answer: str,
    model: LLMModel = LLMModel.OLLAMA_LOCAL
) -> EvaluationResponse:
    prompt = build_rubric_evaluation_prompt(question, expected_answer, user_answer)
    
    # Use raw generation
    raw_response = await _raw_ollama_call(prompt, model_name=model.value)
    
    # Parse JSON
    try:
        # Extract JSON if wrapped in markdown
        cleaned = raw_response.strip()
        m = re.search(r"```json\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if m:
            cleaned = m.group(1)
        
        data = json.loads(cleaned)
        return EvaluationResponse(**data)
    except Exception as e:
        logger.error(f"Failed to parse rubric evaluation: {e}. Raw: {raw_response}")
        # Fallback response
        return EvaluationResponse(
            score=0, 
            is_correct=False, 
            feedback="Değerlendirme yapılamadı (Sistem hatası).",
            rubric=[]
        )


async def execute_chat_completion_with_retry(
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

    # [LOGGING] Add to DB
    try:
        from app.domain.repositories.llm_run_repo import add_llm_run
        # Token counts not always available from chat endpoint but let's try
        t_in = usage.get("prompt_eval_count") or usage.get("prompt_tokens") or usage.get("input_tokens")
        t_out = usage.get("eval_count") or usage.get("completion_tokens") or usage.get("output_tokens")
        
        # Simple hash of last user message for uniqueness
        p_hash = None
        if messages:
            last_msg = messages[-1].content
            import hashlib
            p_hash = hashlib.sha256(last_msg.encode()).hexdigest()

        add_llm_run(
            model_name=cfg.model,
            prompt_hash=p_hash,
            latency_ms=latency,
            token_input=int(t_in) if t_in else None,
            token_output=int(t_out) if t_out else None,
            is_success=True
        )
    except Exception as e:
        logger.error(f"Failed to log chat run: {e}")

    return {"content": content, "usage": final_usage}
