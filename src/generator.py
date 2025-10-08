import argparse
import random
import time
from src import question

def main(total: int = 150, mistral_ratio: float = 0.5):
    question.init_db()

    # hangi modelleri kullanacağız
    models = ["mistral", "llama3:instruct"]

    generated = 0
    while generated < total:
        # model seç (oranlara göre)
        model = random.choices(models, weights=[mistral_ratio, 1-mistral_ratio])[0]

        # topic, level, qtype seç
        topic = random.choice(question.TOPICS)
        level = random.choice(question.LEVELS)
        qtype = random.choice(question.QUESTION_TYPES)

        print(f"🔄 {topic} | {level} | {qtype} | {generated+1}/{total} | model={model}")

        # soru üret
        q = question.generate_question_from_context(topic, level, qtype, model=model)
        ""
        if "error" not in q:
            print(f"✅ Soru eklendi: {q.get('stem')[:60]}...")
            generated += 1
        else:
            print(f"❌ Hata: {q}")
            time.sleep(3)  # API aşırı yüklenmesin diye küçük gecikme

    print(f"\n🎉 Tamamlandı! Toplam {generated} soru üretildi.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--total", type=int, default=30, help="Kaç soru üretilecek")
    parser.add_argument("--ratio", type=float, default=0.5, help="Mistral oranı (0–1 arası)")
    args = parser.parse_args()

    main(total=args.total, mistral_ratio=args.ratio)
