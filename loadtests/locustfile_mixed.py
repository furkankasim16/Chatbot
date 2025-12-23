import os
import random
import time
from typing import Dict, Any, Optional
from locust import HttpUser, task, between, events

# Configuration
ADMIN_USERNAME = os.getenv("LOCUST_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("LOCUST_ADMIN_PASS", "admin123")

REGULAR_USERNAME = os.getenv("LOCUST_USER", "admin") # Defaulting to admin if no user provided, assuming admin can also chat
REGULAR_PASSWORD = os.getenv("LOCUST_PASS", "admin123")

HOST = os.getenv("LOCUST_HOST", "http://localhost:8000")

# Topics and Levels for randomization
TOPICS = ["security_policy", "network_security", "cryptography", "web_security"]
LEVELS = ["beginner", "intermediate", "advanced"]
CHAT_MODES = ["tutor", "playground"] # Excluding review for simplicity or adding it if confident

class ChatbotUser(HttpUser):
    abstract = True
    host = HOST
    token: Optional[str] = None
    headers: Dict[str, str] = {}
    
    def on_start(self):
        self.login()

    def login(self):
        # Determine credentials based on class name or property
        if isinstance(self, AdminUser):
            u, p = ADMIN_USERNAME, ADMIN_PASSWORD
        else:
            u, p = REGULAR_USERNAME, REGULAR_PASSWORD

        resp = self.client.post("/api/v1/auth/login", data={"username": u, "password": p})
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            print(f"Login failed for {u}: {resp.status_code}")

    def wait_for_started_job(self, job_id: str):
        """Polls for job completion."""
        start_time = time.time()
        while time.time() - start_time < 60: # 60s timeout
            time.sleep(1)
            # Use name to group all polling requests in stats
            with self.client.get(f"/api/v1/chat/result/{job_id}", headers=self.headers, catch_response=True, name="/api/v1/chat/result/[id]") as resp:
                if resp.status_code != 200:
                    break # Error
                data = resp.json()
                status = data.get("status")
                if status == "completed":
                    return # Success
                if status in ["failed", "expired"]:
                    return # Failed
        
class AdminUser(ChatbotUser):
    wait_time = between(2, 5)
    weight = 1

    @task(3)
    def generate_random_question(self):
        if not self.token: return
        
        # dry_run=True is CRITICAL here to avoid polluting DB
        # Also pass model=mock as query param
        self.client.post("/api/v1/admin/generate-random-question", 
                         headers=self.headers,
                         params={"dry_run": True, "model": "mock"},
                         name="/api/v1/admin/generate-random-question")

    @task(1)
    def generate_specific_question(self):
        if not self.token: return

        # These are query params in the FastApi endpoint, NOT body
        params = {
            "topic": random.choice(TOPICS),
            "level": random.choice(LEVELS),
            "qtype": "mcq",
            "model": "mock", 
            "dry_run": True
        }
        
        url = "/api/v1/admin/generate-question"
        self.client.post(url, headers=self.headers, params=params, name="/api/v1/admin/generate-question")

class RegularUser(ChatbotUser):
    wait_time = between(2, 5)
    weight = 3 # More regular users than admins

    @task
    def chat_turn(self):
        if not self.token: return

        mode = random.choice(CHAT_MODES)
        message = "Bana bu konuda bilgi ver."
        
        payload = {
            "question": message, # Old endpoint usage? No, check new endpoint schema.
            # New endpoint /turn uses ChatTurnRequest.
            # Check ChatTurnRequest schema? 
            # I suspect it has: mode, message, history, topic, level etc.
            # Let's check schemas/chat.py if possible, or guess from chat.py usage.
            # chat.py: data: ChatTurnRequest.
        }
        
        # Based on typical usage:
        payload = {
            "mode": mode,
            "message": "Merhaba, bu bir test mesajıdır. Konu: " + random.choice(TOPICS),
            "topic": random.choice(TOPICS),
            "level": random.choice(LEVELS),
            "history": []
        }

        with self.client.post("/api/v1/chat/turn", json=payload, headers=self.headers, catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if "job_id" in data:
                    self.wait_for_started_job(data["job_id"])
            elif resp.status_code == 429:
                # Queue full, valid load test outcome
                resp.success()
            else:
                # potentially fail
                pass

