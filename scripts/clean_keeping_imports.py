import sqlite3
import os

DB_PATH = 'app/storage/db/questions.db'

KEPT_STEMS = [
    "SENARYO: Bir şirket çalışanı, kendisine BT departmanından gelmiş gibi görünen bir e-posta alır. E-postada 'Sistem güncellemesi için şifrenizi aşağıdaki bağlantıya girerek onaylayın' denilmektedir. Çalışan bağlantıya tıklar ve şifresini girer. 10 dakika sonra sistem yöneticisi olağandışı bir giriş fark eder.\n\n SORU: Bu olayda ihlal edilen temel güvenlik politikası prensibi nedir ve acil müdahale adımı ne olmalıdır?",
    "Bir ürünün 'Churn Rate' (Müşteri Kayıp Oranı) %10'dan %2'ye düştüğünde aşağıdakilerden hangisi doğrudan gerçekleşmiş olur?",
    "Destek süreçlerinde 'First Response Time' (FRT), bir müşteriye sorununun çözüldüğüne dair gönderilen son mesajın süresini ifade eder.",
    "Veri koruma politikalarında, 'yetkisiz erişimi engellemek için verinin okunamaz hale getirilmesi' işlemine ne ad verilir?",
    "Bir 'SaaS' ürününde 'Product-Led Growth' (Ürün Odaklı Büyüme) stratejisinin temel mantığını ve satış odaklı büyümeden farkını açıklayınız.",
    "SENARYO: Bir müşteri, aldığı hizmetin SLA (Service Level Agreement) süresinin dolmasına rağmen yanıt alamadığını belirterek Twitter üzerinden şikayette bulunuyor. \n\n SORU: Destek akışına göre (Support Flow) bu durumda 'Escalation' (Üst Mercie İletme) süreci nasıl işlemelidir?"
]

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check total before
    cursor.execute("SELECT COUNT(*) FROM questions")
    total_before = cursor.fetchone()[0]
    
    # Delete NOT IN kept_stems
    placeholders = ', '.join(['?'] * len(KEPT_STEMS))
    query = f"DELETE FROM questions WHERE stem NOT IN ({placeholders})"
    
    cursor.execute(query, KEPT_STEMS)
    deleted_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"✅ Cleanup complete.")
    print(f"   Before: {total_before}")
    print(f"   Deleted: {deleted_count}")
    print(f"   Remaining: {total_before - deleted_count}")

if __name__ == "__main__":
    main()
