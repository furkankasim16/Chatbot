import os, requests

token = os.getenv("TOKEN", "").strip()
url = "http://localhost:8000/api/v1/chat/turn"

payload = {
    "mode": "review",
    "topic": "security_policy",
    "level": "beginner",
    "message": "SORU: test?\nCEVAP: test",
    "history": [],
}

r = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
print("status:", r.status_code)
print("text:", r.text[:500])

