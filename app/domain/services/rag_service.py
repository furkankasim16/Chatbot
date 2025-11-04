import os, re
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Tuple
from pathlib import Path
from app.core.config import settings

def _client():
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)

def _collection(name: str = "default"):
    ef = embedding_functions.DefaultEmbeddingFunction()
    return _client().get_or_create_collection(name=name, embedding_function=ef)

def search(query: str, top_k: int = 3, collection: str = "default") -> List[Tuple[str, float]]:
    col = _collection(collection)
    res = col.query(query_texts=[query], n_results=top_k)
    docs = res.get("documents", [[]])[0]
    dists = res.get("distances", [[]])[0]
    return list(zip(docs, dists))

# ---- Indexing ----
def index_texts(texts: List[str], ids: List[str], collection: str = "default"):
    col = _collection(collection)
    col.add(documents=texts, ids=ids)

def clear_collection(collection: str = "default"):
    col = _collection(collection)
    col.delete(where={})  # all

# Basit metin çıkarımı (pdf/docx/pptx/xlsx -> düz metin)
def extract_text_from_path(path: str) -> str:
    p = Path(path)
    low = p.suffix.lower()
    if low in {".txt", ".md"}:
        return p.read_text(encoding="utf-8", errors="ignore")
    # Minimal, dış bağımlılıksız: ikili dosyaları ham olarak okuyup ascii çıkaralım
    raw = p.read_bytes()
    text = raw.decode("utf-8", errors="ignore")
    text = re.sub(r"\s+", " ", text)
    return text

def index_folder(folder: str, collection: str = "default") -> int:
    p = Path(folder)
    files = [fp for fp in p.rglob("*") if fp.is_file()]
    docs, ids = [], []
    for f in files:
        try:
            t = extract_text_from_path(str(f))
            if t.strip():
                docs.append(t[:20000])   # güvenlik: çok uzunları kıs
                ids.append(str(f))
        except Exception:
            continue
    if docs:
        index_texts(docs, ids, collection=collection)
    return len(docs)
