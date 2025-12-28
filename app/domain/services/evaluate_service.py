import requests
import logging
from typing import Dict, Any
from app.core.config import settings
from app.domain.services.rag_service import search

logger = logging.getLogger("app.evaluate")

def chat_with_context(question: str) -> Dict[str, Any]:
    # Basit iskelet: RAG araması + Ollama çağrısı
    logger.info(f"Chat (Legacy) Request: {question[:50]}...")
    
    ctx_pairs = search(question, top_k=3)
    context = "\n\n".join([doc for doc, _ in ctx_pairs]) if ctx_pairs else ""
    
    prompt = f"Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer in Turkish."
    try:
        r = requests.post(f"{settings.OLLAMA_URL}/api/generate",
                          json={"model": "llama3.1", "prompt": prompt, "stream": False},
                          timeout=60)
        r.raise_for_status()
        data = r.json()
        answer = data.get("response", "")
        logger.info(f"Chat (Legacy) Response: {answer[:100]}...")
        return {"answer": answer, "context_used": bool(context)}
    except Exception as e:
        logger.error(f"Chat (Legacy) Error: {e}")
        return {"answer": "", "error": str(e), "context_used": bool(context)}
