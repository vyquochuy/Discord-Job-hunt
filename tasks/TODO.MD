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

## Phase 2 — Job Collection (Completed)
- [x] Implement database models: `raw_jobs`, `jobs`, `skills`, `skill_aliases`, `job_skills`
- [x] Create Alembic migration `003_job_collection_models.py`
- [x] Implement `BaseJobCollector` abstract interface
- [x] Implement Source Adapters: `ITViecJobCollector`, `RemotiveJobCollector`, `CareerLinkJobCollector`, `TopCVJobCollector`, `MockJobCollector`
- [x] Implement Normalization Engine (`SkillNormalizer` + `JobNormalizer`)
- [x] Implement 3-Tier Deduplication Engine (Exact Hash -> RapidFuzz -> pgvector)
- [x] Ingestion Pipeline with SHA-256 Content Hash caching (0 LLM cost hit)
- [x] Integrate background worker loop in `backend/app/worker.py`
- [x] Expose REST APIs (`/api/v1/jobs`, `/api/v1/jobs/{id}`, `/api/v1/jobs/collect`, `/api/v1/jobs/taxonomy/skills`)
- [x] 28/28 automated unit and integration tests passing with live logs

---

## Phase 3 — Job Intelligence (Next Target)

### Data Models & Schemas
- [ ] Match models & MatchScore schemas (hard filters, match signals, weights, explanations)
- [ ] Alembic migration for Phase 3 models

### Hard Filtering & Match Engine
- [ ] Hard filter validation (Location, Work Mode, Target Roles, Minimum Salary)
- [ ] Exact Skill Set Overlap calculation via Canonical Taxonomy
- [ ] Semantic Similarity calculation using pgvector embeddings

### Scoring & Explanation
- [ ] Deterministic weighted scoring algorithm (0 - 100)
- [ ] Match explanation generator (highlights strengths, missing requirements, caveats)
- [ ] Job ranking & recommendation engine

### Discord Commands & APIs
- [ ] REST API endpoints for matching (`GET /api/v1/matches`, `POST /api/v1/matches/calculate/{job_id}`)
- [ ] Discord Slash Commands: `/jobs`, `/job <id>`, `/match <id>`
