"""
Chat endpoint'ini backend'e entegre etmek için bu dosyayı kullanın.

ADIM 1: Bu dosyayı backend klasörünüze 'chat.py' olarak kaydedin
ADIM 2: app.py dosyanızı güncelleyin (aşağıdaki talimatları takip edin)
ADIM 3: Backend'i yeniden başlatın
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import requests
import json
from typing import Optional, List
import chromadb
from chromadb.utils import embedding_functions

router = APIRouter(prefix="/chat", tags=["chat"])

EMBED_MODEL = "intfloat/multilingual-e5-large"

try:
    client = chromadb.PersistentClient(path="chroma_data")
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    collection = client.get_or_create_collection(
        name="knowledge_bot",
        embedding_function=sentence_transformer_ef
    )
    RAG_ENABLED = True
    print("[CHAT] ChromaDB connected successfully")
except Exception as e:
    RAG_ENABLED = False
    print(f"[CHAT] ChromaDB connection failed: {e}")

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

class ChatResponse(BaseModel):
    response: str

def check_ollama_connection():
    """Ollama'nın çalışıp çalışmadığını kontrol eder."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def search_knowledge_base(query: str, top_k: int = 3) -> List[str]:
    """
    ChromaDB'de kullanıcı mesajına göre ilgili chunk'ları arar.
    """
    if not RAG_ENABLED:
        return []
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        if results and results.get("documents") and len(results["documents"]) > 0:
            chunks = results["documents"][0]
            truncated_chunks = [chunk[:300] + "..." if len(chunk) > 300 else chunk for chunk in chunks]
            print(f"[CHAT] Found {len(truncated_chunks)} relevant chunks from knowledge base")
            return truncated_chunks
        else:
            print("[CHAT] No relevant chunks found in knowledge base")
            return []
    except Exception as e:
        print(f"[CHAT] Error searching knowledge base: {e}")
        return []

@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Kullanıcı mesajını alır, ChromaDB'den ilgili bilgileri çeker ve Ollama ile yanıt üretir.
    Ollama çalışmıyorsa fallback mesajı döner.
    """
    print(f"[CHAT] Received message: {request.message}")
    print(f"[CHAT] Context: {request.context}")
    
    if not check_ollama_connection():
        print("[CHAT] Ollama is not running!")
        return ChatResponse(
            response="Ollama çalışmıyor. Lütfen Ollama'yı başlatın: 'ollama serve' komutu ile."
        )
    
    try:
        relevant_chunks = search_knowledge_base(request.message, top_k=2)
        
        ollama_url = "http://localhost:11434/api/generate"
        
        if relevant_chunks:
            context_text = "\n\n".join([f"Bilgi {i+1}: {chunk}" for i, chunk in enumerate(relevant_chunks)])
            prompt = f"""Bilgi Bankası:
{context_text}

Soru: {request.message}

Kısa ve net yanıt ver:"""
            print(f"[CHAT] Using RAG context with {len(relevant_chunks)} chunks")
        else:
            prompt = f"""Soru: {request.message}

Kısa yanıt:"""
            print("[CHAT] No RAG context available, using standard prompt")
        
        if request.context:
            prompt = f"""Konu: {request.context}
Soru: {request.message}

Kısa yanıt:"""
        
        payload = {
            "model": "llama3:instruct",
            "prompt": prompt,
            "stream": False,
            "temperature": 0.3,
            "top_p": 0.8,
            "num_predict": 200,
        }
        
        print(f"[CHAT] Sending request to Ollama at {ollama_url}")
        
        response = requests.post(
            ollama_url,
            json=payload,
            timeout=60,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"[CHAT] Ollama response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get("response", "Yanıt alınamadı.")
            print(f"[CHAT] Ollama response received: {ai_response[:100]}...")
            return ChatResponse(response=ai_response)
        else:
            print(f"[CHAT] Ollama error: {response.status_code}")
            print(f"[CHAT] Response body: {response.text}")
            raise Exception(f"Ollama error: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("[CHAT] Timeout error")
        return ChatResponse(
            response="Yanıt süresi aşıldı. Daha basit bir soru deneyin veya Ollama'nın yükünü kontrol edin."
        )
    except Exception as e:
        print(f"[CHAT] Error: {str(e)}")
        return ChatResponse(
            response=f"Hata: {str(e)}. Ollama çalışıyor mu kontrol edin."
        )

@router.get("/health")
async def chat_health():
    """Chat endpoint'inin çalışıp çalışmadığını kontrol eder."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        ollama_status = "running" if response.status_code == 200 else "not running"
        
        models = []
        if response.status_code == 200:
            models = [model["name"] for model in response.json().get("models", [])]
    except Exception as e:
        ollama_status = f"error: {str(e)}"
        models = []
    
    return {
        "status": "ok",
        "ollama": ollama_status,
        "rag_enabled": RAG_ENABLED,
        "models": models,
        "message": "Chat endpoint is working"
    }
