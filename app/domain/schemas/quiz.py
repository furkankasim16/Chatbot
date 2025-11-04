# app/domain/schemas/quiz.py
from pydantic import BaseModel
from typing import Optional

class QuizStartIn(BaseModel):
    user_id: int
    topic: str
    difficulty: str
    total_questions: int
    start_time: str

class QuizEndIn(BaseModel):
    attempt_id: int
    end_time: str
    correct_answers: int
    score: float
    total_duration_ms: int
    questions_attempted: str

class QuestionTimingIn(BaseModel):
    attempt_id: int
    question_id: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: Optional[int] = None

class TimeEventIn(BaseModel):
    attempt_id: int
    event_type: str
    ts: str
    meta_json: Optional[str] = None
