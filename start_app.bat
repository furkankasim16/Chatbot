@echo off
echo ===================================================
echo   CHATBOT UYGULAMASI BASLATILIYOR...
echo ===================================================

:: 1. Backend (API) Başlat
echo [1/3] Backend (Uvicorn) baslatiliyor...
start "Chatbot Backend (API)" cmd /k "call .venv\Scripts\activate && uvicorn app.main:app --reload"

:: 2. Worker (Arkaplan Islemleri) Başlat
echo [2/3] Worker baslatiliyor...
start "Chatbot Worker" cmd /k "call .venv\Scripts\activate && python -m app.workers.llm_worker"

:: 3. Frontend (UI) Başlat
echo [3/3] Frontend (Next.js) baslatiliyor...
cd ui
start "Chatbot Frontend" cmd /k "npm run dev"

echo ===================================================
echo   TUM SERVISLER BASLATILDI!
echo   Pencereleri kapatarak servisleri durdurabilirsiniz.
echo ===================================================
timeout /t 5
