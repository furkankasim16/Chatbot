
# 🧠 AI-Powered Quiz Bot

Yapay zeka tabanlı, kişiselleştirilmiş bir eğitim ve değerlendirme asistanı.

## 🚀 Özellikler

- **🤖 AI Soru Üretimi:** Llama 3, Phi-3 ve GPT modelleri ile otomatik soru oluşturma.
- **📚 RAG (Doküman Tabanlı Öğrenme):** PDF yükleyip kendi içeriklerinizden soru türetme.
- **🎯 Rubric Değerlendirme:** Açık uçlu sorular için detaylı, kriter bazlı puanlama.
- **🛡️ Güvenlik (Guardrails):** Hassas verileri (PII) otomatik maskeleme.
- **📊 Gelişmiş Analitik:** Kullanıcı performansını ve konu bazlı eksikleri görselleştirme.
- **💡 Akıllı Öneriler:** Başarısız olunan konuları tespit edip çalışma önerileri sunma.

## 🛠️ Kurulum

### 1. Ön Gereksinimler
- **Docker** ve **Docker Compose** yüklü olmalı.
- (Opsiyonel) **Ollama** lokalde çalışıyor olmalı (LLM için).

### 2. Çalıştırma
Projeyi indirdikten sonra ana dizinde terminali açın ve şu komutu çalıştırın:

```bash
docker-compose up --build
```
Bu işlem ilk seferde birkaç dakika sürebilir.

### 3. Erişim
- **Frontend (Arayüz):** [http://localhost:3000](http://localhost:3000)
- **Backend (API):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ChromaDB:** [http://localhost:8008](http://localhost:8008)

## 📂 Proje Yapısı

- `app/`: Python (FastAPI) backend kodları.
- `ui/`: Next.js frontend kodları.
- `app/data/`: SQLite veritabanı ve yüklenen PDF'ler burada saklanır.

## 🧪 Geliştirme Modu (Lokal)

Eğer Docker kullanmadan geliştirmek isterseniz:

**Backend:**
```bash
poetry install
poetry run uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd ui
npm install
npm run dev
```

---
*Geliştirici: Furkan Talha KASIM*
