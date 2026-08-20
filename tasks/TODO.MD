# TODO

## Phase 0 — Foundation (Completed)
- [x] Write `docker-compose.yml` defining services (postgres with pgvector, redis, backend, discord-bot, workers)
- [x] Create `.env.example` with required variables
- [x] Configure database connection & session factory (SQLAlchemy 2.0 async + asyncpg)
- [x] Initialize Alembic migration environment in `backend/alembic/` with initial pgvector activation
- [x] Set up `backend/requirements.txt` and `backend/Dockerfile`
- [x] Create FastAPI skeleton in `backend/app/main.py` with `/health` and `/api/v1` routers
- [x] Implement internal API authentication with `INTERNAL_API_SECRET`
- [x] Set up background worker skeleton in `backend/app/worker.py`
- [x] Configure `discord-bot/package.json`, `tsconfig.json`, and `discord-bot/Dockerfile`
- [x] Implement Discord Bot client in `discord-bot/src/index.ts` with slash command loader
- [x] Build backend REST API client in `discord-bot/src/services/api-client.ts`
- [x] Add `/ping` health check slash command responding with rich embed

---

## Phase 1 — Candidate Profile (Completed)
- [x] Implement SQLAlchemy ORM models (`Candidate`, `CandidateSkill`, `CandidateExperience`, `CandidateProject`, `CandidateCertification`)
- [x] Implement Pydantic validation schemas (`CandidateDetailResponse`, `CandidateCreate`, `CandidateUpdate`, `CandidateSyncResponse`, etc.)
- [x] Create Alembic migration script `002_candidate_profile_models.py`
- [x] Create parser service for `context/candidate-profile.yaml`, `context/master-resume.tex`, `context/master-resume.md`
- [x] Implement `CandidateRepository` for database CRUD operations & context sync
- [x] Implement `CandidateService` for profile management & sync orchestration
- [x] Expose REST API endpoints with `X-Internal-Secret` security (`GET /api/v1/profile`, `PUT /api/v1/profile`, `POST /api/v1/profile/sync`)
- [x] Unit and API integration tests (`backend/tests/test_profile_api.py`)
- [x] Implement `/profile` slash command (`view`, `update`, `sync` with Rich Embed, Action Buttons, and interactive Modals)

---

## Phase 2 — Job Collection (Current Active)

### Data Models & Schema
- [ ] Implement Job and Company database models (SQLAlchemy ORM + Alembic migration)
- [ ] Implement Pydantic schemas for normalized Job data

### Collectors & Normalization
- [ ] Define `JobCollector` abstract interface
- [ ] Implement first job source collector
- [ ] Build job normalization engine
- [ ] Implement deduplication logic (Layers 1-3)

### Worker & Scheduling
- [ ] Configure scheduled collection tasks in worker
- [ ] Implement collection run logging and error recovery
- [ ] Add health tracking metrics for collectors
