from fastapi import APIRouter
from pydantic import BaseModel
from app.domain.services.evaluate_service import chat_with_context
from app.domain.services.rag_service import index_folder, clear_collection
from app.core.paths import CORPUS_DIR

router = APIRouter()

class ChatIn(BaseModel):
    question: str

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
