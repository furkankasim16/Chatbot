from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from app.core.config import settings
from app.core.init_db import init_app_db, init_questions_db
from app.core.db import _open_sqlite
from app.core.paths import DB_DIR

app = FastAPI(title="API", openapi_url="/api/v1/openapi.json")

from app.api.routers.health import router as health_router
from app.api.routers.questions import router as questions_router
from app.api.routers.chat import router as chat_router
from app.api.routers.auth import router as auth_router
from app.api.routers.quiz import router as quiz_router
from app.api.routers.admin import router as admin_router

# main.py (middleware kısmı)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[                     # ✅ DEV: açık liste
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,             # cookie/token ile çalışıyorsanız True
    allow_methods=["*"],                # GET,POST,PUT,DELETE,OPTIONS dahil
    allow_headers=["*"],                # Authorization, Content-Type, X-* ...
    expose_headers=["*"],
    max_age=86400,
)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(health_router, tags=["health"])
api_v1.include_router(questions_router,tags=["questions"])  # questions.py prefixsiz kalsın
api_v1.include_router(chat_router, prefix="/chat", tags=["chat"])
api_v1.include_router(auth_router)       # bu dosyalarda kendi prefix’i var
api_v1.include_router(quiz_router, tags=["quiz"])
api_v1.include_router(admin_router, tags=["admin"])
app.include_router(api_v1)

def _bump_once(db_path, init_fn, target_version: int = 1):
    conn = _open_sqlite(db_path)
    try:
        (ver,) = conn.execute("PRAGMA user_version").fetchone()
        if ver < target_version:
            init_fn()
            conn.execute(f"PRAGMA user_version={target_version}")
            conn.commit()
    finally:
        conn.close()

@app.on_event("startup")
def startup_init_all():
    print(f"[DB] dir     : {DB_DIR}")
    print(f"[DB] app     : {settings.APP_DB_PATH}")
    print(f"[DB] questions: {settings.QUESTIONS_DB_PATH}")
    _bump_once(settings.QUESTIONS_DB_PATH, init_questions_db, 1)
    _bump_once(settings.APP_DB_PATH, init_app_db, 1)

@app.get("/api/v1/ping")
def ping():
    return {"pong": True}

print("=== ROUTE MAP ===")
for r in app.routes:
    try:
        print(" ", r.path, sorted(r.methods))
    except Exception:
        pass
print("=================")
