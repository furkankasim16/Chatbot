# knowledge-bot
## Kurulum

### 1. Gereksinimler
- Python 3.11+
- Git
- (Opsiyonel) Docker / Docker Compose
- (Opsiyonel) Make (Linux/Mac, Windows’ta gerekmez)

---

### 2. Sanal ortam (Windows PowerShell)

   powershell
# Proje klasörüne gir
cd chatbot

# Sanal ortam oluştur
python -m venv .venv

# Aktivasyon
.venv\Scripts\Activate.ps1

# Eğer hata alırsan (script policy):
# PowerShell'i Administrator olarak aç ve çalıştır:
# Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
Linux/Mac için:
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install fastapi uvicorn[standard] pytest httpx python-dotenv pydantic-settings

### 3.Çalıştırma
    python -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
    http://localhost:8000/docs  (Tarayıcıdan kontrol edin)

    

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r <yoksa doğrudan pip ile yukarıdaki paketler>
make dev
# http://localhost:8000/health
