
# 🧠 AI-Powered Quiz Bot

Yapay zeka tabanlı, kişiselleştirilmiş bir eğitim ve değerlendirme asistanı.

## 🚀 Özellikler

- **🤖 AI Soru Üretimi:** Llama 3, Phi-3 ve GPT modelleri ile otomatik soru oluşturma.
- **📚 RAG (Doküman Tabanlı Öğrenme):** PDF yükleyip kendi içeriklerinizden soru türetme.
- **🎯 Rubric Değerlendirme:** Açık uçlu sorular için detaylı, kriter bazlı puanlama.
- **🛡️ Güvenlik (Guardrails):** Hassas verileri (PII) otomatik maskeleme.
- **📊 Gelişmiş Analitik:** Kullanıcı performansını ve konu bazlı eksikleri görselleştirme.
- **💡 Akıllı Öneriler:** Başarısız olunan konuları tespit edip çalışma önerileri sunma.

## 🛠️ Kurulum Öncesi Gereksinimler

Projeyi çalıştırmadan önce aşağıdaki araçların kurulu olduğundan emin olun:
- **Docker & Docker Compose**
- **Ollama** (Yerel LLM için)

Ayrıca aşağıdaki **Ollama modellerini** indirmeniz **ZORUNLUDUR**:
```bash
ollama pull llama3:instruct
ollama pull intfloat/multilingual-e5-large
```

---

## 🚀 Hızlı Başlangıç (Docker ile)

1. **Repoyu Klonlayın:**
   ```bash
   git clone https://github.com/furkankasim16/Chatbot.git
   cd Chatbot
   ```

2. **Çevresel Değişkenleri Ayarlayın (.env):**
   Ana dizinde `.env` adında bir dosya oluşturun ve aşağıdaki ayarları ekleyin. (Eğer `env.example` varsa kopyalayabilirsiniz):
   
   ```ini
   # --- LLM Ayarları (Zorunlu) ---
   # Docker içinden host'taki Ollama'ya erişmek için:
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   EMBED_MODEL=intfloat/multilingual-e5-large

   # --- Cloud API Anahtarları (Opsiyonel) ---
   # Eğer yerel LLM yerine bunları kullanmak isterseniz:
   GEMINI_API_KEY=AIzaSy...
   GROQ_API_KEY=gsk_...
   ```

3. **Uygulamayı Başlatın:**

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
