# app/core/ollama_limiter.py
from __future__ import annotations

import os
import time
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_str(name: str, default: str) -> str:
    return (os.getenv(name, default) or default).strip().lower()


@dataclass
class AcquireResult:
    acquired: bool
    waited_ms: int = 0
    enabled: bool = True


class OllamaLimiter:
    """
    max_concurrency = 0 -> limiter kapalı (passthrough)
    overload_mode:
      - reject: doluysa acquire etmez (429 döndürebilirsin)
      - wait: müsait olana kadar bekler
    """
    def __init__(self, max_concurrency: int, overload_mode: str = "reject"):
        self.max_concurrency = int(max_concurrency)
        self.overload_mode = overload_mode
        self.enabled = self.max_concurrency > 0
        self._sem = asyncio.Semaphore(self.max_concurrency) if self.enabled else None

    async def try_acquire(self) -> AcquireResult:
        if not self.enabled:
            return AcquireResult(acquired=True, waited_ms=0, enabled=False)

        if self.overload_mode == "wait":
            t0 = time.perf_counter()
            await self._sem.acquire()
            waited = int((time.perf_counter() - t0) * 1000)
            return AcquireResult(acquired=True, waited_ms=waited, enabled=True)

        # reject
        try:
            self._sem.acquire_nowait()
            return AcquireResult(acquired=True, waited_ms=0, enabled=True)
        except Exception:
            return AcquireResult(acquired=False, waited_ms=0, enabled=True)

    def release(self) -> None:
        if not self.enabled:
            return
        try:
            self._sem.release()
        except Exception:
            pass

    @asynccontextmanager
    async def slot(self):
        res = await self.try_acquire()
        try:
            yield res
        finally:
            if res.acquired and res.enabled:
                self.release()


OLLAMA_MAX_CONCURRENCY = _env_int("OLLAMA_MAX_CONCURRENCY", 0)  # 0 = kapalı
OLLAMA_OVERLOAD_MODE = _env_str("OLLAMA_OVERLOAD_MODE", "reject")

ollama_limiter = OllamaLimiter(
    max_concurrency=OLLAMA_MAX_CONCURRENCY,
    overload_mode=OLLAMA_OVERLOAD_MODE,
)
