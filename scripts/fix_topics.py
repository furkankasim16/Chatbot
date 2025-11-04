# scripts/fix_topics.py
"""
Fix wrong 'topic' values in questions table.

Usage:
  Dry-run (önerilir):  python scripts/fix_topics.py
  Uygula:              python scripts/fix_topics.py --apply
"""

from __future__ import annotations
import sys
import shutil
from datetime import datetime
from pathlib import Path
import sqlite3

# Proje kökünü sys.path'e ekle
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.core.config import settings  # QUESTIONS_DB_PATH
from app.core.db import _open_sqlite  # sqlite bağlantı yardımcıları


# Eski -> Yeni eşleştirmeler (case-insensitive karşılaştırma)
TOPIC_MAP = {
    "product basic": "product_basics",
    "security policy": "security_policy",
    "support flow": "support_flow",
}


def backup_db(src: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = src.with_suffix(f".bak.{ts}")
    shutil.copy2(src, dst)
    return dst


def count_matches(conn: sqlite3.Connection, old_key: str) -> int:
    (cnt,) = conn.execute(
        "SELECT COUNT(1) FROM questions WHERE lower(topic) = ?",
        (old_key.lower(),),
    ).fetchone()
    return int(cnt)


def apply_update(conn: sqlite3.Connection, old_key: str, new_value: str) -> int:
    cur = conn.execute(
        "UPDATE questions SET topic = ? WHERE lower(topic) = ?",
        (new_value, old_key.lower()),
    )
    return cur.rowcount or 0


def main(apply: bool = False):
    db_path: Path = Path(settings.QUESTIONS_DB_PATH)

    if not db_path.exists():
        print(f"[❌] DB not found: {db_path}")
        sys.exit(1)

    conn = _open_sqlite(db_path)
    try:
        # Ön rapor
        print(f"[ℹ️] DB: {db_path}")
        total_to_fix = 0
        for old_key, new_value in TOPIC_MAP.items():
            cnt = count_matches(conn, old_key)
            total_to_fix += cnt
            print(f" - Will change '{old_key}' → '{new_value}': {cnt} rows")

        if total_to_fix == 0:
            print("\n✅ Nothing to fix. All topics look good.")
            return

        if not apply:
            print("\n🔎 Dry-run complete. Use --apply to write changes.")
            return

        # Yedek al
        bak = backup_db(db_path)
        print(f"\n🧯 Backup created: {bak}")

        # Uygula (tek transaction)
        conn.execute("BEGIN")
        changed = 0
        for old_key, new_value in TOPIC_MAP.items():
            changed += apply_update(conn, old_key, new_value)
        conn.commit()

        print(f"\n✅ Applied. Rows updated: {changed}")

        # Son kontrol
        remaining = 0
        for old_key in TOPIC_MAP.keys():
            remaining += count_matches(conn, old_key)
        if remaining == 0:
            print("🔒 Verification OK: no old values remain.")
        else:
            print(f"⚠️ Verification: {remaining} old values still present.")

    except Exception as e:
        # Hata olursa rollback
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[❌] Failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    apply_flag = "--apply" in sys.argv
    main(apply=apply_flag)
