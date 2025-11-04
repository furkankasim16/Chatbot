import os
import io
import json
from pathlib import Path
import datetime
import re
import ollama

from src.rag import extract_text_from_file
from src.question import save_question, question_hash
from src.utils import evaluate_quality

# ===========================
# Ayarlar
# ===========================
CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "generator_log.txt"
MODEL = "phi3:medium"
MAX_TEXT_LEN = 8000

# ===========================
# Yardımcılar
# ===========================
def log(message: str):
    """Zaman damgalı log kaydı."""
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")
    print(message)

def fix_json_output(text: str) -> str:
    """Modelin bozuk JSON çıktısını olabildiğince düzeltir."""
    if not text:
        return "[]"

    clean = (
        text.replace("```json", "")
            .replace("```", "")
            .replace("\r", "")
            .strip()
    )

    # Fazla açıklama satırlarını at
    clean = re.sub(r"^[^{\[]+", "", clean)
    clean = re.sub(r"[^}\]]+$", "", clean)

    # Eksik virgülleri düzelt ("A)" "B)" arası)
    clean = re.sub(r'"\s+"', '", "', clean)
    # Eksik tırnakları onar
    clean = clean.replace("“", '"').replace("”", '"')

    # JSON listesi değilse sarmala
    if not clean.startswith("["):
        clean = "[" + clean
    if not clean.endswith("]"):
        clean += "]"
    return clean

def safe_json_loads(text: str):
    """JSON'u parse etmeyi dener, olmazsa fallback olarak soru listesi üretir."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]
        else:
            raise ValueError("Liste veya dict bekleniyordu")
    except Exception:
        # fallback: satır bazlı soru çıkarımı
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 10]
        questions = []
        for line in lines:
            if "?" in line:
                questions.append({
                    "question": line.split("?")[0].strip() + "?",
                    "options": [],
                    "answer": ""
                })
        return questions if questions else [{
            "question": text[:150],
            "options": [],
            "answer": ""
        }]

# ===========================
# Dosyadan Soru Üretme
# ===========================
def generate_questions_from_file(filepath: Path, topic: str):
    log(f"📘 {filepath.name} ({topic}) dosyasından sorular üretiliyor...")

    with open(filepath, "rb") as f:
        raw = f.read()

    text = extract_text_from_file(filepath.name, raw)
    if not text or len(text.strip()) < 50:
        log("⚠️ Dosya metni çok kısa veya okunamadı, atlandı.")
        return []

    if filepath.suffix.lower() == ".xlsx":
        log("⚠️ Excel dosyaları genellikle tablo içerir, model doğrudan anlamlı soru üretemeyebilir.")

    text = text[:MAX_TEXT_LEN]

    prompt = f"""
    Sen QuizBot adında bir eğitim asistanısın.
    Görevin, aşağıdaki metinden anlamlı ve açık Türkçe çoktan seçmeli sorular üretmektir.
    Kurallar:
    - Sadece verilen metindeki bilgilerden yararlan.
    - Sorular doğal Türkçe ile yazılmalı, anlamlı ve özgün olmalı.
    - Her soruda 3 seçenek olmalı (A, B, C).
    - Cevapları doğru şekilde işaretle.
    - Format:
    [
      {{
        "question": "...",
        "options": ["A) ...", "B) ...", "C) ..."],
        "answer": "A)"
      }},
      ...
    ]
    ÖNEMLİ:
    - Çıktını yalnızca JSON formatında döndür.
    - ```json veya ``` ekleme.
    - Yanıt [ ile başlamalı, ] ile bitmeli.

    Konu: {topic}
    ---
    {text}
    ---
    """

    try:
        response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}])
        content = response.get("message", {}).get("content", "").strip()
        log(f"📄 Model yanıtı ({filepath.name}): {content[:200]}...")

        clean = fix_json_output(content)
        questions = safe_json_loads(clean)

    except Exception as e:
        log(f"❌ Ollama çağrısı başarısız: {e}")
        return []

    valid_questions = []
    for q in questions:
        if not isinstance(q, dict):
            log(f"⚠️ Beklenmeyen veri tipi ({filepath.name}): {type(q)} -> {q}")
            continue
        if "question" not in q or not isinstance(q["question"], str):
            log(f"⚠️ Soru alanı geçersiz ({filepath.name}): {q}")
            continue

        q["topic"] = topic
        q["quality_score"] = evaluate_quality(q["question"])

        try:
            q["hash"] = question_hash(q["question"])
        except Exception as e:
            log(f"❌ Hash oluşturulamadı ({filepath.name}): {e}")
            q["hash"] = "error_hash"

        valid_questions.append(q)
        log(f"✅ Soru işlendi: {q['question'][:80]} (skor={q['quality_score']})")

    return valid_questions

# ===========================
# Ana Çalıştırıcı
# ===========================
def main():
    if not CORPUS_DIR.exists():
        log(f"❌ Klasör bulunamadı: {CORPUS_DIR}")
        return

    all_questions = []
    for topic_dir in CORPUS_DIR.iterdir():
        if not topic_dir.is_dir():
            continue
        topic = topic_dir.name
        for file in topic_dir.iterdir():
            if not file.is_file():
                continue
            questions = generate_questions_from_file(file, topic)
            for q in questions:
                if q.get("quality_score", 0) >= 0.65:
                    save_question(q)
                    all_questions.append(q)

    log(f"\n🎯 Tamamlandı! Toplam {len(all_questions)} kaliteli soru kaydedildi.\n")


if __name__ == "__main__":
    main()
