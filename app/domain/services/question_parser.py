from typing import Any, Dict

from app.domain.schemas.question import (
    QuestionModel,
    QuestionType,
    DifficultyLevel,
    ShortAnswerMatchingType,
    MCQQuestion,
    TrueFalseQuestion,
    ShortAnswerQuestion,
    OpenEndedQuestion,
    ScenarioQuestion,
    StepQuestion,
)


def _normalize_difficulty(value: str) -> DifficultyLevel:
    value = (value or "").lower()
    if value not in {"easy", "medium", "hard"}:
        return DifficultyLevel.MEDIUM
    return DifficultyLevel(value)


def parse_llm_question_payload(payload: Dict[str, Any]) -> QuestionModel:
    """
    LLM'in ürettiği JSON payload'ını uygun QuestionModel objesine dönüştürür.
    """
    qtype = QuestionType(payload["question_type"])

    base = dict(
        topic=payload.get("topic"),
        subtopic=payload.get("subtopic"),
        difficulty=_normalize_difficulty(payload.get("difficulty")),
        tags=payload.get("tags") or [],
        stem=payload["stem"],
        explanation=payload.get("explanation"),
        max_score=float(payload.get("max_score") or 1.0),
    )

    # ---- MCQ ----
    if qtype == QuestionType.MCQ:
        return MCQQuestion(
            question_type=qtype,
            options=payload["options"],
            correct_option_indexes=payload["correct_option_indexes"],
            **base,
        )

    # ---- TRUE/FALSE ----
    if qtype == QuestionType.TRUE_FALSE:
        return TrueFalseQuestion(
            question_type=qtype,
            correct_answer=payload["correct_answer"],
            **base,
        )

    # ---- SHORT ANSWER ----
    if qtype == QuestionType.SHORT_ANSWER:
        return ShortAnswerQuestion(
            question_type=qtype,
            accepted_answers=payload["accepted_answers"],
            matching_type=ShortAnswerMatchingType(
                payload.get("matching_type", "case_insensitive")
            ),
            **base,
        )

    # ---- OPEN ENDED ----
    if qtype == QuestionType.OPEN_ENDED:
        return OpenEndedQuestion(
            question_type=qtype,
            rubric=payload.get("rubric"),
            **base,
        )

    # ---- SCENARIO ----
    if qtype == QuestionType.SCENARIO:
        steps = []
        for idx, s in enumerate(payload["steps"], 1):
            steps.append(
                StepQuestion(
                    step_id=s.get("step_id", idx),
                    step_type=QuestionType(s["step_type"]),
                    stem=s["stem"],
                    max_score=s.get("max_score", 1.0),
                    options=s.get("options"),
                    correct_option_indexes=s.get("correct_option_indexes"),
                    correct_answer_bool=s.get("correct_answer_bool"),
                    accepted_answers=s.get("accepted_answers"),
                    matching_type=(
                        ShortAnswerMatchingType(s["matching_type"])
                        if s.get("matching_type")
                        else None
                    ),
                    rubric=s.get("rubric"),
                )
            )

        return ScenarioQuestion(
            question_type=qtype,
            scenario=payload["scenario"],
            steps=steps,
            total_score=payload.get("total_score") or sum(s.max_score for s in steps),
            **base,
        )

    raise ValueError(f"Unsupported question_type: {qtype}")
