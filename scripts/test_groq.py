import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.domain.services.llm_service import call_groq_llama3, LLMModel

async def main():
    print(f"Checking GROQ_API_KEY...")
    key = settings.GROQ_API_KEY
    if not key:
        print("ERROR: GROQ_API_KEY is missing or empty.")
        return
    
    print(f"Key found: {key[:4]}...{key[-4:]}")
    
    print("Attempting to call Groq API...")
    try:
        result = await call_groq_llama3("Test prompt", LLMModel.GROQ_LLAMA3.value)
        print("Success!")
        # print(result) # Don't print full result to avoid clutter
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
