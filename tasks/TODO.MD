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

## Phase 3 — Job Intelligence (Completed)

### Data Models & Schemas
- [x] Match models & MatchScore schemas (tri-state hard filters, 7 match signals, weights, snapshots, versioning)
- [x] Alembic migration `004_job_match_models.py`

### Hard Filtering & Match Engine
- [x] Tri-state hard filter validation (Location, Work Mode, Target Roles, Minimum Salary) with explicit UNKNOWN semantics
- [x] Exact Skill Set Overlap calculation via Canonical Taxonomy & Aliases (zero embedding hallucination)
- [x] Per-project Semantic Similarity calculation (Cosine similarity normalized to [0.0, 1.0] with keyword fallback)

### Scoring & Explanation
- [x] Deterministic 7-signal weighted scoring algorithm (0 - 100) with weight sum invariant assertion
- [x] Score cap rule (< 30% required skill coverage -> score <= 50.0)
- [x] Clear separation between Eligibility (ELIGIBLE / BLOCKED / UNCERTAIN) and Match Score
- [x] Match explanation generator (structured strengths, missing requirements, caveats, LLM + deterministic template)
- [x] Job ranking & recommendation engine (`/recommend`, `GET /api/v1/matches/recommendations/top`)

### Discord Commands & APIs
- [x] REST API endpoints for matching (`GET /api/v1/matches`, `POST /api/v1/matches/calculate/{job_id}`, `POST /api/v1/matches/calculate-all`, `GET /api/v1/matches/recommendations/top`)
- [x] Discord Slash Commands: `/ping`, `/profile`, `/collect`, `/jobs`, `/job <id>`, `/match <id>`, `/recommend`
- [x] 45/45 automated tests passing (invariant tests, boundary tests, skill dedup, experience independence, API lifecycle, golden test case)

---

## Phase 4 — Resume Intelligence & Application Automation (Next Target)

### 1. Data Models & Schemas
- [ ] Tailored Resume Schema (`TailoredResume`, `EvidenceMap`, `ResumePlan`, `CoverLetter`)
- [ ] Alembic migration `005_resume_tailoring_models.py`

### 2. Tailoring & Provenance Engine
- [ ] Evidence-Locked Rewriter: Chỉ sử dụng các sự thật (facts) và số liệu có sẵn trong `master-resume.tex` & `context/candidate-profile.yaml` (Zero Hallucination).
- [ ] Dynamic LaTeX Generator: Tái cấu trúc file `.tex` theo thứ tự ưu tiên của JD (skills nổi bật, highlight metric liên quan).
- [ ] Provenance Verification: Kiểm tra từng bullet point trước khi xuất file PDF.

### 3. LaTeX Compilation & PDF Pipeline
- [ ] Containerized / Local LaTeX Compiler (`pdflatex` / `xelatex` wrapper).
- [ ] Export Artifacts: Sinh đồng thời file `.tex`, `.pdf` và `cover_letter.md`.

### 4. REST APIs & Discord Commands
- [ ] API endpoints: `POST /api/v1/resumes/tailor/{job_id}`, `GET /api/v1/resumes/{id}/pdf`, `POST /api/v1/resumes/apply/{job_id}`.
- [ ] Discord Slash Commands: `/resume <job_id>`, `/apply <job_id>` (gửi file PDF trực tiếp vào Discord channel và gửi email ứng tuyển).


