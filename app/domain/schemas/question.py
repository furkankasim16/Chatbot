# app/domain/schemas/question.py

from enum import Enum
from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field

# --- enums ---

class QuestionType(str, Enum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    OPEN_ENDED = "open_ended"
    SHORT_ANSWER = "short_answer"
    SCENARIO = "scenario"

class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class ShortAnswerMatchingType(str, Enum):
    EXACT = "exact"
    CASE_INSENSITIVE = "case_insensitive"
    CONTAINS = "contains"
    REGEX = "regex"

# --- base ---

class BaseQuestion(BaseModel):
    id: Optional[int] = None
    question_type: QuestionType
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    tags: List[str] = Field(default_factory=list)
    stem: str
    explanation: Optional[str] = None
    max_score: float = 1.0

# --- tek adımlılar (mcq / tf / short / open) ---

class MCQQuestion(BaseQuestion):
    question_type: Literal[QuestionType.MCQ] = QuestionType.MCQ
    options: List[str]
    correct_option_indexes: List[int]

class TrueFalseQuestion(BaseQuestion):
    question_type: Literal[QuestionType.TRUE_FALSE] = QuestionType.TRUE_FALSE
    correct_answer: bool

class ShortAnswerQuestion(BaseQuestion):
    question_type: Literal[QuestionType.SHORT_ANSWER] = QuestionType.SHORT_ANSWER
    accepted_answers: List[str]
    matching_type: ShortAnswerMatchingType = ShortAnswerMatchingType.CASE_INSENSITIVE

class OpenEndedQuestion(BaseQuestion):
    question_type: Literal[QuestionType.OPEN_ENDED] = QuestionType.OPEN_ENDED
    rubric: Optional[str] = None

# --- scenario / çok adımlı ---

class StepQuestion(BaseModel):
    step_id: int
    step_type: QuestionType  # mcq/true_false/short_answer/open_ended
    stem: str
    max_score: float = 1.0
    options: Optional[List[str]] = None
    correct_option_indexes: Optional[List[int]] = None
    correct_answer_bool: Optional[bool] = None
    accepted_answers: Optional[List[str]] = None
    matching_type: Optional[ShortAnswerMatchingType] = None
    rubric: Optional[str] = None

class ScenarioQuestion(BaseQuestion):
    question_type: Literal[QuestionType.SCENARIO] = QuestionType.SCENARIO
    scenario: str
    steps: List[StepQuestion]
    total_score: float

QuestionModel = Union[
    MCQQuestion,
    TrueFalseQuestion,
    ShortAnswerQuestion,
    OpenEndedQuestion,
    ScenarioQuestion,
]
