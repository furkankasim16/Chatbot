import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.services.rag_service import rag_service

async def main():
    print("Testing RAG Service...")
    
    # Create a dummy PDF content (just text pretending to be PDF extracted content for now, 
    # but rag_service expects PDF bytes. Let's create a minimal valid PDF with reportlab or just mock extract)
    
    # Actually rag_service._extract_text_from_pdf uses pypdf.
    # Let's create a simple text file and pretend it's what we want to test, 
    # BUT rag_service.index_pdf takes bytes and calls pypdf.
    # So we need a real PDF or mock the extractor. 
    # Let's mock the extractor for this test to avoid needing a real PDF file.
    
    original_extractor = rag_service._extract_text_from_pdf
    rag_service._extract_text_from_pdf = lambda b: "Title: AI Guide\n\nChapter 1: Intro to AI.\nAI is great. " * 50 + "\n\nChapter 2: ML.\nML is cool."
    
    try:
        collection_name = "test_collection_001"
        print(f"Indexing into {collection_name}...")
        count = rag_service.index_pdf(b"dummy_bytes", collection_name)
        print(f"Indexed {count} chunks.")
        
        print("Retrieving context for 'ML'...")
        context = rag_service.retrieve_context("ML", collection_name)
        print("Context found (first 100 chars):", context[:100])
        
        print("Retrieving random context...")
        random_ctx = rag_service.get_random_context(collection_name)
        print("Random context (first 100 chars):", random_ctx[:100])
        
        if count > 0 and context and random_ctx:
            print("✅ RAG Service verification PASSED")
        else:
            print("❌ RAG Service verification FAILED")
            
    finally:
        # Restore (though script ends anyway)
        rag_service._extract_text_from_pdf = original_extractor

if __name__ == "__main__":
    asyncio.run(main())
