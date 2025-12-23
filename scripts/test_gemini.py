import asyncio
import sys
import os
import httpx

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

async def main():
    print(f"Checking GEMINI_API_KEY...")
    key = settings.GEMINI_API_KEY
    if not key:
        print("ERROR: GEMINI_API_KEY is missing or empty.")
        return
    
    print(f"Key found: {key[:4]}...{key[-4:]}")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
    
    payload = {
        "contents": [{"parts": [{"text": "Hello, are you working?"}]}]
    }

    print("Attempting to call Gemini API...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            print(f"Status: {r.status_code}")
            if r.status_code == 200:
                print("Success!")
                # print(r.json())
            else:
                print(f"Failed: {r.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
