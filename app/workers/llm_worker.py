# app/workers/llm_worker.py
import sys
import os

# "app" modülünü bulabilmesi için projeyi sys.path'e ekliyoruz (gerekirse)
sys.path.append(os.getcwd())

from rq import SimpleWorker, Queue
from app.infra.queue.redis_conn import redis_conn
from app.core.config import settings

def start_worker():
    listen = [settings.LLM_QUEUE_NAME]
    
    print(f"🚀 Worker starting... Listening on: {listen}")
    print(f"Redis: {settings.REDIS_URL}")
    print("ℹ️  Running in WINDOWS mode (SimpleWorker)")

    # Explicitly pass connection to Queues
    queues = [Queue(name, connection=redis_conn) for name in listen]

    # Use SimpleWorker on Windows (no fork)
    worker = SimpleWorker(queues, connection=redis_conn)
    worker.work()

if __name__ == "__main__":
    start_worker()
