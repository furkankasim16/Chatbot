# app/domain/services/llm/validators.py

from typing import Any, Dict


class QuestionValidationError(Exception):
    """MCQ validasyonu başarısız olduğunda fırlatılır."""
    pass


def validate_question_schema(mcq: Dict[str, Any]) -> None:
    """
    parse_and_normalize_mcq() sonrasında,
    DB'ye kaydedilmeden önce soru şemasını doğrular.
    """
    required_keys = ["question", "options", "correct_option_index", "explanation"]
    for key in required_keys:
        if key not in mcq:
            raise QuestionValidationError(f"Eksik alan: {key}")

    question = mcq["question"]
    if not isinstance(question, str):
        raise QuestionValidationError("question alanı string olmalı.")
    if len(question.strip()) < 5:
        raise QuestionValidationError("Soru çok kısa (5 karakterden az).")
    if len(question.strip()) > 500:
        raise QuestionValidationError("Soru çok uzun (500 karakteri geçiyor).")

    options = mcq["options"]
    if not isinstance(options, list):
        raise QuestionValidationError("options bir liste olmalı.")
    if len(options) != 4:
        raise QuestionValidationError("options listesi tam olarak 4 eleman içermeli.")

    for i, opt in enumerate(options):
        if not isinstance(opt, str):
            raise QuestionValidationError(f"Seçenek {i} string değil.")
        if len(opt.strip()) < 1:
            raise QuestionValidationError(f"Seçenek {i} boş.")
        if len(opt.strip()) > 200:
            raise QuestionValidationError(f"Seçenek {i} çok uzun (200 karakter).")

    coi = mcq["correct_option_index"]
    if not isinstance(coi, int):
        raise QuestionValidationError("correct_option_index bir integer olmalı.")
    if not (0 <= coi < 4):
        raise QuestionValidationError("correct_option_index 0–3 arasında olmalı.")

    explanation = mcq["explanation"]
    if not isinstance(explanation, str):
        raise QuestionValidationError("explanation string olmalı.")
    if len(explanation.strip()) < 5:
        raise QuestionValidationError("Açıklama çok kısa.")
    if len(explanation.strip()) > 800:
        raise QuestionValidationError("Açıklama çok uzun (800 karakter).")

    if len(set(o.lower().strip() for o in options)) < 4:
        raise QuestionValidationError("Seçenekler çok benzer veya tamamen aynı.")

    correct = options[coi].lower()
    if correct in question.lower():
        raise QuestionValidationError("Soru kökünde doğru cevaba dair ipucu bulunuyor.")