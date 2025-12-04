from typing import Optional, Dict, Any
from app.core.db import app_cursor
from app.core.security import hash_password, verify_password

def create_user(username: str, email: str, password: str) -> int:
    with app_cursor() as c:
        c.execute("INSERT INTO users(username, email, hashed_password) VALUES(?,?,?)",
                  (username, email, hash_password(password)))
        return c.lastrowid

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with app_cursor() as c:
        c.execute("SELECT id, username, email, hashed_password, is_admin FROM users WHERE username=?", (username,))
        row = c.fetchone()
    if not row: return None
    uid, u, e, h, admin = row
    return {"id": uid, "username": u, "email": e, "hashed_password": h, "is_admin": bool(admin)}

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with app_cursor() as c:
        c.execute("SELECT id, username, email, is_admin FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
    if not row: return None
    uid, u, e, admin = row
    return {"id": uid, "username": u, "email": e, "is_admin": bool(admin)}

def verify_user_password(username: str, password: str) -> Optional[Dict[str, Any]]:
    u = get_user_by_username(username)
    if not u: return None
    if not verify_password(password, u["hashed_password"]): return None
    return u

def get_auth_stats() -> dict:
    with app_cursor() as c:
        c.execute("SELECT COUNT(*), SUM(is_admin) FROM users")
        cnt, admins = c.fetchone()
    return {"total_users": cnt or 0, "total_admins": admins or 0}