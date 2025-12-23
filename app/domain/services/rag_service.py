import os
import random
import logging
from typing import List, Optional
import pypdf
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger("app.rag_service")

# Global instances (lazy loaded)
_chroma_client = None
_embed_model = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        # Ensure persistence directory exists
        persist_dir = settings.CHROMA_PERSIST_DIR
        os.makedirs(persist_dir, exist_ok=True)
        
        _chroma_client = chromadb.PersistentClient(path=persist_dir)
    return _chroma_client

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        model_name = settings.EMBED_MODEL or "intfloat/multilingual-e5-large"
        logger.info(f"Loading embedding model: {model_name}")
        _embed_model = SentenceTransformer(model_name)
    return _embed_model

class RAGService:
    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """PDF bytes -> Full text"""
        import io
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            text = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text.append(t)
            return "\n".join(text)
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            raise ValueError("PDF content could not be read.")

    def index_pdf(self, pdf_bytes: bytes, collection_name: str, filename: str = "pdf") -> int:
        """
        Extracts text, chunks it, embeds it, and stores it in ChromaDB.
        Returns the number of chunks indexed.
        """
        text = self._extract_text_from_pdf(pdf_bytes)
        if not text.strip():
            return 0
            
        chunks = self.splitter.split_text(text)
        if not chunks:
            return 0
            
        # Get embeddings
        model = get_embed_model()
        embeddings = model.encode(chunks) # List of vectors
        
        # Get/Create collection
        client = get_chroma_client()
        collection = client.get_or_create_collection(name=collection_name)
        
        # Prepare data for Chroma
        # ⚠️ CRITICAL: IDs must be unique across files. Using filename prefix.
        safe_name = filename.replace(" ", "_").replace("/", "_")
        ids = [f"{safe_name}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]
        
        # Add to collection
        collection.add(
            documents=chunks,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Indexed {len(chunks)} chunks from {filename} into '{collection_name}'")
        return len(chunks)

    def retrieve_context(self, query: str, collection_name: str, n_results: int = 3) -> str:
        """
        Semantically searches the collection for the query.
        Returns joined chunk texts.
        """
        client = get_chroma_client()
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            # Collection might not exist
            return ""
            
        model = get_embed_model()
        query_vec = model.encode([query]).tolist()
        
        results = collection.query(
            query_embeddings=query_vec,
            n_results=n_results
        )
        
        # results['documents'] is a list of list of strings
        docs = results.get("documents", [])
        if not docs or not docs[0]:
            return ""
            
        return "\n\n".join(docs[0])

    def get_random_context(self, collection_name: str, n_results: int = 1) -> str:
        """
        Returns random text chunks from the collection.
        Useful when we want 'quiz from this book' without a specific topic.
        """
        client = get_chroma_client()
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            return ""
            
        # Chroma doesn't support 'random' natively easily without getting all IDs.
        # Efficient hack: Get first N items or known IDs if we generated them sequentially.
        # But we want true random. 
        # Let's just peek a large number and sample python side if dataset is small, 
        # or just query with a random vector? Querying with random vector is fun and effective enough.
        
        model = get_embed_model()
        # Create a random vector of correct dimension. 
        # E5-large dim is 1024. But let's verify dimension from model.
        dim = model.get_sentence_embedding_dimension()
        import numpy as np
        rand_vec = np.random.rand(dim).tolist()
        
        results = collection.query(
            query_embeddings=[rand_vec],
            n_results=n_results
        )
        
        docs = results.get("documents", [])
        if not docs or not docs[0]:
            return ""
            
        return "\n\n".join(docs[0])

rag_service = RAGService()


# --- Compatibility Wrappers (for legacy evaluate_service.py & chat.py) ---

def search(query: str, top_k: int = 3) -> List[tuple]:
    """
    Legacy search support for evaluate_service.chat_with_context.
    Uses 'default' collection.
    Returns list of (document_text, score). Score is mocked as 0.0 since Chroma query doesn't easily return it here.
    """
    # Assuming 'default' collection for global chat context
    res = rag_service.retrieve_context(query, collection_name="default", n_results=top_k)
    if not res:
        return []
    # retrieve_context returns joined string. We'll just return it as one big chunk.
    return [(res, 0.9)]


def index_folder(folder_path: str, collection: str = "default") -> int:
    """
    Legacy folder indexing. Scans folder for PDFs and indexes them.
    """
    if not os.path.exists(folder_path):
        return 0
    
    count = 0
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".pdf"):
                path = os.path.join(root, file)
                try:
                    with open(path, "rb") as f:
                        rag_service.index_pdf(f.read(), collection_name=collection)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to index {path}: {e}")
    return count


def clear_collection(collection_name: str = "default"):
    """
    Deletes a collection.
    """
    client = get_chroma_client()
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass
