# app/domain/services/llm/prompts.py

def build_gemini_mcq_prompt(
    topic: str,
    level: str,
    audience_description: str = "University-level computer engineering students",
) -> str:
    return f"""
You are an assessment item generator for an educational quiz platform.

Your task:
- Generate EXACTLY ONE multiple-choice question (MCQ).
- The topic is: "{topic}"
- The difficulty level is: "{level}"  (e.g., beginner, intermediate, advanced)
- The target audience: {audience_description}

Language requirements:
- The "question", "options", and "explanation" fields MUST be in Turkish.
- The JSON keys (question, options, correct_option_index, explanation) MUST remain in English.

Question requirements:
- The question must be clear, unambiguous, and technically correct.
- The question must be relevant to the given topic and difficulty.
- The question must have exactly 4 answer options.
- Only one option must be correct.
- The other options must be plausible but clearly wrong for an expert.

Output format (VERY IMPORTANT):
- You MUST output a single valid JSON object.
- Do NOT include Markdown, backticks, explanations, comments, or additional text.
- Do NOT wrap JSON in ```json or any other markers.
- Do NOT include any field other than the ones defined below.

The ONLY allowed JSON schema is:

{{
  "question": "string",
  "options": ["string", "string", "string", "string"],
  "correct_option_index": 0,
  "explanation": "string"
}}

Strict rules:
- "options" MUST have length 4.
- "correct_option_index" MUST be 0, 1, 2, or 3.
- "explanation" MUST explain why the correct option is correct and why the others are wrong.
- Do NOT generate more than one question.
- Do NOT include any keys that are not listed in the schema.
- Do NOT include trailing commas.

Now generate the JSON.
""".strip()

def build_groq_mcq_prompt(topic: str, level: str) -> str:
    return f"""
You are a question generator.

Return ONLY a single JSON object, nothing else. No explanation outside JSON, no markdown.
And the questions and answers must be in Turkish.

Format exactly:

{{
  "question": "string",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "correct_option_index": 0,
  "explanation": "string"
}}

Requirements:
- Exactly 4 options.
- correct_option_index must be 0, 1, 2 or 3.
- Do NOT write any text before or after the JSON.

Topic: {topic}
Level: {level}
Question type: mcq
""".strip()