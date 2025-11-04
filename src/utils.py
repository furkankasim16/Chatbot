import re

def evaluate_quality(text: str) -> float:
    """
    Basit metin kalitesi değerlendirme fonksiyonu.
    0.0 - 1.0 arası skor döndürür.
    """
    if not text or len(text.strip()) < 10:
        return 0.0

    # Türkçe harf oranı
    turkish_chars = len(re.findall(r"[ığüşöçİĞÜŞÖÇ]", text))
    turkish_ratio = turkish_chars / (len(text) + 1)

    # Uzunluk (çok kısa veya çok uzun cümleler düşük skor)
    length_score = 1.0 if 50 <= len(text) <= 300 else 0.6

    # Noktalama kontrolü
    punctuation_score = 1.0 if text.strip().endswith('.') else 0.7

    # Sayı, URL, gereksiz karakter kontrolü
    noise_penalty = 0.0 if re.search(r"(http|www|[0-9]{4,})", text) else 1.0

    # Skor ağırlıkları
    score = (
        turkish_ratio * 0.4 +
        length_score * 0.3 +
        punctuation_score * 0.2 +
        noise_penalty * 0.1
    )

    return round(min(max(score, 0.0), 1.0), 2)
