from fastapi import APIRouter, Depends, HTTPException
from app.domain.services.rag_service import rag_service, clear_collection, get_chroma_client
from app.api.deps import get_current_user
import os

router = APIRouter(prefix="/admin/knowledge-base", tags=["knowledge-base"])

from app.core.paths import CORPUS_DIR

COLLECTION_NAME = "knowledge-base"

@router.post("/scan")
async def scan_corpus(current_user: dict = Depends(get_current_user)):
    """
    Scans app/data/corpus for PDFs and indexes them into the 'knowledge-base' collection.
    """
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin authorization required")
    
    # CORPUS_DIR comes from app.core.paths (Path object), convert to string for os.walk if needed or use as is
    corpus_path = str(CORPUS_DIR)
    
    if not os.path.exists(corpus_path):
        raise HTTPException(status_code=404, detail=f"Corpus directory not found: {corpus_path}")

    total_chunks = 0
    files_processed = []
    errors = []

    for root, _, files in os.walk(corpus_path):
        for file in files:
            if file.lower().endswith(".pdf"):
                path = os.path.join(root, file)
                try:
                    with open(path, "rb") as f:
                        pdf_bytes = f.read()
                        # Use filename for unique IDs
                        count = rag_service.index_pdf(pdf_bytes, collection_name=COLLECTION_NAME, filename=file)
                        total_chunks += count
                        files_processed.append(file)
                except Exception as e:
                    # Capture specific errors
                    errors.append(f"{file}: {str(e)}")
                    print(f"Failed to index {file}: {e}")

    return {
        "status": "success",
        "message": f"Indexed {len(files_processed)} files, {total_chunks} chunks.",
        "files": files_processed,
        "errors": errors,  # Return errors to UI
        "total_chunks": total_chunks,
        "scanned_path": corpus_path
    }

@router.delete("/reset")
async def reset_knowledge_base(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin authorization required")

    clear_collection(COLLECTION_NAME)
    return {"status": "success", "message": "Knowledge base cleared."}

@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    client = get_chroma_client()
    try:
        coll = client.get_collection(name=COLLECTION_NAME)
        count = coll.count()
    except:
        count = 0
    
    return {"chunk_count": count}
