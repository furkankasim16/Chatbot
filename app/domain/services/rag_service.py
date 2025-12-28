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

        return len(chunks)

    def add_documents(self, documents: List[str], metadatas: List[dict], ids: List[str], collection_name: str = "knowledge-base"):
        """
        Directly add processed chunks to Chroma.
        """
        client = get_chroma_client()
        collection = client.get_or_create_collection(name=collection_name)
        
        model = get_embed_model()
        embeddings = model.encode(documents).tolist()
        
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def index_text(self, text: str, collection_name: str, metadata: dict = None) -> bool:
        """
        Indexes a single text string (e.g., a question) into ChromaDB.
        """
        if not text or not text.strip():
            return False

        try:
            client = get_chroma_client()
            collection = client.get_or_create_collection(name=collection_name)
            model = get_embed_model()
            
            embeddings = model.encode([text])
            
            import hashlib
            text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
            doc_id = f"text_{text_hash}"
            
            if metadata:
                metadata["hash"] = text_hash
            else:
                metadata = {"hash": text_hash}

            collection.add(
                documents=[text],
                embeddings=embeddings.tolist(),
                metadatas=[metadata],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to index text: {e}")
            return False

    def find_similar(self, text: str, collection_name: str, k: int = 3, threshold: float = 0.0) -> List[str]:
        """
        Finds similar texts. Returns list of document strings.
        Threshold: if set, only return results with distance < threshold (L2).
        """
        try:
            client = get_chroma_client()
            try:
                collection = client.get_collection(name=collection_name)
            except ValueError:
                return [] 

            model = get_embed_model()
            query_embedding = model.encode([text]).tolist()
            
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=k
            )
            
            documents = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            matches = []
            for doc, dist in zip(documents, distances):
                if threshold > 0:
                    if dist < threshold:
                        matches.append(doc)
                else:
                    matches.append(doc)
                    
            return matches

        except Exception as e:
            logger.error(f"Failed to find similar: {e}")
            return []
        """
        Semantically searches the collection for the query.
        Returns joined chunk texts.
        """
        import time
        start_ts = time.perf_counter()
        
        client = get_chroma_client()
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            logger.warning(f"Collection '{collection_name}' not found during retrieval.")
            return ""
            
        model = get_embed_model()
        query_vec = model.encode([query]).tolist()
        
        try:
            results = collection.query(
                query_embeddings=query_vec,
                n_results=n_results
            )
            
            # results['documents'] is a list of list of strings
            docs = results.get("documents", [])
            found_docs = docs[0] if docs and docs[0] else []
            
            duration = (time.perf_counter() - start_ts) * 1000
            if found_docs:
                logger.info(f"RAG Retrieval '{collection_name}' | Query: {query[:50]}... | Found: {len(found_docs)} docs | Time: {duration:.2f}ms")
            else:
                logger.info(f"RAG Retrieval '{collection_name}' | Query: {query[:50]}... | Found: 0 docs | Time: {duration:.2f}ms")

            if not found_docs:
                return ""
                
            return "\n\n".join(found_docs)

        except Exception as e:
            logger.error(f"RAG Retrieval Failed: {e}")
            return ""

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

        return "\n\n".join(docs[0])

    def index_csv_intents(self, csv_path: str, collection_name: str = "intents") -> int:
        """
        Indexes a CSV file (text, intent) for semantic classification.
        """
        import csv
        
        if not os.path.exists(csv_path):
            logger.error(f"CSV not found: {csv_path}")
            return 0
            
        texts = []
        metadatas = []
        ids = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    text = row.get("text", "").strip()
                    intent = row.get("intent", "").strip()
                    if text and intent:
                        texts.append(text)
                        metadatas.append({"intent": intent, "original_text": text})
                        ids.append(f"intent_{count}")
                        count += 1
                        
            if not texts:
                return 0
                
            # Get embeddings
            model = get_embed_model()
            embeddings = model.encode(texts)
            
            # Get/Create collection
            client = get_chroma_client()
            # Reset collection mostly to avoid duplicates if re-indexing
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass
                
            collection = client.create_collection(name=collection_name)
            
            # Batch add (Chroma handles batching usually, but let's dump all if < 5000)
            collection.add(
                documents=texts,
                embeddings=embeddings.tolist(),
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Indexed {len(texts)} intents into '{collection_name}'")
            return len(texts)
            
        except Exception as e:
            logger.error(f"Failed to index CSV intents: {e}")
            return 0

    def predict_intent(self, query: str, collection_name: str = "intents", threshold: float = 0.4) -> Optional[str]:
        """
        Predicts intent based on nearest neighbor search.
        Returns intent string if similarity score is below distance threshold (for cosine distance).
        Chroma uses L2 by default or Cosine? Default is L2 usually.
        If using E5-large, we should check distance.
        """
        client = get_chroma_client()
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            return None
            
        model = get_embed_model()
        query_vec = model.encode([query]).tolist()
        
        results = collection.query(
            query_embeddings=query_vec,
            n_results=1
        )
        
        if not results['metadatas'] or not results['metadatas'][0]:
            return None
            
        # Check distance if available
        # Chroma default for new collections is commonly L2.
        # But for semantic similarity, we usually want low distance.
        # Let's use the provided threshold.
        
        top_dist = results['distances'][0][0]
        top_intent = results['metadatas'][0][0].get("intent")
        
        if top_dist > threshold:
            logger.info(f"Intent Prediction REJECTED: Query='{query}' -> Intent='{top_intent}' (Dist: {top_dist:.4f} > {threshold})")
            return None
        
        logger.info(f"Intent Prediction ACCEPTED: Query='{query}' -> Intent='{top_intent}' (Dist: {top_dist:.4f})")
        return top_intent

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
