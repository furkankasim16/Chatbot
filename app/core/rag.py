
import os
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings

# Persistent path for vector DB
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "knowledge_base"

class RagClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RagClient, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        print(f"[RAG] Initializing ChromaDB at {CHROMA_DB_PATH}...")
        
        # Initialize Embedding Function (runs locally)
        # This will download the model on first run (~80MB)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Initialize Client
        self.client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(allow_reset=True)
        )
        
        # Get or Create Collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"[RAG] Collection '{COLLECTION_NAME}' ready with {self.collection.count()} documents.")

    def add_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        """
        Add documents to the collection.
        """
        if not documents:
            return

        print(f"[RAG] Adding {len(documents)} documents...")
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"[RAG] Added successfully. Total count: {self.collection.count()}")

    def query(self, query_text: str, n_results: int = 3, where: dict = None):
        """
        Query the collection.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        return results

    def reset(self):
        """
        Reset (clear) the database.
        """
        self.client.reset()
        # After reset, we need to recreate the collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn
        )
        print("[RAG] Database reset.")

# Global instance
rag_client = RagClient()
