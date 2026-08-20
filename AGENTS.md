# AGENTS.md

CEAP for Schools — monorepo: `backend/` (Flask + SQLAlchemy + ChromaDB) and `frontend/` (React 19 + Vite).

The root `README.md` is **stale** (still references the old "OneDrive_Chatbot"/Gemini era). Trust code, not the README. `DEPLOY.md` is accurate.

## Backend

- Single config file is `backend/.env` (loaded via `load_dotenv` in `app/config.py` and `run.py`). Root `.env.example` is a starting template. `DB_URI` (PostgreSQL) is **required** — `app/db.py` raises at import if unset.
- Run: `python run.py` (dev server on :5000, loads demo users from `AuthConfig.USERS` in `app/config.py`). Production entrypoint: `gunicorn run:app` (Dockerfile).
- Blueprints live in `app/modules/<feature>/routes.py` (AI chat is `ai/routes.py` + `ai/studio_routes.py`). Every new blueprint MUST be registered in `create_app()` in `app/__init__.py` **twice**: `register_blueprint` AND `csrf.exempt(...)` (CSRF is enabled globally but exempted per-blueprint).
- Schema: no Alembic migrations in the run path. `app/db.py` `init_db()` does `create_all` + additive `_ensure_columns()` ALTER TABLEs. Add new columns on existing tables to `_ensure_columns()` too. The `alembic/` dir is orphaned (alembic isn't in requirements.txt).
- LLM is **Groq** (`groq_service.py`, default `llama-3.3-70b-versatile`), not Gemini. Agentic answers route through `query_router.py` + `tools.py`/`tool_executor.py`; RAG uses Chroma hybrid (HNSW + BM25 + RRF).
- No test framework — `backend/tests/` are plain assert scripts run manually (e.g. `python tests/test_query_router.py`), and they need a live DB. Lint with `ruff` (no config, defaults); neither runs in CI.
- CLI jobs: `python run.py index-repo-docs`, `python run.py check-compliance-status` (cron).
- App log goes to `logs/ceap.log`. ChromaDB data lives at `backend/chroma_db`.

## Frontend

- React 19 + Tailwind v4 + `react-router-dom` v7 + oxlint (NOT eslint).
- Commands (in `frontend/`): `npm run dev` (:5173, proxies `/api /auth /logout /onedrive /gdrive` → :5000), `npm run build` (→ `dist/`), `npm run lint`.
- All API calls go through `src/lib/api.js` (relative base, `credentials: include`).
- Some pages still render mock data (`src/data/mockData.js`, `osData.js`) instead of the backend — check before assuming a page is wired up.

## Deploy

- Push to `main` triggers `.github/workflows/deploy.yml`: builds frontend, rsyncs to the VPS `/opt/CEAP`, `docker compose up -d --build backend`. No lint/tests in CI.
- `backend/.env` on the server is **manually managed and never overwritten** by CI. Backend binds `127.0.0.1:8010`, nginx fronts it.