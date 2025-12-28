# app/domain/services/llm/normalizers.py

import json
import re
from typing import Any, Dict


# ------------------ Validation ------------------ #

class QuestionValidationError(Exception):
    """MCQ validasyonu başarısız olduğunda fırlatılır."""
    pass


def validate_question_schema(mcq: Dict[str, Any]) -> None:
    """
    parse_and_normalize_mcq() sonrasında,
    DB'ye kaydedilmeden önce soru şemasını doğrular.

    Geçerli değilse QuestionValidationError fırlatır.
    """

    # 1) Temel alan kontrolü
    # 1) Temel alan kontrolü
    # Open Ended veya MCQ ayırımı yapalım
    is_open_ended = "answer" in mcq and "options" not in mcq
    
    if is_open_ended:
        required_keys = ["question", "answer", "explanation"]
    else:
        required_keys = ["question", "options", "correct_option_index", "explanation"]

    for key in required_keys:
        if key not in mcq:
            raise QuestionValidationError(f"Eksik alan: {key}")

    # 2) question alanı
    question = mcq["question"]
    if not isinstance(question, str):
        raise QuestionValidationError("question alanı string olmalı.")
    if len(question.strip()) < 5:
        raise QuestionValidationError("Soru çok kısa (5 karakterden az).")
    if len(question.strip()) > 1000:
        raise QuestionValidationError("Soru çok uzun (1000 karakteri geçiyor).")
    
    if is_open_ended:
        # Open Ended ise options kontrolünü atla
        return

    # 3) options
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
        if len(opt.strip()) > 300:
            raise QuestionValidationError(f"Seçenek {i} çok uzun (300 karakter).")

    # 4) correct_option_index
    coi = mcq["correct_option_index"]
    if not isinstance(coi, int):
        raise QuestionValidationError("correct_option_index bir integer olmalı.")
    if not (0 <= coi < 4):
        raise QuestionValidationError("correct_option_index 0–3 arasında olmalı.")

    # 5) explanation
    explanation = mcq["explanation"]
    if not isinstance(explanation, str):
        raise QuestionValidationError("explanation string olmalı.")
    if len(explanation.strip()) < 5:
        raise QuestionValidationError("Açıklama çok kısa.")
    if len(explanation.strip()) > 800:
        raise QuestionValidationError("Açıklama çok uzun (800 karakter).")

    # 6) Seçenek benzerlik kontrolü (opsiyonel ileri seviye)
    if len(set(o.lower().strip() for o in options)) < 4:
        raise QuestionValidationError("Seçenekler çok benzer veya tamamen aynı.")

    # 7) Soru içinde doğru cevabın ipucu olup olmadığını kontrol et (basit heuristik)
    correct = options[coi].lower()
    if correct in question.lower():
        raise QuestionValidationError("Soru kökünde doğru cevaba dair ipucu bulunuyor.")


# ------------------ LLM JSON Parse & Normalize ------------------ #

class LLMParseError(Exception):
    """LLM çıktısı beklenen JSON formatına parse edilemediğinde fırlatılır."""
    pass


def _strip_markdown_fences(text: str) -> str:
    """
    ```json ... ``` gibi markdown bloklarını temizler.
    """
    fenced_match = re.search(
        r"```(?:json)?(.*?)```", text, flags=re.DOTALL | re.IGNORECASE
    )
    if fenced_match:
        return fenced_match.group(1).strip()

    text = text.strip()
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _extract_first_json_object(text: str) -> str:
    """
    Metin içinden ilk JSON objesini ( { ... } ) bulmaya çalışır.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMParseError("Metin içinde geçerli bir JSON objesi bulunamadı.")

    candidate = text[start : end + 1].strip()
    return candidate


def safe_parse_llm_json(raw_text: str) -> Dict[str, Any]:
    """
    LLM'den gelen ham metni güvenli şekilde JSON'a çevirmeye çalışır.
    """
    if not raw_text or not raw_text.strip():
        raise LLMParseError("Boş LLM çıktısı alındı.")

    text = raw_text.strip()
    text = _strip_markdown_fences(text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            json_candidate = _extract_first_json_object(text)
            parsed = json.loads(json_candidate)
        except Exception as e:
            raise LLMParseError(f"LLM JSON parse edilemedi: {e}") from e

    if isinstance(parsed, list):
        if not parsed:
            raise LLMParseError("LLM JSON listesi boş döndü.")
        parsed = parsed[0]

    if not isinstance(parsed, dict):
        raise LLMParseError("LLM çıktısı JSON dict formatında değil.")

    return parsed


def normalize_mcq(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM'den gelen dict'i bizim beklediğimiz MCQ şemasına normalize eder.

    Hedef şema:
    {
      "question": str,
      "options": [str, str, str, str],
      "correct_option_index": int (0-3),
      "explanation": str
    }
    """
    normalized: Dict[str, Any] = {}

    # 1) question
    question = str(raw.get("question", "")).strip()
    if not question:
        question = str(raw.get("prompt", "")).strip()

    if not question:
        raise ValueError("MCQ normalizasyonu: 'question' alanı boş.")

    normalized["question"] = question

    # 2) options
    options = raw.get("options")
    if isinstance(options, str):
        # "A) ..." satırları, noktalı virgül vs. ile gelmiş olabilir
        parts = re.split(r"[\n;]+", options)
        cleaned = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            # Baştaki "A) ", "B." gibi harf etiketlerini temizle
            p = re.sub(r"^[A-Da-d][\)\].:-]\s*", "", p)
            cleaned.append(p)
        options = cleaned

    if not isinstance(options, list):
        options = []

    options = [str(o).strip() for o in options if str(o).strip()]

    if len(options) < 2:
        raise ValueError(
            f"MCQ normalizasyonu: Yetersiz seçenek sayısı (len={len(options)})."
        )

    if len(options) > 4:
        options = options[:4]

    if len(options) != 4:
        raise ValueError(
            f"MCQ normalizasyonu: options uzunluğu 4 değil (len={len(options)})."
        )

    normalized["options"] = options

    # 3) correct_option_index — mümkün olan her yerden türet
    coi = raw.get("correct_option_index")

    # Doğrudan numeric alan isimleri
    if coi is None and "answer_index" in raw:
        coi = raw["answer_index"]
    if coi is None and "correct_index" in raw:
        coi = raw["correct_index"]

    # Eğer hâlâ yoksa, çeşitli string alanlardan çıkarmayı dene
    if coi is None:
        candidate = None

        # Farklı olası field isimleri
        for key in [
            "correct_option",
            "answer",
            "correct_answer",
            "correctOption",
            "dogru_cevap",
            "doğru_cevap",
            "correct",
        ]:
            if key in raw and raw[key] is not None:
                candidate = raw[key]
                break

        if candidate is not None:
            if isinstance(candidate, str):
                c_raw = candidate.strip()
                c = c_raw.upper()

                # 1) A, B, C, D tek başına verilmişse
                if c in ["A", "B", "C", "D"]:
                    coi = ["A", "B", "C", "D"].index(c)
                else:
                    # 2) "Doğru Cevap: B) Kalite" gibi pattern'ler
                    m = re.search(r"\b([A-D])\s*[\)\].:-]?", c)
                    if m:
                        letter = m.group(1)
                        coi = ["A", "B", "C", "D"].index(letter)

                    # 3) Şık metniyle eşleşmeye çalış
                    if coi is None:
                        for idx, opt in enumerate(options):
                            opt_up = opt.upper()
                            if opt_up in c or c in opt_up:
                                coi = idx
                                break

                    # 4) Baştaki numarayı dene (örn. "2 - Güvenilirlik")
                    if coi is None:
                        m_num = re.search(r"\b([0-3])\b", c)
                        if m_num:
                            coi = int(m_num.group(1))

            elif isinstance(candidate, (int, float)):
                coi = int(candidate)

    if coi is None:
        raise ValueError(
            "MCQ normalizasyonu: 'correct_option_index' / 'answer_index' "
            "bulunamadı ve türetilemedi."
        )

    try:
        coi_int = int(coi)
    except (TypeError, ValueError):
        raise ValueError(
            f"MCQ normalizasyonu: correct_option_index int'e çevrilemedi: {coi!r}"
        )

    if not (0 <= coi_int < len(options)):
        raise ValueError(
            f"MCQ normalizasyonu: correct_option_index aralık dışında: "
            f"{coi_int}, options_len={len(options)}"
        )

    normalized["correct_option_index"] = coi_int

    # 4) explanation
    explanation = str(raw.get("explanation", "")).strip()
    if not explanation:
        explanation = str(raw.get("rationale", "")).strip()

    if not explanation:
        explanation = "Bu soru için model açıklama üretmedi."

    normalized["explanation"] = explanation

    return normalized



def normalize_open_ended(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Open-Ended soruları normalize eder.
    {
        "question": ...,
        "answer": ...,
        "explanation": ...,
        ...
    }
    """
    normalized = {}
    
    # 1) question
    question = str(raw.get("question", "")).strip()
    if not question:
        question = str(raw.get("prompt", "")).strip()
    if not question:
         # Belki tek bir prompt field vardır
         if "stem" in raw: question = raw["stem"]
         
    if not question:
        raise ValueError("OpenEnded normalizasyonu: 'question' alanı boş.")
    normalized["question"] = question

    # 2) answer
    answer = str(raw.get("answer", "")).strip()
    if not answer:
        # Belki 'ideal_answer' vs
        answer = str(raw.get("ideal_answer", "")).strip()
    if not answer:
         # Fallback: explanation'ı answer yap
         pass
    
    normalized["answer"] = answer
    
    # 3) explanation
    explanation = str(raw.get("explanation", "")).strip()
    if not explanation:
        explanation = "Açıklama yok."
    normalized["explanation"] = explanation
    
    return normalized


def parse_and_normalize_mcq(raw_text: str) -> Dict[str, Any]:
    """
    Adı 'mcq' kalsa da artık generic davranıyor.
    """
    parsed = safe_parse_llm_json(raw_text)
    
    # Tip tespiti logic güncellendi:
    # 1) Eğer "answer_index" veya "correct_option_index" varsa -> KESİN MCQ
    if "answer_index" in parsed or "correct_option_index" in parsed:
        return normalize_mcq(parsed)

    # 2) Eğer "answer" var VE "options" yoksa -> KESİN OPEN ENDED
    if "answer" in parsed and "options" not in parsed:
        return normalize_open_ended(parsed)

    # 3) Eğer "answer" var ama "options" da varsa (Hallucinasyon durumu):
    # Eğer answer string ise ve uzunsa muhtemelen Open Ended'dir.
    if "answer" in parsed and isinstance(parsed["answer"], str) and len(parsed["answer"]) > 5:
        # Ancak yine de emin olmalıyız. "Correct Answer: B" gibi bir string de olabilir.
        ans_str = parsed["answer"].strip().lower()
        if len(ans_str) < 3 and ans_str in ["a", "b", "c", "d"]:
             return normalize_mcq(parsed)
        return normalize_open_ended(parsed)

    # 4) Eğer "options" varsa -> MCQ olarak dene (Index türetmeyi dener)
    if "options" in parsed and isinstance(parsed["options"], list):
        return normalize_mcq(parsed)
        
    # 5) Fallback: Eğer "answer" varsa -> Open Ended
    if "answer" in parsed:
        return normalize_open_ended(parsed)
        
    # Varsayılan
    return normalize_mcq(parsed)


# ------------------ Validation helper for generated questions ------------------ #

def validate_generated_llm_question(raw: Dict[str, Any]) -> None:
    """
    call_model()'den dönen soru dict'ini (zaten normalize edilmiş) validate_question_schema ile doğrular.

    Beklenen raw format:
    {
      "question": str,
      "options": list[str],
      "correct_option_index": int,
      "explanation": str
    }
    """
    mcq_for_validation: Dict[str, Any] = {
        "question": raw.get("question"),
        "options": raw.get("options") or [],
        "correct_option_index": raw.get("correct_option_index"),
        "explanation": raw.get("explanation") or "",
    }

    validate_question_schema(mcq_for_validation)