
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.core.rag import rag_client
from app.services.pdf_service import pdf_service
from app.api.deps import get_current_user

router = APIRouter(prefix="/rag", tags=["RAG"])

class QueryRequest(BaseModel):
    query: str
    n_results: int = 5

class IndexResponse(BaseModel):
    filename: str
    chunks_count: int
    message: str

@router.post("/index", response_model=IndexResponse)
async def index_pdf(
    file: UploadFile = File(...),
    topic: str = Form("general"),
    current_user = Depends(get_current_user)
):
    """
    Upload a PDF, parse it, chunk it, and index it in ChromaDB.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    try:
        content = await file.read()
        chunks, metadatas, ids = await pdf_service.extract_and_chunk(
            file_content=content, 
            filename=file.filename, 
            topic=topic
        )
        
        if not chunks:
            return IndexResponse(
                filename=file.filename,
                chunks_count=0,
                message="No text extracted from PDF."
            )
            
        rag_client.add_documents(chunks, metadatas, ids)
        
        return IndexResponse(
            filename=file.filename,
            chunks_count=len(chunks),
            message="Successfully indexed PDF."
        )
    except Exception as e:
        print(f"[RAG] Index error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_rag(
    request: QueryRequest,
    current_user = Depends(get_current_user)
):
    """
    Test retrieval from ChromaDB.
    """
    try:
        results = rag_client.query(
            query_text=request.query, 
            n_results=request.n_results
        )
        return {
            "query": request.query,
            "results": results
        }
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.delete("/reset")
async def reset_db(
    current_user=Depends(get_current_user)
):
    """
    Reset the knowledge base (Admin only - practically unrestricted for now if admin).
    """
    if not current_user.is_admin:
         raise HTTPException(status_code=403, detail="Admin access required")
    
    rag_client.reset()
    return {"message": "Knowledge base reset."}
