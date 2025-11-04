"""
SQLite teşhis aracı:
- settings.APP_DB_PATH ve settings.QUESTIONS_DB_PATH tam yolunu, varlık durumunu, boyutunu, mtime'ını gösterir
- Her DB'de tablo listesini ve (isteğe bağlı) tablo başına kayıt sayısını gösterir
- İstersen proje altında tüm *.db dosyalarını tarar

Kullanım:
  python scripts/db_inspect.py
  python scripts/db_inspect.py --scan
  python scripts/db_inspect.py --counts
  python scripts/db_inspect.py --scan --counts --root .
"""
from __future__ import annotations
import sys, os, argparse, sqlite3
from pathlib import Path
from datetime import datetime

# Proje kökünü sys.path'e ekle
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.core.config import settings
from app.core.db import _open_sqlite

def human_size(n: int) -> str:
    for unit in ("B","KB","MB","GB","TB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"

def file_info(p: Path) -> str:
    if not p.exists():
        return "NOT FOUND"
    stat = p.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return f"exists, size={human_size(stat.st_size)}, mtime={mtime}"

def list_tables(conn: sqlite3.Connection) -> list[tuple[str,str]]:
    rows = conn.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name").fetchall()
    return [(r[0], r[1]) for r in rows if r[0] not in ("sqlite_sequence",)]

def count_rows(conn: sqlite3.Connection, table: str) -> int:
    try:
        (cnt,) = conn.execute(f"SELECT COUNT(1) FROM {table}").fetchone()
        return int(cnt)
    except Exception:
        return -1

def show_db(path: Path, show_counts: bool):
    print(f"\n=== DB: {path.resolve()} ===")
    print("   ", file_info(path))
    if not path.exists():
        return
    try:
        conn = _open_sqlite(path)
    except Exception as e:
        print(f"   [!] Open error: {e}")
        return
    try:
        rows = conn.execute("PRAGMA database_list").fetchall()
        for r in rows:
            print(f"   [db] seq={r[0]} name={r[1]} file={r[2]}")
        tables = list_tables(conn)
        if not tables:
            print("   (no tables)")
            return
        print("   Tables:")
        for name, ttype in tables:
            if show_counts and ttype == "table":
                cnt = count_rows(conn, name)
                extra = f" ({cnt})" if cnt >= 0 else " (?)"
            else:
                extra = ""
            print(f"     - {name} [{ttype}]{extra}")
        # Bonus: sık kullanılan tablolar için kısa özet
        try:
            (q_total,) = conn.execute("SELECT COUNT(1) FROM questions").fetchone()
            print(f"   [summary] questions={q_total}")
        except Exception:
            pass
        try:
            (u_total,) = conn.execute("SELECT COUNT(1) FROM users").fetchone()
            print(f"   [summary] users={u_total}")
        except Exception:
            pass
    finally:
        conn.close()

def scan_for_dbs(root: Path) -> list[Path]:
    # proje ağacında *.db dosyalarını tara (node_modules, .venv gibi klasörleri atla)
    ignore = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dn = Path(dirpath).name
        if dn in ignore:
            dirnames[:] = []  # bu klasöre inmeyi durdur
            continue
        for f in filenames:
            if f.lower().endswith(".db"):
                found.append(Path(dirpath) / f)
    return sorted(found)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true", help="Proje altında tüm *.db dosyalarını listele")
    ap.add_argument("--root", default=str(ROOT), help="--scan için kök dizin (default: proje kökü)")
    ap.add_argument("--counts", action="store_true", help="Tablo başına kayıt sayısını göster")
    args = ap.parse_args()

    # Settings'ten gelen kanonik dosyalar
    app_db = Path(settings.APP_DB_PATH)
    q_db = Path(settings.QUESTIONS_DB_PATH)

    print("=== Canonical DB Paths (from settings) ===")
    print(" APP_DB_PATH      :", app_db.resolve())
    print(" QUESTIONS_DB_PATH:", q_db.resolve())

    show_db(app_db, args.counts)
    show_db(q_db, args.counts)

    if args.scan:
        print(f"\n=== Scan for *.db under: {Path(args.root).resolve()} ===")
        dbs = scan_for_dbs(Path(args.root))
        if not dbs:
            print(" (no .db files found)")
        for p in dbs:
            mark = ""
            if p.resolve() == app_db.resolve():
                mark = "  <-- APP_DB_PATH"
            elif p.resolve() == q_db.resolve():
                mark = "  <-- QUESTIONS_DB_PATH"
            print(" -", p.resolve(), file_info(p), mark)

if __name__ == "__main__":
    main()
