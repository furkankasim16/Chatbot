from pydantic import BaseModel, Field
from typing import List, Optional

class RubricItem(BaseModel):
    criteria: str = Field(..., description="Criteria description, e.g. 'Use of correct terminology'")
    score: int = Field(..., description="Score given for this criteria")
    max_score: int = Field(..., description="Max possible score for this criteria")
    feedback: str = Field(..., description="Specific feedback for this criteria")

class EvaluationResponse(BaseModel):
    score: float = Field(..., description="Total score (0-100)")
    is_correct: bool = Field(..., description="Pass/Fail status based on threshold")
    feedback: str = Field(..., description="Overall feedback")
    rubric: List[RubricItem] = Field(default_factory=list, description="Detailed rubric breakdown")
