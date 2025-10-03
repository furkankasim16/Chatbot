import requests, json, re, os, datetime, uuid

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gpt-oss:20b"

LEVEL_GUIDE = """
BEGINNER → Temel tanım / doğrudan pasajdan bilgi.
INTERMEDIATE → Uygulama veya süreç adımı, 1-2 adımlı çıkarım gerekebilir.
ADVANCED → Neden–sonuç, politika yorumu, soyutlama, çok adımlı düşünme.
"""

# -------------------
# Ollama çağrısı
# -------------------
def _call_ollama(prompt: str):
    try:
        res = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False, "options": {"num_ctx": 8192}},
        )
        data = res.json()
        raw = data.get("response", "")
        cleaned = raw.strip().replace("```json", "").replace("```", "")
        match = re.search(r"\{[\s\S]*\}", cleaned)
        q = json.loads(match.group(0)) if match else {"error": "JSON yok", "raw": raw}
    except Exception as e:
        q = {"error": f"Ollama hata: {str(e)}"}

    # id & created_at ekle
    if isinstance(q, dict) and "error" not in q:
        q["id"] = str(uuid.uuid4())
        q["created_at"] = datetime.datetime.utcnow().isoformat()
    return q


# -------------------
# Soru Üretim Fonksiyonları
# -------------------
def generate_mcq(passage: str, topic: str, level: str = "beginner"):
    prompt = f"""
    Sen bir eğitim soru üretici botsun.
    Aşağıdaki pasajdan 1 çoktan seçmeli (MCQ) soru üret.
    Kurallar:
    - JSON dışında hiçbir şey yazma.
    - DİL: Türkçe.
    - Seçenekler "A) ...", "B) ...", "C) ...", "D) ..." formatında olsun.
    - Zorluk seviyeleri:
    {LEVEL_GUIDE}

    JSON şeması:
    {{
      "type": "mcq",
      "topic": "{topic}",
      "level": "{level}",
      "stem": "SORU METNİ",
      "choices": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "answer_index": 1,
      "rationale": "Kısa açıklama"
    }}

    Pasaj:
    {passage}
    """
    return _call_ollama(prompt)


def generate_true_false(passage: str, topic: str, level: str = "beginner"):
    prompt = f"""
    Sen bir eğitim soru üretici botsun.
    Aşağıdaki pasajdan 1 doğru/yanlış sorusu üret.
    Kurallar:
    - JSON dışında hiçbir şey yazma.
    - DİL: Türkçe.
    - Zorluk seviyeleri:
    {LEVEL_GUIDE}

    JSON şeması:
    {{
      "type": "true_false",
      "topic": "{topic}",
      "level": "{level}",
      "stem": "SORU METNİ",
      "answer": true,
      "rationale": "Kısa açıklama"
    }}

    Pasaj:
    {passage}
    """
    return _call_ollama(prompt)


def generate_short_answer(passage: str, topic: str, level: str = "beginner"):
    prompt = f"""
    Sen bir eğitim soru üretici botsun.
    Aşağıdaki pasajdan 1 kısa cevap sorusu üret.
    Kurallar:
    - JSON dışında hiçbir şey yazma.
    - DİL: Türkçe.
    - Zorluk seviyeleri:
    {LEVEL_GUIDE}

    JSON şeması:
    {{
      "type": "short_answer",
      "topic": "{topic}",
      "level": "{level}",
      "stem": "SORU METNİ",
      "expected": "Kısa beklenen yanıt",
      "rationale": "Kısa açıklama"
    }}

    Pasaj:
    {passage}
    """
    return _call_ollama(prompt)


def generate_scenario(passage: str, topic: str, level: str = "intermediate"):
    prompt = f"""
    Sen bir eğitim soru üretici botsun.
    Aşağıdaki pasajdan 1 senaryo (çok adımlı) soru üret.
    Kurallar:
    - JSON dışında hiçbir şey yazma.
    - DİL: Türkçe.
    - Zorluk seviyeleri:
    {LEVEL_GUIDE}

    JSON şeması:
    {{
      "type": "scenario",
      "topic": "{topic}",
      "level": "{level}",
      "stem": "Durum açıklaması",
      "expected_points": ["1. adım", "2. adım"],
      "rubric": "Puanlama kuralları"
    }}

    Pasaj:
    {passage}
    """
    return _call_ollama(prompt)


# -------------------
# Loglama
# -------------------
def log_question(q: dict):
    """Her üretilen soruyu günlük JSON dosyasına logla"""
    log_dir = "data/questions/logs"
    os.makedirs(log_dir, exist_ok=True)
    today = datetime.date.today().isoformat()
    with open(f"{log_dir}/{today}.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")
