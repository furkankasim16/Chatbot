# scripts/seed_questions.py
"""
Batch import script for questions database.

Usage:
    python scripts/seed_questions.py path/to/batch_all.json
"""

import json
import sys
from pathlib import Path
import sqlite3

# Proje kökünü sys.path'e ekle
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.core.init_db import init_questions_db  # DB tablosu hazır mı kontrolü
from app.domain.schemas.question import Question
from app.domain.repositories.quesitons_repo import add_question  # ⬅️ yazım hatası düzeltilmiş
from app.utils.text import json_hash


def main(json_path: str):
    file_path = Path(json_path)

    # Dosya mevcut mu?
    if not file_path.exists():
        print(f"[❌] JSON file not found: {file_path}")
        sys.exit(1)

    # JSON içeriğini oku
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[❌] Invalid JSON format in {file_path}: {e}")
        sys.exit(1)

    # DB tablo yapısını garanti altına al
    init_questions_db()

    imported, skipped, failed = 0, 0, 0
    for i, item in enumerate(data, start=1):
        try:
            # Hash üret ve ekle
            item["hash"] = json_hash(item)
            q = Question(**item)
            add_question(q)
            imported += 1
        except sqlite3.IntegrityError:
            # Aynı hash zaten varsa atla
            skipped += 1
        except Exception as e:
            print(f"[⚠️] Row {i} failed: {e}")
            failed += 1

    print(f"\n✅ Import complete.")
    print(f"   Imported: {imported}")
    print(f"   Skipped (duplicates): {skipped}")
    print(f"   Failed: {failed}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_questions.py path/to/batch_all.json")
        sys.exit(1)

    main(sys.argv[1])
