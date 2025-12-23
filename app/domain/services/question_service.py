# app/domain/services/question_service.py

"""
Compatibility shim & facade service.

Eskiden question_service altında olan fonksiyonlar artık
question_generation altında. Ancak admin paneli ve diğer modüller
question_service'i import ettiği için, burası sadece bir
"geçit/facade" görevi görür.
"""

import random
from typing import Tuple, Dict, Any

from app.domain.services.question_generation import (
    generate_question_from_llm,
    pick_random_topic_and_level as _pick_random_topic_and_level,
)
from app.domain.schemas.question import QuestionModel


def pick_random_topic_and_level() -> Tuple[str, str]:
    """Admin paneli için."""
    return _pick_random_topic_and_level()


async def generate_question(
    model_name: str,
    params: Dict[str, Any],
    save: bool = True,
) -> QuestionModel:
    """Eski generate_question çağrılarını yeni fonksiyona yönlendirir."""
    return await generate_question_from_llm(model_name, params, save=save)
