import asyncio
import aiohttp
import sys
import os
import time
import random

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
PASSWORD = "admin123"
NUM_REQUESTS = 5  # Number of concurrent requests

async def login(session):
    url = f"{BASE_URL}/auth/login"
    data = {"username": USERNAME, "password": PASSWORD}
    async with session.post(url, data=data) as resp:
        if resp.status != 200:
            text = await resp.text()
            print(f"❌ Login failed: {text}")
            return None
        json_resp = await resp.json()
        return json_resp.get("access_token")

async def poll_job(session, token, job_id, user_num):
    url = f"{BASE_URL}/chat/result/{job_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    start_time = time.time()
    while True:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                print(f"User {user_num}: Polling failed {resp.status}")
                return
            
            data = await resp.json()
            status = data.get("status")
            
            elapsed = time.time() - start_time
            print(f"User {user_num}: Status '{status}' (waited {elapsed:.1f}s)")
            
            if status == "completed":
                print(f"✅ User {user_num}: DONE! Result received.")
                return
            elif status in ("failed", "expired"):
                print(f"❌ User {user_num}: Job failed: {data.get('error')}")
                return
            
            await asyncio.sleep(1.0) # Poll every 1s

async def send_chat_request(session, token, user_num):
    url = f"{BASE_URL}/chat/turn"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "mode": "playground",
        "topic": "security_policy",
        "level": "beginner",
        "message": f"User {user_num}: Bana kısa bir siber güvenlik hikayesi anlat. (Rastgele: {random.randint(1, 100)})",
        "history": []
    }
    
    print(f"User {user_num}: Sending request...")
    async with session.post(url, json=payload, headers=headers) as resp:
        if resp.status == 429:
            print(f"⚠️ User {user_num}: 429 Too Many Requests (Queue Full!)")
            return
        
        if resp.status != 200:
            text = await resp.text()
            print(f"❌ User {user_num}: Request failed {resp.status} - {text}")
            return

        data = await resp.json()
        
        # Check if queued
        if "job_id" in data:
            job_id = data["job_id"]
            print(f"User {user_num}: Enqueued! Job ID: {job_id}")
            await poll_job(session, token, job_id, user_num)
        else:
            print(f"User {user_num}: Unexpected direct response (Fast path?)")

async def main():
    print(f"--- Starting Concurrency Test with {NUM_REQUESTS} Users ---")
    async with aiohttp.ClientSession() as session:
        token = await login(session)
        if not token:
            return
        
        tasks = []
        for i in range(1, NUM_REQUESTS + 1):
            tasks.append(send_chat_request(session, token, i))
        
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
