
# 🧠 AI-Powered Quiz Bot

Yapay zeka tabanlı, kişiselleştirilmiş bir eğitim ve değerlendirme asistanı.

## 🚀 Özellikler

- **🤖 AI Soru Üretimi:** Llama 3, Phi-3 ve GPT modelleri ile otomatik soru oluşturma.
- **📚 RAG (Doküman Tabanlı Öğrenme):** PDF yükleyip kendi içeriklerinizden soru türetme.
- **🎯 Rubric Değerlendirme:** Açık uçlu sorular için detaylı, kriter bazlı puanlama.
- **🛡️ Güvenlik (Guardrails):** Hassas verileri (PII) otomatik maskeleme.
- **📊 Gelişmiş Analitik:** Kullanıcı performansını ve konu bazlı eksikleri görselleştirme.
- **💡 Akıllı Öneriler:** Başarısız olunan konuları tespit edip çalışma önerileri sunma.

## 💻 Sistem Gereksinimleri (Önemli)

Bu proje yerel LLM modelleri kullandığı için donanım kaynağına ihtiyaç duyar:

| Model | Min. RAM | Min. VRAM (GPU) | Önerilen |
|-------|----------|-----------------|----------|
| **Llama 3 (8B)** | 16 GB | 6 GB | NVIDIA RTX 3060+ |
| **Gemma 2 (2B)** | 8 GB | 2 GB | Giriş Seviye GPU |
| **QuizBot-TR (8B)**| 16 GB | 8 GB | NVIDIA RTX 4060+ |
| **Gemini/Groq** | 2 GB | - | Sadece internet |

**Not:** Yeterli donanımınız yoksa `.env` dosyasında `GEMINI_API_KEY` veya `GROQ_API_KEY` tanımlayarak bulut tabanlı modelleri kullanabilirsiniz.

## 🛠️ Kurulum Öncesi Gereksinimler

Projeyi çalıştırmadan önce aşağıdaki araçların kurulu olduğundan emin olun:
- **Docker & Docker Compose**
- **Ollama** (Yerel LLM için)

Ayrıca aşağıdaki **Ollama modellerini** indirmeniz gerekir (Fine-Tune edilmiş modeliniz varsa onu da ekleyin):
```bash
ollama pull llama3:instruct
ollama pull intfloat/multilingual-e5-large
```

### 🧠 Özel Model & Veri Seti (Opsiyonel)

Proje için özel olarak eğitilmiş (fine-tuned) Türkçe modele ve kullanılan veri setine aşağıdaki bağlantılardan ulaşabilirsiniz:

- **Model (Hugging Face):** [furkankasim16/llama3-8b-quizbot-tr](https://huggingface.co/furkankasim16/llama3-8b-quizbot-tr)
- **Veri Seti:** [furkankasim16/turkish-educational-content](https://huggingface.co/datasets/furkankasim16/turkish-educational-content)

**Özel Modeli Kullanmak İçin:**
1. Yukarıdaki linkten model dosyasını (`.gguf`) indirin.
2. Proje ana dizinindeki `Modelfile` dosyasını kullanın (veya kendiniz oluşturun).
3. Aşağıdaki komutla modeli Ollama'ya tanıtın:
   ```bash
   ollama create quizbot-tr -f Modelfile
   ```
4. Artık `.env` dosyasında `OLLAMA_MODEL=quizbot-tr` ayarını kullanabilirsiniz.

## 📚 Kendi Verilerinizle Çalışma (RAG)

QuizBot, sadece genel kültürü değil, **sizin verdiğiniz belgeleri de** öğrenebilir.
1. Proje içindeki `app/corpus/` klasörüne (yoksa oluşturun) PDF, TXT veya DOCX dosyalarınızı atın.
2. Uygulama arayüzünden veya API'den `/index` endpoint'ini tetikleyin (veya uygulamayı yeniden başlatın).
3. Artık QuizBot bu belgelerdeki bilgilerden de soru sorabilir! 

> **İpucu:** Konular (topics) sadece örnek olarak verilmiştir. İstediğiniz herhangi bir konuda (Tarih, Biyoloji, Şirket İçi Dokümanlar) quiz oluşturabilirsiniz.


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
