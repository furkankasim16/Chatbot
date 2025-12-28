import json
import asyncio
import sys
import os
import argparse

# App context
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.repositories.quesitons_repo import add_question
from app.domain.schemas.question import (
    MCQQuestion, TrueFalseQuestion, ShortAnswerQuestion, OpenEndedQuestion, ScenarioQuestion,
    QuestionType, DifficultyLevel, StepQuestion, ShortAnswerMatchingType
)

def map_difficulty(d_str: str) -> DifficultyLevel:
    d = d_str.lower()
    if d == "easy": return DifficultyLevel.EASY
    if d == "hard": return DifficultyLevel.HARD
    return DifficultyLevel.MEDIUM

def main():
    parser = argparse.ArgumentParser(description="Import questions from JSON file")
    parser.add_argument("file", help="Path to JSON file")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        return

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Invalid JSON: {e}")
        return

    if not isinstance(data, list):
        print("❌ JSON root must be a list of question objects.")
        return

    count = 0
    for i, item in enumerate(data):
        try:
            qtype = item.get("question_type", "mcq")
            topic = item.get("topic", "general")
            difficulty = map_difficulty(item.get("difficulty", "medium"))
            stem = item.get("stem", "Question?")
            explanation = item.get("explanation")
            source_context = item.get("source_context")
            
            model = None

            if qtype == "mcq":
                opts = item.get("options_json", [])
                if isinstance(opts, str):
                    try:
                        opts = json.loads(opts)
                    except:
                        opts = [] # Fallback
                # Handle "correct_answer_json": "0" -> [0]
                idx_str = item.get("correct_answer_json", "0")
                try:
                    idx = int(idx_str)
                except:
                    idx = 0
                
                model = MCQQuestion(
                    topic=topic,
                    difficulty=difficulty,
                    stem=stem,
                    explanation=explanation,
                    source_context=source_context,
                    options=opts,
                    correct_option_indexes=[idx],
                    question_type=QuestionType.MCQ
                )

            elif qtype == "true_false":
                # Handle "correct_answer_json": "1" -> False? Or 1=index? 
                # User sample: "Dodru", "Yanlis" -> index 1 ("Yanlis") -> Correct is False?
                # Wait, schema uses `correct_answer: bool`.
                # If index is used: 0=True, 1=False usually? 
                # Let's assume user provides INDEX as string. 
                idx_str = item.get("correct_answer_json", "0")
                is_true = True
                if idx_str == "1": is_true = False # "Yanlış" selected
                
                model = TrueFalseQuestion(
                    topic=topic,
                    difficulty=difficulty,
                    stem=stem,
                    explanation=explanation,
                    source_context=source_context,
                    correct_answer=is_true,
                    question_type=QuestionType.TRUE_FALSE
                )
            
            elif qtype == "short_answer":
                ans_text = item.get("correct_answer_json", "")
                model = ShortAnswerQuestion(
                    topic=topic,
                    difficulty=difficulty,
                    stem=stem,
                    explanation=explanation,
                    source_context=source_context,
                    accepted_answers=[ans_text],
                    matching_type=ShortAnswerMatchingType.CONTAINS, # Default to contains for safety
                    question_type=QuestionType.SHORT_ANSWER
                )

            elif qtype == "open_ended":
                ans_text = item.get("correct_answer_json", "")
                # Store ideal answer in explanation or rubric? 
                # Schema has rubric: Optional[str]. We can put it there JSONified or plain.
                rubric_data = [
                    {"criteria": "Doğruluk", "score": 10, "description": "Cevap şu bilgileri içermeli: " + ans_text}
                ]
                import json as j
                
                model = OpenEndedQuestion(
                    topic=topic,
                    difficulty=difficulty,
                    stem=stem,
                    explanation=explanation,
                    source_context=source_context,
                    rubric=j.dumps(rubric_data, ensure_ascii=False),
                    question_type=QuestionType.OPEN_ENDED
                )
            
            elif qtype == "scenario":
                # User provided flat scenario, we map to ScenarioQuestion with 1 step
                scenario_text = item.get("scenario", "")
                ans_text = item.get("correct_answer_json", "")
                
                step = StepQuestion(
                    step_id=1,
                    step_type=QuestionType.OPEN_ENDED,
                    stem=stem, # The specific question part
                    rubric=json.dumps([{"criteria": "Analiz", "score": 10, "expected": ans_text}], ensure_ascii=False)
                )

                model = ScenarioQuestion(
                    topic=topic,
                    difficulty=difficulty,
                    stem=stem, # Main stem usually empty for scenario or title? Schema says stem is required.
                    explanation=explanation,
                    source_context=source_context,
                    scenario=scenario_text,
                    steps=[step],
                    total_score=10,
                    question_type=QuestionType.SCENARIO
                )

            if model:
                add_question(model)
                count += 1
                print(f"✅ Imported: {stem[:50]}...")
            else:
                print(f"⚠️ Skipped unknown type: {qtype}")

        except Exception as e:
            print(f"❌ Error importing item {i}: {e}")

    print(f"✨ Import complete. Added {count} questions.")

if __name__ == "__main__":
    main()
