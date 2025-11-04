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

    OLLAMA_URL: AnyHttpUrl = "http://localhost:11434"
    EMBED_MODEL: str = "intfloat/multilingual-e5-large"

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
