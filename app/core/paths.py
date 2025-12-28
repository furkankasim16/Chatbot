from pathlib import Path

# ---- Proje kökü (örnek: Chatbot/)
ROOT = Path(__file__).resolve().parents[1]

# ---- Veri dizinleri ----
DATA_DIR = ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"

# ---- Yazılabilir depolama ----
STORAGE_DIR = ROOT / "storage"
CHROMA_DIR = STORAGE_DIR / "chroma_v2" # 🚀 Migrated to v2 to bypass corruption
DB_DIR = STORAGE_DIR / "db"
DB_BACKUP_DIR = DB_DIR / "backups"

DB_DIR.mkdir(parents=True, exist_ok=True)

APP_DB        = DB_DIR / "app.db"
QUESTIONS_DB  = DB_DIR / "questions.db"

def ensure_dirs():
    DB_DIR.mkdir(parents=True, exist_ok=True)

def resolve_db_path(p: str | Path) -> Path:
    # Çevreden gelen göreli yolları da BASE_DIR'e göre mutlaklaştır
    p = Path(p)
    return p if p.is_absolute() else (DB_DIR / p)
DB_BACKUP = DB_BACKUP_DIR / "app_backup.db"