from fastapi import FastAPI,UploadFile, File
from pydantic import BaseModel
import src.rag as rag 

app = FastAPI(title="knowledge-bot", version="0.1.0")

class Health(BaseModel):
    status: str = "ok"
    service: str = "knowledge-bot"

@app.get("/health", response_model=Health, tags=["system"])
def health():
    return Health()

@app.post("/index")
async def index(file: UploadFile = File(...)):
    try:
        raw = await file.read()
        text = rag.extract_text_from_file(file.filename, raw)
        if not text.strip():
            return {"status": "error", "detail": "No text extracted"}
        n_chunks = rag.index_doc(file.filename, text)
        return {"status": "indexed", "chunks": n_chunks}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/search")
async def search(q: str):
    results = rag.search(q)
    return results

@app.delete("/delete/{doc_id}")
async def delete(doc_id: str):
    result = rag.delete_doc(doc_id)
    return result

@app.delete("/delete_all")
async def delete_all():
    return rag.delete_all()



