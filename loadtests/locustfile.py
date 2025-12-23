import os
import random
import time
from typing import Optional, Dict, Any, List

from locust import HttpUser, task, between, SequentialTaskSet, events


# -------------------------
# Config (env ile yönet)
# -------------------------
BASE_TOPIC = os.getenv("LOADTEST_TOPIC", "security_policy")
BASE_LEVEL = os.getenv("LOADTEST_LEVEL", "beginner")

USERNAME = os.getenv("LOADTEST_USER", "admin")
PASSWORD = os.getenv("LOADTEST_PASS", "admin123")

QUIZ_N = int(os.getenv("LOADTEST_QUIZ_N", "5"))
USE_OLLAMA_IN_QUIZ = os.getenv("LOADTEST_QUIZ_USE_OLLAMA", "false").lower() == "true"
ENABLE_CHAT_LOAD = os.getenv("LOADTEST_ENABLE_CHAT", "true").lower() == "true"

# Timing bekleme (kullanıcı düşünme süresi)
QUESTION_THINK_MIN = float(os.getenv("LOADTEST_Q_THINK_MIN", "0.6"))
QUESTION_THINK_MAX = float(os.getenv("LOADTEST_Q_THINK_MAX", "2.0"))

CHAT_MESSAGES = [
    "JWT ile session farkı nedir?",
    "CORS ne işe yarar, ne zaman risk olur?",
    "SQL Injection'ı önlemek için 3 yöntem say.",
    "Rate limiting nasıl uygulanır?",
]


def _is_unauthorized(status_code: int) -> bool:
    return status_code == 401


class UserSession:
    """
    Her sanal kullanıcı için state:
      - token
      - attempt_id / quiz_id
      - questions list
    """
    def __init__(self):
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.attempt_id: Optional[int] = None
        self.quiz_id: Optional[int] = None
        self.questions: List[Dict[str, Any]] = []
        self.correct: int = 0


class RealisticFlow(SequentialTaskSet):
    """
    Gerçek kullanıcı akışı (Sequential):
      Login -> Quiz build -> Attempt start -> (Question start/wait/end)*N -> Attempt end -> Chat (opsiyonel) -> tekrar
    """

    def on_start(self):
        self.s = UserSession()
        ok = self._login()
        if not ok:
            self.interrupt(reschedule=False)

    # -------------------------
    # Auth
    # -------------------------
    def _login(self) -> bool:
        data = {"username": USERNAME, "password": PASSWORD}
        with self.client.post(
            "/api/v1/auth/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="auth_login",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"login failed: {resp.status_code} {resp.text[:200]}")
                return False
            try:
                j = resp.json()
                token = j.get("access_token")
                if not token:
                    resp.failure("login ok but access_token missing")
                    return False
                self.s.token = token
                self.s.headers = {"Authorization": f"Bearer {token}"}
                resp.success()
                return True
            except Exception as e:
                resp.failure(f"login parse error: {e}")
                return False

    def _ensure_auth(self) -> bool:
        if self.s.token and self.s.headers:
            return True
        return self._login()

    # -------------------------
    # Helpers
    # -------------------------
    def _authed_post(self, url: str, json_body: Dict[str, Any], name: str):
        return self.client.post(
            url,
            json=json_body,
            headers={**self.s.headers, "Content-Type": "application/json"},
            name=name,
        )

    def _authed_get(self, url: str, name: str):
        return self.client.get(url, headers=self.s.headers, name=name)

    # -------------------------
    # Steps
    # -------------------------
    @task
    def step_quiz_build(self):
        """
        POST /api/v1/quiz/
        Beklenen: quiz_id + questions list döndürmesi ideal.
        """
        if not self._ensure_auth():
            self.interrupt(reschedule=False)
            return

        payload = {
            "topic": BASE_TOPIC,
            "level": BASE_LEVEL,
            "total_questions": QUIZ_N,
            "qtype": "mixed",
            "use_ollama": USE_OLLAMA_IN_QUIZ,
        }

        with self.client.post(
            "/api/v1/quiz/",
            json=payload,
            headers={**self.s.headers, "Content-Type": "application/json"},
            name="quiz_build",
            catch_response=True,
        ) as resp:
            if _is_unauthorized(resp.status_code):
                # 401 -> bir kez relogin
                if self._login():
                    resp2 = self._authed_post("/api/v1/quiz/", payload, "quiz_build")
                    if resp2.status_code >= 400:
                        resp.failure(f"retry failed: {resp2.status_code} {resp2.text[:200]}")
                        self.interrupt(reschedule=False)
                        return
                    resp.success()
                    j = resp2.json()
                else:
                    resp.failure("401 + relogin failed")
                    self.interrupt(reschedule=False)
                    return
            else:
                if resp.status_code >= 400:
                    resp.failure(f"{resp.status_code}: {resp.text[:200]}")
                    self.interrupt(reschedule=False)
                    return
                j = resp.json()
                resp.success()

        self.s.quiz_id = j.get("quiz_id") or j.get("id")
        self.s.questions = j.get("questions") or j.get("items") or []

    @task
    def step_attempt_start(self):
        """
        POST /api/v1/quiz/attempt/start
        Beklenen: attempt_id
        """
        if not self._ensure_auth():
            self.interrupt(reschedule=False)
            return

        payload = {
            "topic": BASE_TOPIC,
            "level": BASE_LEVEL,
            "total_questions": QUIZ_N,
            "quiz_id": self.s.quiz_id,
        }

        with self.client.post(
            "/api/v1/quiz/attempt/start",
            json=payload,
            headers={**self.s.headers, "Content-Type": "application/json"},
            name="quiz_attempt_start",
            catch_response=True,
        ) as resp:
            if resp.status_code >= 400:
                resp.failure(f"{resp.status_code}: {resp.text[:250]}")
                self.interrupt(reschedule=False)
                return
            try:
                j = resp.json()
            except Exception:
                resp.failure("attempt_start: json parse error")
                self.interrupt(reschedule=False)
                return

            self.s.attempt_id = j.get("attempt_id") or j.get("id")
            if not self.s.questions:
                self.s.questions = j.get("questions") or []

            resp.success()

        if not self.s.attempt_id:
            self.interrupt(reschedule=False)

    @task
    def step_questions_loop(self):
        if not self.s.attempt_id:
            self.interrupt(reschedule=False)
            return
        if not self.s.questions:
            self.interrupt(reschedule=False)
            return

        self.s.correct = 0

        for q in self.s.questions:
            qid = q.get("id") or q.get("question_id") or q.get("qid")
            if qid is None:
                continue

            qid = str(qid)

            # 1) question/start -> timing_id al
            start_payload = {
                "attempt_id": self.s.attempt_id,
                "question_id": qid,
            }

            with self.client.post(
                "/api/v1/quiz/question/start",
                json=start_payload,
                headers={**self.s.headers, "Content-Type": "application/json"},
                name="quiz_question_start",
                catch_response=True,
            ) as r1:
                if r1.status_code >= 400:
                    r1.failure(f"{r1.status_code}: {r1.text[:200]}")
                    continue
                try:
                    timing_id = r1.json().get("timing_id")
                except Exception:
                    r1.failure("question_start: json parse error")
                    continue
                if not timing_id:
                    r1.failure("timing_id missing")
                    continue
                r1.success()

            time.sleep(random.uniform(QUESTION_THINK_MIN, QUESTION_THINK_MAX))

            # (opsiyonel) basit doğru sayacı
            options = q.get("options") or q.get("choices") or []
            correct_answer = q.get("answer")
            user_answer = random.choice(options) if options else "A"
            if correct_answer is not None and str(user_answer).strip() == str(correct_answer).strip():
                self.s.correct += 1

            # 3) question/end
            end_payload = {"timing_id": int(timing_id)}

            with self.client.post(
                "/api/v1/quiz/question/end",
                json=end_payload,
                headers={**self.s.headers, "Content-Type": "application/json"},
                name="quiz_question_end",
                catch_response=True,
            ) as r2:
                if r2.status_code >= 400:
                    r2.failure(f"{r2.status_code}: {r2.text[:200]}")
                else:
                    r2.success()

    def step_optional_chat(self):
        """
        Chat'i GARANTİ çalıştırmak için @task değil.
        step_attempt_end içinde çağırıyoruz.
        """
        if not ENABLE_CHAT_LOAD:
            return
        if not self._ensure_auth():
            return

        payload = {
            "mode": "loadtest", # "playground" yerine "loadtest" (Mock LLM)
            "topic": BASE_TOPIC,
            "level": BASE_LEVEL,
            "message": random.choice(CHAT_MESSAGES),
            "history": [],
        }

        with self.client.post(
            "/api/v1/chat/turn",
            json=payload,
            headers={**self.s.headers, "Content-Type": "application/json"},
            name="chat_turn_playground",
            catch_response=True,
        ) as resp:
            # 429: Queue Full -> Fail saymayıp skip edebiliriz, ya da fail diyebiliriz.
            if resp.status_code == 429:
                resp.failure("Queue full (429)")
                return

            if _is_unauthorized(resp.status_code):
                # ... (relogin logic omit for brevity or implement if crucial)
                resp.failure("401 unauthorized in chat")
                return
            
            if resp.status_code >= 400:
                resp.failure(f"{resp.status_code}: {resp.text[:250]}")
                return

            # Başarılı cevap (200 OK)
            try:
                data = resp.json()
            except Exception:
                resp.failure("json parse error")
                return

            # Check if Queued
            job_id = data.get("job_id")
            if job_id and data.get("status") == "queued":
                # Polling start
                start_t = time.time()
                while True:
                    time.sleep(1.0) # locust gevent uyumlu sleep
                    
                    # Timeout check (e.g. 60s)
                    if time.time() - start_t > 600:
                        resp.failure(f"Polling timeout for job {job_id}")
                        break

                    with self.client.get(
                        f"/api/v1/chat/result/{job_id}",
                        headers=self.s.headers,
                        name="chat_poll_result",
                        catch_response=True
                    ) as poll_resp:
                        if poll_resp.status_code != 200:
                            poll_resp.failure(f"Poll failed: {poll_resp.status_code}")
                            break
                        
                        pdata = poll_resp.json()
                        status = pdata.get("status")
                        
                        if status == "completed":
                            # SUCCESS: We consider the whole flow done here
                            resp.success() # Asıl request success
                            poll_resp.success()
                            break
                        elif status in ("failed", "expired"):
                            resp.failure(f"Job failed: {pdata.get('error')}")
                            poll_resp.failure(f"Job failed: {pdata.get('error')}")
                            break
                        # else: still queued/started -> continue loop
            else:
                # Direct response (Fast Path)
                resp.success()

    @task
    def step_attempt_end(self):
        if not self.s.attempt_id:
            self.interrupt(reschedule=False)
            return

        correct = int(getattr(self.s, "correct", 0))
        total = max(1, len(self.s.questions) if self.s.questions else QUIZ_N)
        score = (correct / total) * 100.0

        payload = {
            "attempt_id": self.s.attempt_id,
            "correct_answers": correct,
            "score": float(score),
            "total_duration_ms": None,
            "questions_attempted": None,
        }

        with self.client.post(
            "/api/v1/quiz/attempt/end",
            json=payload,
            headers={**self.s.headers, "Content-Type": "application/json"},
            name="quiz_attempt_end",
            catch_response=True,
        ) as resp:
            if resp.status_code >= 400:
                resp.failure(f"{resp.status_code}: {resp.text[:250]}")
            else:
                resp.success()

        self._authed_get("/api/v1/quiz/attempts/recent?limit=5", "quiz_attempts_recent")

        # ✅ Chat'i burada garanti vur
        self.step_optional_chat()

        # yeni senaryoya dön
        self.interrupt(reschedule=True)


class WebsiteUser(HttpUser):
    wait_time = between(0.2, 1.0)
    tasks = [RealisticFlow]
    host = "http://localhost:8000"


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("✅ Load test started")
    print(f"   user={USERNAME} topic={BASE_TOPIC} level={BASE_LEVEL} n={QUIZ_N} chat={ENABLE_CHAT_LOAD}")
