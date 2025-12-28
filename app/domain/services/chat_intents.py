import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class QuizIntent:
    n: int = 5
    qtype: str = "mcq"         # mcq | true_false | short_answer | open_ended | scenario
    topic: Optional[str] = None
    level: Optional[str] = None

QUIZ_WORDS = {"quiz", "soru", "soruluk", "test"}

def parse_quiz_intent(text: str) -> Optional[QuizIntent]:
    t = text.strip().lower()

    # Hızlı eleme
    if not any(w in t for w in QUIZ_WORDS) and not re.search(r"\b\d+\s*(soru|question)\b", t):
        return None

    intent = QuizIntent()

    # n: "5 soru", "10 question"
    m = re.search(r"\b(\d+)\s*(soru|question)\b", t)
    if m:
        intent.n = max(1, min(50, int(m.group(1))))

    # qtype
    if "true_false" in t or "doğru yanlış" in t or "dogru yanlis" in t:
        intent.qtype = "true_false"
    elif "short_answer" in t or "kısa" in t or "kisa" in t:
        intent.qtype = "short_answer"
    elif "open_ended" in t or "açık uçlu" in t or "acik uclu" in t:
        intent.qtype = "open_ended"
    elif "scenario" in t or "senaryo" in t:
        intent.qtype = "scenario"
    elif "mcq" in t or "çoktan" in t or "coktan" in t:
        intent.qtype = "mcq"

    # topic/level varsa (basit): "topic=security_policy", "level=beginner"
    mt = re.search(r"\btopic\s*=\s*([a-z0-9_\-]+)\b", t)
    if mt:
        intent.topic = mt.group(1)

    ml = re.search(r"\blevel\s*=\s*([a-z0-9_\-]+)\b", t)
    if ml:
        intent.level = ml.group(1)

    return intent

GREETINGS = {
    "selam", "slm", "merhaba", "mrh", "selamlar", "günaydın", "iyi akşamlar",
    "hi", "hello", "hey",
}

def parse_greeting_intent(user_message: str) -> Optional[str]:
    """
    Basit selamlaşma kontrolü.
    """
    msg = user_message.lower().strip()
    
    # Direkt eşleşmeler
    if msg in GREETINGS:
        return "greeting"
        
    # Kelime bazlı kontrol (daha esnek)
    # "selam naber", "merhaba nasılsın" gibi
    words = set(msg.split())
    if words.intersection(GREETINGS):
        return "greeting"
        
    # Naber/Nasılsın/İyi misin check
    common_starters = ["naber", "nasılsın", "nasilsin", "iyi misin", "ne haber"]
    for s in common_starters:
        if s in msg:
            return "greeting"
            
    return None
