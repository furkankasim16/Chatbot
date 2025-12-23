# app/infra/queue/enqueue.py
import time
from typing import Any, Dict, Optional
from rq import Queue
from app.infra.queue.redis_conn import redis_conn
from app.infra.queue.jobs import process_llm_turn
from app.core.config import settings

queue = Queue(settings.LLM_QUEUE_NAME, connection=redis_conn)

class QueueFullError(Exception):
    pass

def enqueue_chat_job(request_data: Dict[str, Any], user_id: int | None) -> str:
    """
    Kuyruğa iş ekler. Kuyruk doluysa hata fırlatır.
    Dönen değer: Job ID
    """
    # Load Shedding: Kuyruk uzunluğunu kontrol et
    current_len = len(queue)
    if current_len >= settings.LLM_QUEUE_MAX:
        raise QueueFullError("System is temporarily overloaded. Please try again later.")

    job = queue.enqueue(
        process_llm_turn,
        args=(request_data, user_id, time.time()),
        job_timeout=settings.LLM_CALL_TIMEOUT_SEC,
        result_ttl=300, # Sonuç 5 dk saklansın
        description=f"chat_turn_user_{user_id}"
    )
    
    return job.id

def get_job_status(job_id: str) -> Dict[str, Any]:
    job = queue.fetch_job(job_id)
    if not job:
        return {"status": "not_found"}

    state = job.get_status()
    
    # rq status: queued, started, finished, failed, deferred, scheduled
    if state == "finished":
        return job.result # jobs.py içindeki dict yapısı döner
    elif state == "failed":
        return {"status": "failed", "error": str(job.exc_info)}
    else:
        return {"status": "queued"}
