import sys
import os
import asyncio
import httpx
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.services import llm_service
from app.domain.services.llm_service import LLMModel, call_model

async def main():
    print("Testing Intelligent Fallback Mechanism...")
    
    # 1. Simulate Gemini failing with 429
    fake_gemini_response = MagicMock(spec=httpx.Response)
    fake_gemini_response.status_code = 429
    
    # 2. Simulate Groq succeeding
    fake_groq_result = {
        "question": {
            "question": "Fallback Worked?", 
            "options": ["A","B"], 
            "answer_index": 0, 
            "explanation": "Yes"
        },
        "token_input": 10,
        "token_output": 10
    }

    # Patch the functions in llm_service module
    with patch("app.domain.services.llm_service.call_gemini", side_effect=httpx.HTTPStatusError("Rate Limit", request=None, response=fake_gemini_response)) as mock_gemini:
        with patch("app.domain.services.llm_service.call_groq_llama3", return_value=fake_groq_result) as mock_groq:
            
            print(f"Requesting generation with {LLMModel.GEMINI_FLASH} (Primary)...")
            
            # This should internally fail on Gemini and switch to Groq
            result = await call_model(LLMModel.GEMINI_FLASH, "test_topic", "easy", "mcq")
            
            print("Generation Result:", result)
            
            # Assertions
            if mock_gemini.called:
                print("✅ Gemini was called (and failed as expected).")
            else:
                print("❌ Gemini was NOT called.")
                
            if mock_groq.called:
                print("✅ Groq was called (Fallback triggered).")
            else:
                print("❌ Groq was NOT called.")
                
            meta_source = result["question"].get("meta", {}).get("source_model")
            print(f"Result Source: {meta_source}")
            
            if meta_source == LLMModel.GROQ_LLAMA3:
                print("✅ Source correctly identified as Groq.")
            else:
                print(f"❌ Source mismatch. Expected {LLMModel.GROQ_LLAMA3}, got {meta_source}")

if __name__ == "__main__":
    asyncio.run(main())
