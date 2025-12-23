
import io
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class PdfService:
    def __init__(self):
        # Initialize splitter once
        # Chunk size 1000 chars ~ 200-250 tokens
        # Overlap 100 chars to maintain context
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
            is_separator_regex=False,
        )

    async def extract_and_chunk(self, file_content: bytes, filename: str, topic: str = "general"):
        """
        Extract text from PDF and split into chunks with metadata.
        """
        reader = PdfReader(io.BytesIO(file_content))
        
        chunks = []
        metadatas = []
        ids = []
        
        total_pages = len(reader.pages)
        print(f"[PDF] Processing {filename} with {total_pages} pages...")

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text:
                continue
                
            # Split page text into chunks
            page_chunks = self.splitter.split_text(text)
            
            for j, chunk in enumerate(page_chunks):
                # Unique ID for each chunk: file_page_chunkIndex
                chunk_id = f"{filename}_p{i+1}_{j}"
                
                chunks.append(chunk)
                ids.append(chunk_id)
                metadatas.append({
                    "source": filename,
                    "page": i + 1,
                    "chunk_index": j,
                    "topic": topic,
                    "total_pages": total_pages
                })

        print(f"[PDF] Extracted {len(chunks)} chunks from {filename}.")
        return chunks, metadatas, ids

# Singleton
pdf_service = PdfService()
