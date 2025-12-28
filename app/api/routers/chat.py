# app/api/routers/chat.py

from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.domain.schemas.chat import ChatTurnRequest, ChatTurnResponse, ChatJobResponse
from app.domain.services.chat_llm import ChatLlmError
from app.domain.services.chat_service import handle_fast_turn
from app.infra.queue.enqueue import enqueue_chat_job, get_job_status, QueueFullError
from app.domain.services.evaluate_service import chat_with_context
from app.domain.services.rag_service import index_folder, clear_collection
from app.core.paths import CORPUS_DIR
from app.core.chat_prompts import CHAT_MODE_CONFIG

router = APIRouter()


class ChatIn(BaseModel):
    question: str


# 🔹 Eski RAG tabanlı chat endpoint'in (istersen ileride kaldırırız)
@router.post("/")
def chat(in_: ChatIn):
  return chat_with_context(in_.question)


@router.post("/index")
def build_index(collection: str = "default"):
    n = index_folder(str(CORPUS_DIR), collection=collection)
    return {"indexed": n}


@router.post("/clear-index")
def clear_index(collection: str = "default"):
    clear_collection(collection)
    return {"ok": True}


@router.post("/clear-index")
def clear_index(collection: str = "default"):
    clear_collection(collection)
    return {"ok": True}


@router.get("/models")
def get_models():
    """
    Returns list of available LLM models (Local + Cloud).
    Fetches dynamic list from Ollama and adds static Cloud options.
    """
    import requests
    from app.core.config import settings
    
    models = []
    
    # 1. Local (Ollama)
    try:
        # Default URL is http://127.0.0.1:11434
        ollama_url = str(settings.OLLAMA_URL).rstrip("/")
        # /api/tags returns list of installed models
        r = requests.get(f"{ollama_url}/api/tags", timeout=2)
        
        if r.status_code == 200:
            data = r.json()
            # data['models'] is a list of objects
            for m in data.get("models", []):
                # m['name'] -> 'llama3:latest'
                raw_name = m["name"]
                
                # We prefix with 'ollama:' so Admin Panel knows it's ollama
                # BUT wait, question_generation.py checks startswith("ollama")?
                # Let's check logic: _call_text_llm passes 'model' param directly to _ollama_generate
                # _ollama_generate uses 'model' as is.
                # So if we pass "ollama:llama3", _ollama_generate gets "ollama:llama3".
                # But Ollama API expects "llama3".
                # Current hardcoded values in UI are "ollama:llama3". 
                # Does backend strip "ollama:"? 
                # Let's verify question_generation.py calls first.
                
                # Checking question_generation.py:
                # def _call_text_llm(model_name: str, ...):
                #    if model_name.startswith("llama-") or model_name.startswith("mixtral-"): return _groq_generate...
                #    if model_name.startswith("gemini-"): return _gemini_generate...
                #    # Default fallback is OLLAMA
                #    return _ollama_generate(prompt, model_name)
                
                # _ollama_generate(..., model=model):
                #    payload = { "model": model, ... }
                
                # So if UI sends "ollama:llama3", Ollama API receives "ollama:llama3". 
                # Usually Ollama API fails if prefix 'ollama:' is confusing it suitable only for internal logic?
                # Actually, some users treat "ollama:model" as a convention. 
                # If the user has "llama3" installed, requesting "ollama:llama3" might fail unless code strips it.
                
                # I see `admin-panel` values are "ollama:llama3". 
                # If that WORKS currently, then `_ollama_generate` might be stripping it OR Ollama tolerates it?
                # I suspect `_ollama_generate` or similar might NOT be stripping it, which would be a bug if verified.
                # OR the updated code in `question_generation.py` doesn't handle stripping.
                
                # Let's assume for now I should send what works. 
                # Users reported it works. Maybe they are using models named so? Unlikely.
                # Actually, in `admin-panel.tsx`, value is "ollama:llama3:instruct".
                # I will strip "ollama:" prefix in `question_generation.py` if needed, 
                # OR I will populate `id` as just `llama3:latest` and let frontend handle it.
                # BUT `question_generation.py` routing logic relies on prefixes? 
                # "Default fallback is OLLAMA". So any string not matching groq/gemini goes to Ollama.
                # So plain "llama3:latest" works fine for routing.
                
                models.append({
                    "id": raw_name,            # e.g. "llama3:latest"
                    "name": f"Ollama - {raw_name}", 
                    "provider": "ollama"
                })

    except Exception as e:
        print(f"Ollama fetch error: {e}")
        # Fallback hardcoded if fetch fails?
        models.append({"id": "llama3:latest", "name": "Ollama - Llama 3 (Offline?)", "provider": "ollama"})

    # 2. Cloud (Static)
    # These match the check prefixes in question_generation.py
    models.append({"id": "llama-3.1-8b-instant", "name": "Groq - LLaMA3 70B", "provider": "groq"})
    models.append({"id": "gemini-2.0-flash", "name": "Google - Gemini 2.0 Flash", "provider": "google"})
    
    return models


@router.get("/modes", response_model=Dict[str, Dict[str, Any]])
def list_chat_modes():
    """
    Frontend’de drop-down / butonlar için mod listesi.
    { "tutor": {title, description, ...}, ... } şeklinde döner.
    """
    out: Dict[str, Dict[str, Any]] = {}

    for key, cfg in CHAT_MODE_CONFIG.items():
        # key: "tutor", "playground", "review" ...
        out[key] = {
            "id": key,
            "title": key.capitalize(),
            "description": getattr(cfg, "description", ""),
            "provider": cfg.provider,
            "model": cfg.model,
            "max_history": cfg.max_history,
            # temperature alanını ChatModeConfig’e eklediysen:
            "temperature": getattr(cfg, "temperature", 0.4),
        }

    return out


@router.post("/turn", response_model=Union[ChatTurnResponse, ChatJobResponse])
async def chat_turn(
    data: ChatTurnRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_id = current_user.get("id") or current_user.get("user_id")

    # 1. Hızlı yanıt kontrolü (LLM bypass)
    try:
        fast_resp = await handle_fast_turn(data)
        if fast_resp:
            return fast_resp
    except Exception as e:
        # Hızlı yolda hata olursa logla, ama main flow bozulmasın diye devam edebilirsin
        # veya direkt hata dönebilirsin. Şimdilik raise.
        raise HTTPException(status_code=500, detail=str(e))

    # 2. Kuyruğa ekle (Slow Path)
    try:
        # Request verisini dict'e çevirip kuyruğa atıyoruz
        job_id = enqueue_chat_job(data.model_dump(), user_id=user_id)
        return ChatJobResponse(job_id=job_id, status="queued")

    except QueueFullError:
        raise HTTPException(
            status_code=429,
            detail="System is currently overloaded. Please try again later.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Queue error: {str(e)}",
        )


@router.get("/result/{job_id}", response_model=ChatJobResponse)
def get_turn_result(job_id: str):
    """
    Job durumunu ve varsa sonucunu döner.
    """
    status_data = get_job_status(job_id)
    
    # Status data: {status, result, error, waited_ms}
    # Eğer result varsa, içinde ChatTurnResponse dict'i var demektir.
    
    # status_data'yı ChatJobResponse modeline map etmeliyiz
    return ChatJobResponse(
        job_id=job_id,
        status=status_data.get("status", "not_found"),
        result=status_data.get("result"), # Pydantic otomatik parse eder
        waited_ms=status_data.get("waited_ms"),
        error=status_data.get("error")
    )