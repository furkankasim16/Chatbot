
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
    is_success: bool = True

class LLMStatsSummary(BaseModel):
    model_name: str
    total_calls: int
    avg_latency_ms: Optional[float]
    min_latency_ms: Optional[int]
    max_latency_ms: Optional[int]
    avg_input_tokens: Optional[float]
    avg_output_tokens: Optional[float]
    success_calls: Optional[int] = 0
    success_rate: Optional[float] = 0.0
