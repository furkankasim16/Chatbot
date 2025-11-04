from pydantic import BaseModel
from typing import List, Optional

class Question(BaseModel):
    id: Optional[int] = None
    hash: Optional[str] = None
    type: str
    topic: str
    level: str
    stem: str
    choices: Optional[List[str]] = None
    answer_index: Optional[int] = None
    rationale: Optional[str] = None
    source_model: Optional[str] = None
