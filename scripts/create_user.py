# scripts/create_user.py
"""
Create a new user (or update an existing one) in app.db users table.

Usage examples:
  # Yeni admin oluştur
  python scripts/create_user.py --username admin --email admin@example.com --password admin123 --admin

  # Var olan kullanıcının şifresini güncelle
  python scripts/create_user.py --username admin --password newpass --update
"""
from __future__ import annotations
import sys
import argparse
import sqlite3
from pathlib import Path

# Proje kökünü path'e ekle
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from passlib.context import CryptContext
from app.core.config import settings
from app.core.db import _open_sqlite

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def main():
    parser = argparse.ArgumentParser(description="Add or update user in app.db")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", help="Required when creating a new user")
    parser.add_argument("--password", required=True)
    parser.add_argument("--admin", action="store_true", help="Set as admin user")
    parser.add_argument("--update", action="store_true", help="Update existing user password")
    args = parser.parse_args()

    db_path = Path(settings.APP_DB_PATH)
    conn = _open_sqlite(db_path)

    try:
        hashed_pw = pwd_ctx.hash(args.password)

        if args.update:
            cur = conn.execute("SELECT id FROM users WHERE username=?", (args.username,))
            row = cur.fetchone()
            if not row:
                print(f"[❌] User '{args.username}' not found.")
                sys.exit(1)

            conn.execute(
                "UPDATE users SET hashed_password=?, is_admin=? WHERE username=?",
                (hashed_pw, 1 if args.admin else 0, args.username),
            )
            conn.commit()
            print(f"[✅] Updated password for '{args.username}' (admin={bool(args.admin)})")

        else:
            if not args.email:
                print("[❌] --email is required when creating a new user")
                sys.exit(1)

            conn.execute(
                """
                INSERT INTO users (username, email, hashed_password, is_admin)
                VALUES (?, ?, ?, ?)
                """,
                (args.username, args.email, hashed_pw, 1 if args.admin else 0),
            )
            conn.commit()

            # created_at otomatik CURRENT_TIMESTAMP ile set edilir
            print(
                f"[✅] Created user '{args.username}' "
                f"(admin={bool(args.admin)}) in {db_path}"
            )

    except sqlite3.IntegrityError as e:
        print(f"[⚠️] IntegrityError: {e}. Use --update if you want to modify existing user.")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
