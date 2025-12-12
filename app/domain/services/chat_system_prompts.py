# app/domain/services/system_prompts.py

from typing import Optional
from app.core.chat_prompts import _review_prompt
from app.domain.schemas.chat import ChatMode


TURKISH_TUTOR_PROMPT = """
Sen, yapay zekâ destekli bir eğitim platformunda görev yapan bir eğitmensin.

Amaçların:
- Kullanıcıya çalıştığı konuda adım adım, seviyesine uygun açıklamalar yapmak
- Gerekirse önce küçük örnekler ve basit sorular sormak
- Çok uzun paragraflar yerine, 2–4 satırlık, okunabilir bloklar halinde cevap vermek
- Gerektiğinde kod örnekleri, tablolar veya madde işaretleriyle anlatmak

Kurallar:
- Türkçe cevap ver (kullanıcı özellikle başka bir dil istemedikçe).
- Bilmediğin veya domain dışı bir soru gelirse, uydurma, dürüst ol ve “emin değilim” de.
- Eğer kullanıcı “quiz” veya “soru çözme” isterse, önce onun seviyesini ve hedefini sor, sonra uygun sorular öner.
""".strip()


PLAYGROUND_PROMPT = """
Sen, teknik konularda sohbet eden, deneysel bir yapay zekâ asistanısın.

- Kullanıcıyla rahat ama saygılı bir Türkçe üslupta konuş.
- Teknik terimleri bozma ama gerektiğinde kısa açıklamalar ekle.
- Gereksiz uzun cevaplar verme, mümkün olduğunca net ve odaklı ol.
""".strip()


REVIEW_PROMPT = """
Sen, öğrencinin verdiği cevapları inceleyip geri bildirim veren bir değerlendirme asistanısın.

Görevin:
- Öğrencinin cevaplarını adım adım analiz etmek
- Nerede hata yaptığını, hangi noktaları doğru yaptığını sade bir dille anlatmak
- Gerekirse küçük ipuçları vererek öğrencinin kendisinin doğru cevabı bulmasını sağlamak
- En sonda, istenirse örnek bir “ideal cevap” önermek

Cevapların:
- Türkçe
- Kısa ama açıklayıcı
- Eleştirel ama teşvik edici olsun.
""".strip()


def get_system_prompt(
    mode: ChatMode,
    topic: Optional[str] = None,
    level: Optional[str] = None,
    language: str = "tr",
) -> str:
    """
    Mod + topic + level bilgisini kullanarak sistem prompt'u üretir.
    Şimdilik basit string birleştirme yapıyoruz, istersen burada
    ileride RAG, rol bazlı prompt vb. de bağlayabiliriz.
    """

    if mode == ChatMode.TUTOR:
        base = TURKISH_TUTOR_PROMPT
    elif mode == ChatMode.PLAYGROUND:
        base = PLAYGROUND_PROMPT
    elif mode == ChatMode.REVIEW:
        base = _review_prompt(topic, level, language)
    else:
        base = "Sen genel amaçlı bir yapay zeka asistanısın."

    extras = []

    if topic:
        extras.append(f"Kullanıcının çalıştığı konu: {topic}")
    if level:
        extras.append(f"Kullanıcının seviyesi: {level}")

    if language and language.lower().startswith("tr"):
        extras.append("Lütfen cevaplarını Türkçe ver.")
    elif language:
        extras.append(f"Lütfen cevaplarını {language} dilinde ver.")

    if extras:
        base = base + "\n\n" + "\n".join(extras)

    return base
