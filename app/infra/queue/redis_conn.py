# app/infra/queue/redis_conn.py
import redis
from app.core.config import settings

def get_redis_conn():
    return redis.from_url(settings.REDIS_URL)

redis_conn = get_redis_conn()
