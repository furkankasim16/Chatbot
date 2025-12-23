from fastapi import APIRouter, Depends
from typing import List, Optional
from pydantic import BaseModel
from app.domain.repositories.llm_run_repo import get_llm_stats_summary

router = APIRouter(prefix="/admin", tags=["admin-llm-stats"])


class LLMStatsSummary(BaseModel):
    model_name: str
    total_calls: int
    avg_latency_ms: Optional[float]
    min_latency_ms: Optional[int]
    max_latency_ms: Optional[int]
    avg_input_tokens: Optional[float]
    avg_output_tokens: Optional[float]


@router.get("/llm-stats/summary", response_model=List[LLMStatsSummary])
def llm_stats_summary() -> List[LLMStatsSummary]:
    """
    LLM model bazlı performans özeti:
    - total_calls
    - avg/min/max latency
    - avg input/output tokens
    """
    try:
        stats = get_llm_stats_summary()
        return [LLMStatsSummary(**row) for row in stats]
    except Exception as e:
        import traceback
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Stats Error: {str(e)}")
