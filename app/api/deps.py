from typing import Any, Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.core.db import app_cursor
from app.core.init_db import init_questions_db, init_app_db
from app.core.config import settings
from app.domain.repositories.users_repo import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def on_start_questions_db():
    init_questions_db(); return True

def on_start_app_db():
    init_app_db(); return True

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    with app_cursor() as c:
        row = c.execute(
            "SELECT id, username, email, is_admin, xp, level FROM users WHERE username=?",
            (username,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return {
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "is_admin": bool(row[3]),
        "xp": row[4] or 0,
        "level": row[5] or 1
    }