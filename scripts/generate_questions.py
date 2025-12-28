
import asyncio
import argparse
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.domain.services.llm_service import generate_batch, LLMModel
from app.core.db import questions_cursor
from app.domain.repositories.quesitons_repo import add_question
from app.domain.schemas.question import (
    MCQQuestion, OpenEndedQuestion, QuestionType, DifficultyLevel
)

async def main():
    parser = argparse.ArgumentParser(description="Bulk Generate Questions")
    parser.add_argument("--topic", type=str, required=True, help="Topic for questions")
    parser.add_argument("--n", type=int, default=10, help="Number of questions to generate")
    parser.add_argument("--level", type=str, default="beginner", help="Difficulty level")
    parser.add_argument("--qtype", type=str, default="mcq", help="Question type (mcq, open, or mixed)")
    parser.add_argument("--clean", action="store_true", help="Delete existing questions for this topic first")
    parser.add_argument("--clean-all", action="store_true", help="Delete ALL questions in DB first")
    args = parser.parse_args()

    # 1. Clean if requested
    if args.clean_all:
        print("🗑️  Deleting ALL questions from database...")
        with questions_cursor() as c:
            c.execute("DELETE FROM questions")
        print("✅ Database wiped clean.")
    
    elif args.clean:
        print(f"🗑️  Deleting existing questions for topic: {args.topic}...")
        with questions_cursor() as c:
            c.execute("DELETE FROM questions WHERE topic = ?", (args.topic,))
        print("✅ Topic cleared.")

    # 2. Determine batches
    tasks = []
    if args.qtype == "mixed":
        n_open = int(args.n * 0.3) # 30% open-ended
        n_mcq = args.n - n_open
        if n_mcq > 0:
            tasks.append(("mcq", n_mcq))
        if n_open > 0:
            tasks.append(("open", n_open))
    else:
        tasks.append((args.qtype, args.n))

    # 2.5 Fetch existing stems for avoidance/diversity
    existing_stems = []
    try:
        with questions_cursor() as c:
            c.execute("SELECT stem FROM questions WHERE topic = ?", (args.topic,))
            rows = c.fetchall()
            existing_stems = [r[0] for r in rows if r[0]]
            print(f"ℹ️ Found {len(existing_stems)} existing questions for topic. Will use for diversity.")
    except Exception as e:
        print(f"⚠️ Failed to fetch existing questions: {e}")

    # 3. Generate Loop
    all_questions = []
    import random
    
    # Difficulty levels to cycle through
    difficulties = ["beginner", "intermediate", "advanced"]
    
    for qtype, count in tasks:
        # We proceed in smaller micro-batches to vary params
        batch_size = 5
        generated_count = 0
        
        while generated_count < count:
             current_batch_size = min(batch_size, count - generated_count)
             
             # Pick random difficulty
             current_level = random.choice(difficulties)
             if args.level != "beginner": # If user forced a level, use it
                  current_level = args.level
             
             # Avoid loop: Pick random subset of existing questions to avoid (Large sample)
             current_avoid = list(existing_stems) + [q.get("question") for q in all_questions]
             subset_avoid = current_avoid[-150:] 
             if len(subset_avoid) > 30:
                 subset_avoid = random.sample(subset_avoid, 30)

             print(f"🚀 Generating {current_batch_size} questions for '{args.topic}' [Type: {qtype}, Level: {current_level}]...")
             
             batch = await generate_batch(
                 topic=args.topic,
                 level=current_level,
                 n=current_batch_size,
                 qtype=qtype,
                 model=LLMModel.OLLAMA_LOCAL,
                 avoid_questions=subset_avoid
             )
             
             if batch:
                 all_questions.extend(batch)
                 generated_count += len(batch)
             else:
                 print("⚠️ Batch generation returned empty or failed.")
    
    if not all_questions:
        print("❌ Generation failed or returned empty.")
        return

    # 4. Insert into DB using Repo
    print(f"💾 Saving {len(all_questions)} questions to DB...")
    
    count = 0
    for q in all_questions:
        try:
            # Map difficulty string to Enum
            diff_str = q.get("level", "beginner").upper()
            if diff_str == "BEGINNER": difficulty = DifficultyLevel.EASY
            elif diff_str == "INTERMEDIATE": difficulty = DifficultyLevel.MEDIUM
            elif diff_str == "ADVANCED": difficulty = DifficultyLevel.HARD
            else: difficulty = DifficultyLevel.MEDIUM

            # Create Question Model
            if q.get("qtype") == "open":
                # Open Ended
                model = OpenEndedQuestion(
                    topic=q.get("topic"),
                    difficulty=difficulty,
                    question_type=QuestionType.OPEN_ENDED,
                    stem=q.get("question"),
                    rubric=[
                        {"criteria": "Doğruluk", "score": 5},
                        {"criteria": "Detay", "score": 5}
                    ], # Default rubric
                    explanation=q.get("explanation"),
                    source_model=q.get("meta", {}).get("source")
                )
            else:
                # MCQ Default
                model = MCQQuestion(
                    topic=q.get("topic"),
                    difficulty=difficulty,
                    question_type=QuestionType.MCQ,
                    stem=q.get("question"),
                    options=q.get("options", []),
                    correct_option_indexes=[q.get("answer_index", 0)],
                    explanation=q.get("explanation"),
                    source_model=q.get("meta", {}).get("source")
                )
            
            # Add to DB
            add_question(model)
            count += 1
            
        except Exception as e:
            print(f"⚠️ Failed to insert question: {e}")

    print(f"✨ Done! {count} new questions added successfully.")

if __name__ == "__main__":
    asyncio.run(main())
