# app/core/config.py
import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from app.core.paths import APP_DB, QUESTIONS_DB, CHROMA_DIR, resolve_db_path

class Settings(BaseSettings):
    # --- mevcut ayarlar ---
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60
    DEBUG: bool = True

    OLLAMA_URL: AnyHttpUrl = "http://localhost:11434"
    OLLAMA_MODEL : str = "qwen2.5:32b" # 🚀 Upgrade to 32B (High Intelligence, Slow Inference)
    OLLAMA_MODEL_TUTOR: Optional[str] = None
    OLLAMA_MODEL_PLAYGROUND: Optional[str] = None
    OLLAMA_MODEL_REVIEW: Optional[str] = None
    
    # .env dosyasından otomatik okunur
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    EMBED_MODEL: str = "intfloat/multilingual-e5-large"

    # --- Redis & Queue ---
    REDIS_URL: str = "redis://localhost:6379/0"
    LLM_QUEUE_NAME: str = "llm"
    LLM_QUEUE_MAX: int = 100
    LLM_JOB_MAX_WAIT_SEC: int = 600
    LLM_CALL_TIMEOUT_SEC: int = 300
    LLM_RETRY_MAX: int = 1

    # ⬇️ TİP ANOTASYONU EKLENDİ (Path)
    QUESTIONS_DB_PATH: Path = resolve_db_path(os.getenv("QUESTIONS_DB_PATH") or QUESTIONS_DB)
    APP_DB_PATH: Path       = resolve_db_path(os.getenv("APP_DB_PATH") or APP_DB)

    # CHROMA_DIR Path ise burada stringe çevirmen mantıklı
    CHROMA_PERSIST_DIR: str = str(CHROMA_DIR)

    # İstersen AnyHttpUrl listesi de kullanabilirsin; şimdilik string list yeterli
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    CORS_ALLOW_ALL: bool = True  # dev için açık; prod’da .env’de false yap

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- ek API anahtarları ---
    OPENROUTER_API_KEY: Optional[str] = None
    HF_API_KEY1: Optional[str] = None
    HF_API_KEY2: Optional[str] = None

settings = Settings()