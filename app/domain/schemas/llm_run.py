# app/domain/schemas/llm_run.py

from pydantic import BaseModel
from typing import Optional


class LLMRun(BaseModel):
    id: Optional[int] = None
    model_name: str
    prompt_hash: Optional[str] = None
    latency_ms: int
    token_input: Optional[int] = None
    token_output: Optional[int] = None
    created_at: Optional[str] = None
