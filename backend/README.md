# AI Job Hunter Platform — Backend API

FastAPI REST API and domain services. PostgreSQL is the runtime source of truth; Discord is an optional adapter, not the business core.

## Run locally

From the repository root, copy `.env.example` to `.env` and configure credentials. For a backend running outside Docker, point `DATABASE_URL`, `DATABASE_URL_SYNC` and `REDIS_URL` at localhost rather than Compose hostnames. Install Python 3.11+ and a local TeX distribution with `pdflatex` if PDF generation is needed.

```bash
docker compose up -d postgres redis
python -m venv .venv
```

Activate `.venv` (`.venv\Scripts\Activate.ps1` on PowerShell or `source .venv/bin/activate` on POSIX). Settings load `.env` relative to the working directory: before switching to `backend/`, export the environment values or create a private `backend/.env` with localhost URLs (do not commit it). Then:

```bash
cd backend
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API docs: `http://localhost:8000/docs`. `/health` is DB-free liveness; `/health/ready` queries the database.

Alternatively, from the repository root:

```bash
docker compose up -d --build backend
```

Compose builds the React frontend through `frontend-build`, runs migrations and serves `frontend/dist` at port 8000. Without that bundle, the backend does not serve Vite source or the removed legacy frontend. After UI edits:

```bash
docker compose run --rm frontend-build
docker compose restart backend
```

For HMR, run `npm ci` and `npm run dev` in a separate `frontend/` terminal (port 5173). Optional workers run from `backend/` with `python -m app.worker`, `--run-once`, or `--daily-batch`.

## Runtime boundaries

- Resume PDFs require authentication and ownership checks (including the existing superuser override). Bearer and supported iframe query tokens are accepted; knowing the UUID grants no public access. Missing artifacts can recompile from stored LaTeX after authorization. PDF compilation requires a readable exactly-one-page result; no placeholder PDF is returned on failure.
- Application preparation defaults to `simulate_only=true` and creates READY without delivery. Actual submission returns HTTP 501; manually updated SENT records track external submissions, not a working email transport.
- Gemini resume writing uses `GEMINI_MODEL` (default `gemini-flash-latest`) and fallback attempts; see `../docs/AI_SYSTEM.MD`. Provider availability is not guaranteed. Without usable AI, the deterministic composer is the fallback.
- Saramin replaces the historical TopDev collector; migration `009_rename_topdev_saramin` updates source data. Restricted sources must report failure rather than bypass access controls.
- Docker contains minimal TeXLive packages, not `texlive-latex-extra`. Container configuration is not proof of production deployment or complete sandbox isolation.

## Checks

From `backend/`: `python -m pytest -q`. From the repository root: `python scripts/check_frontend_serving.py`. From `frontend/`: `npm run build` (TypeScript plus Vite).
