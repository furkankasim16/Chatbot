import requests
from typing import Dict, Any
from app.core.config import settings
from app.domain.services.rag_service import search

def chat_with_context(question: str) -> Dict[str, Any]:
    # Basit iskelet: RAG araması + Ollama çağrısı
    ctx_pairs = search(question, top_k=3)
    context = "\n\n".join([doc for doc, _ in ctx_pairs]) if ctx_pairs else ""
    prompt = f"Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer in Turkish."
    try:
        r = requests.post(f"{settings.OLLAMA_URL}/api/generate",
                          json={"model": "llama3.1", "prompt": prompt, "stream": False},
                          timeout=60)
        r.raise_for_status()
        data = r.json()
        return {"answer": data.get("response", ""), "context_used": bool(context)}
    except Exception as e:
        return {"answer": "", "error": str(e), "context_used": bool(context)}
