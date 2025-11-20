# Copilot / AI Agent Instructions for Chatbot

Short, actionable guidance to help AI coding agents be immediately productive in this repo.

## Big picture
- **Backend (FastAPI)**: code under `app/` — entrypoint is `app/main.py` which mounts API routers from `app/api/routers/*` and runs DB init on startup (`app/core/init_db.py`).
- **Domain logic**: `app/domain/` holds `services/`, `repositories/`, and `schemas/`. Services orchestrate LLM and vector DB calls (e.g., `rag_service.py`, `question_service.py`).
- **Storage**: `storage/chroma/` holds the Chroma persistent DB. `storage/db/` contains SQLite backups for questions and app state.
- **Frontend**: Next.js app lives in `ui/` (see `ui/package.json`); it's a separate dev server.

## Key integration points & external deps
- Ollama LLM: configured via `app/core/config.py` (`OLLAMA_URL`, `OLLAMA_MODEL`). Many service functions call `settings.OLLAMA_URL` directly (see `question_service._ollama`).
- Chroma vector DB: used via `chromadb.PersistentClient(path=...)` in `app/domain/services/rag_service.py`. Persist dir comes from `settings.CHROMA_PERSIST_DIR`.
- SQLite DBs: questions and app DBs are initialized/used via `app/core/db.py` and `app/core/init_db.py`. Startup bumps user_version and runs migration/init logic.

## Project-specific conventions and gotchas
- Imports assume package root: modules import as `app.*`. Run commands from repo root or set `PYTHONPATH` accordingly.
- Settings: `app/core/config.py` uses Pydantic settings and `.env` file. Use env vars to override paths like `QUESTIONS_DB_PATH`, `APP_DB_PATH`, and `CHROMA` dir.
- Typo: repository module is named `app/domain/repositories/quesitons_repo.py` (missing "t" in `questions`). Refer to it by its actual path when editing or importing.
- Ollama responses are often raw text; services parse/repair JSON from LLM output (see `question_service._find_json` and retry logic).
- CORS defaults are permissive in `app/main.py` / `config.py` for local development — tighten for production.

## Common developer workflows (commands)
- Backend (dev): from repo root (PowerShell):
```
$env:QUESTIONS_DB_PATH='storage/db/questions.db'; $env:APP_DB_PATH='storage/db/app.db'; \
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Frontend (dev):
```
cd ui
pnpm install
pnpm dev
```
- Build frontend for production: `cd ui; pnpm build; pnpm start`.

## Where to make changes
- Add or modify API routes in `app/api/routers/*` (these are included in `app/main.py`).
- Business logic belongs in `app/domain/services/*` and persistence in `app/domain/repositories/*`.
- Configs live in `app/core/config.py`; DB helpers in `app/core/db.py` and initialization in `app/core/init_db.py`.

## Testing & linting notes
- No dedicated test folder present. Static checks: project uses Black/isort/flake8 settings in `pyproject.toml`.
- Python target is 3.10 (see Black config). Keep line length ≈100.

## Small examples (pattern snippets)
- Calling Ollama: use `settings.OLLAMA_URL.rstrip('/')` before concatenating endpoints (see `question_service._ollama`).
- Querying Chroma: use `chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)` and `get_or_create_collection(name, embedding_function=..)` (see `rag_service._collection`).

## If you edit DB or persistence
- When changing DB schema, update `app/core/init_db.py` and bump the PRAGMA `user_version` logic used on startup.

## Helpful files to open first
- `app/main.py`, `app/core/config.py`, `app/core/init_db.py`, `app/core/db.py`, `app/api/routers/*`, `app/domain/services/*`, `app/domain/repositories/*`, `storage/chroma/`, `ui/package.json`.

---
If anything above is unclear or you want this expanded (examples of common change PRs, more API endpoint examples, or a short runbook for production deploy), tell me which area to expand and I will iterate.
