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

## Phase 1 — Candidate Profile (Current Active)

### Data Models & Storage (Completed)
- [x] Implement SQLAlchemy ORM models:
  - `Candidate`
  - `CandidateSkill`
  - `CandidateProject` (with evidence points array/json)
  - `CandidateExperience`
  - `CandidateCertification`
- [x] Implement Pydantic validation schemas for candidate domain entities (`backend/app/schemas/candidate.py`)
- [x] Create Alembic migration script `002_candidate_profile_models.py`
- [x] Unit test validation for models and schemas (`backend/tests/test_candidate_models.py`)

### Ingestion & Services (In Progress)
- [x] Create parser service for `context/candidate-profile.yaml`, `context/master-resume.tex`, `context/master-resume.md` (`backend/app/services/parser.py`)
- [x] Implement `CandidateRepository` for database CRUD operations & context sync (`backend/app/repositories/candidate.py`)
- [x] Unit tests for parser and repository sync (`backend/tests/test_candidate_parser_and_repo.py`)
- [ ] Implement `CandidateService` for profile management & sync orchestration (`backend/app/services/candidate.py`)
- [ ] Expose REST API endpoints:
  - `GET /api/v1/profile`: Retrieve candidate profile & evidence
  - `PUT /api/v1/profile`: Update candidate profile
  - `POST /api/v1/profile/sync`: Ingest/sync from `context/` files

### Discord Bot Integration (Next)
- [ ] Implement `/profile` slash command (displays profile in rich Embed format)
- [ ] Implement `/profile update` command (interactive Modal for field updates)
- [ ] Add sync feedback via ephemeral responses
