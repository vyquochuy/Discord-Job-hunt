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

## Phase 2.5 — Manual & Ad-hoc Job Ingestion (Completed)
- [x] `url_fetcher.py`: Abstraction `FetchedDocument` with HTTP + HTML extraction and `JS_REQUIRED` detection
- [x] `heuristic_extractor.py`: Rule-based parser + Canonical Taxonomy matching with per-field confidence (`FieldConfidence`) and overall confidence calculation
- [x] `extraction_pipeline.py`: Orchestrator between Heuristic Extractor and LLM Structured Fallback (confidence threshold based)
- [x] `manual_ingestion_service.py`: Complete orchestration (Input -> Extraction -> Normalization -> Lazy Dedup L1/L2 -> Persist RawJob with provenance -> Lazy Embedding -> Instant 7-signal deterministic match)
- [x] REST API endpoint `POST /api/v1/jobs/ingest-manual` with `ManualJobIngestRequest` & `ManualJobIngestResponse`
- [x] Web App Modal Dialog **"➕ Nhập JD thủ công"** with 2 tabs (Text & URL), confidence bar, field checklist, match score preview, and 1-click Tailor Resume action
- [x] Discord Bot `/import url <link>` & `/import text` (Modal form) with rich embeds and action links
- [x] Automated test suite `backend/tests/test_manual_ingestion.py` (9/9 PASS, 84/84 full suite PASS)

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

### Architectural Hardening & Pre-Phase 4 Alignment (Completed)
- [x] Zero-Cost Ingestion: Disabled bulk LLM calls during crawling, supplemented with deterministic regex/taxonomy skill extraction
- [x] Job Contact Info: Added `contact_email` and `apply_url` columns to `jobs` table (Alembic migration `005_add_job_contact_fields.py`)
- [x] Daily Batch Orchestrator: Built `DailyBatchRunnerService` in `backend/app/services/daily_runner.py` and `POST /api/v1/jobs/daily-batch`
- [x] Fast Explainability: Instant deterministic fallback when OpenAI API key is missing or dummy
- [x] 48/48 automated unit and integration tests passing with 100% success rate

---

## Phase 4 — Resume Intelligence & Application Automation (Completed)

### 1. Data Models & Schemas
- [x] Tailored Resume Schema (`TailoredResume`, `EvidenceMap`, `CoverLetter`, `ApplicationLog`)
- [x] Alembic migration `006_resume_tailoring_models.py`

### 2. Tailoring & Provenance Engine
- [x] Evidence-Locked Rewriter: Chỉ sử dụng các sự thật (facts) và số liệu có sẵn trong `master-resume.tex` & `context/candidate-profile.yaml` (Zero Hallucination).
- [x] Dynamic LaTeX Generator: Tái cấu trúc file `.tex` theo thứ tự ưu tiên của JD (skills nổi bật, highlight metric liên quan).
- [x] Provenance Verification: Kiểm tra từng bullet point trước khi xuất file PDF (`ProvenanceVerifier` with partial + token set fuzzy ratio).

### 3. LaTeX Compilation & PDF Pipeline
- [x] Containerized / Local LaTeX Compiler (`pdflatex` / `xelatex` sandbox wrapper with safe fallback).
- [x] Export Artifacts: Sinh đồng thời file `.tex`, `.pdf` và `cover_letter.md`.

### 4. REST APIs & Discord Commands
- [x] API endpoints: `POST /api/v1/resumes/tailor/{job_id}`, `GET /api/v1/resumes/{id}`, `GET /api/v1/resumes/{id}/pdf`, `GET /api/v1/resumes/{id}/tex`, `POST /api/v1/applications/apply/{job_id}`, `GET /api/v1/applications`.
- [x] Discord Slash Commands: `/resume <job_id>`, `/apply <job_id>` (gửi file PDF trực tiếp vào Discord channel và gửi email/draft ứng tuyển).
- [x] 54/54 automated tests passing with 100% success rate.

---

## Phase 4.5 — JD-Agnostic Strategic Resume Intelligence Engine (Completed)
- [x] **Typed Intermediate Representation (Single Source of Truth)**:
  - Added dataclasses & models: `MetricFact`, `FactNode`, `JDCapabilityProfile`, `SkillRequirementType`, `ClaimVerificationStatus`, `ScoredEvidenceItem`, `DecomposedClaim`, `LayoutBudget`, `ScoredProjectCandidate`, `ProjectScoringDetail`, `ProjectSelectionResult`, `ResumeStrategy`.
- [x] **Canonical Fact Graph Builder**:
  - Structured extraction of immutable fact nodes from Candidate Projects, Bullets, Experiences, Education, Certifications.
  - Deterministic regex metric fact extraction (`MetricFact`).
- [x] **Multi-Dimensional JD Capability Analyzer**:
  - Continuous vector $[0.0, 1.0]$ across 10 capability domains (`backend`, `systems`, `security`, `frontend`, `mobile`, `cloud`, `database`, `realtime`, `data_ai`, `automation`).
  - Word-boundary matching taxonomy eliminating false substring collisions (e.g. single-letter `"c"`).
- [x] **Strategic Project Selector & Targeted MMR**:
  - Multi-signal scoring: Relevance (50%), Role Fit (30%), Direct Tech Overlap (20%), Irrelevance Penalty (-0.10).
  - Targeted MMR with capability diversity bonus ($\le 0.35$) and redundancy penalty ($-0.25$).
  - Generation of Selection Explainability Matrix (`"Được chọn: ..."` / `"Loại bỏ: ..."`).
- [x] **Physical Layout Planner (1-Page ATS)**:
  - Decoupled physical budgeting: Max 3 projects, Max 7 bullets, Min 2 projects.
- [x] **Claim-Level Provenance Verifier**:
  - Decomposition of bullet points into atomic claims (`DecomposedClaim`) and exact metric grounding.
- [x] **Project Evidence Model & Invariant Engine**:
## Phase 4 & 4.5 — Evidence-Grounded Resume Tailoring Engine & Anti-Hallucination Refactor (Completed)
- [x] Refactored Pipeline: `Candidate Profile` $\rightarrow$ `Fact Graph & Evidence Registry` $\rightarrow$ `JD Capability Analyzer` $\rightarrow$ `Tailoring Strategy` $\rightarrow$ `Gemini Semantic Resume Writer` $\rightarrow$ `Claim-Level Evidence Validation` $\rightarrow$ `Structured Resume Model` $\rightarrow$ `Pure LaTeX Renderer` $\rightarrow$ `PDF Output`.
- [x] Canonical Technology Alias Registry (`alias_registry.py`) with word-boundary token matching (50+ tech terms, preventing regex false positives).
- [x] `fact_graph.py` Single Source of Truth extracting atomic `EvidenceFact`s with canonical technologies and quantitative metrics.
- [x] `jd_capability_analyzer.py` capability scoring and candidate gap detection filtering domain stop words.
- [x] `gemini_resume_writer.py` calling Gemini REST API (`gemini-3.6-flash`) with Structured JSON Mode and `claims: list[GeneratedClaimFragment]`.
- [x] `deterministic_composer.py` 100% offline, zero-hallucination fallback composer.
- [x] `evidence_validator.py` 6-stage validation (`INVALID_EVIDENCE_ID`, `UNSUPPORTED_TECHNOLOGY`, `UNSUPPORTED_METRIC`, `EXPERIENCE_INFLATION`, `UNSUPPORTED_JD_FABRICATION`, `ARCHITECTURAL_SCOPE_SHIFT`) with unit-level locking and selective regeneration.
- [x] `latex_generator.py` direct rendering from `StructuredResumeDraft` for ATS 1-page compliance.
- [x] Automated test suite `backend/tests/test_architectural_anti_hallucination.py` (11/11 PASS, full suite 118/118 PASS).

---

## Phase 5 — API Contract & Domain Boundary Layer (Completed)
- [x] Data Models: `User` (1-1 với `Candidate`), `SavedJob`
- [x] Alembic migration `007_user_and_saved_jobs_models.py`
- [x] Authentication & Security Engine (`PBKDF2-HMAC-SHA256`, Bearer Token, `get_current_user`)
- [x] REST API Endpoints: Auth (`/api/v1/auth/*`), Saved Jobs (`/api/v1/jobs/saved`, `POST/DELETE /api/v1/jobs/{id}/save`), Applications status update (`PATCH /api/v1/applications/{id}/status`)
- [x] Notification Service Abstraction (`NotificationService`, `DiscordNotificationProvider`, `ConsoleNotificationProvider`)
- [x] Automated Test Suite (`test_auth_and_saved_jobs.py`) - 5/5 PASS

---

## Phase 6 — Web Application Frontend (Simple Blue) & Discord Deprecation (Completed)
- [x] Simple Blue Design System in `frontend/css/index.css` (No Tailwind, CSS variables, -webkit-backdrop-filter, zero linter warnings)
- [x] Single Page Application in `frontend/index.html` (Accessible, no inline styles, modern layout)
- [x] REST API Client in `frontend/js/api.js`
- [x] SPA View Controllers in `frontend/js/app.js` (Dashboard, Job Search, Job Details Modal with 7-Signal Score breakdown, Recommendations, Resume Workspace, Applications Tracker, Candidate Profile)
- [x] FastAPI static mounting and serving at root `/`
- [x] Discord Bot command deprecation notices and web redirect links
- [x] 103/103 backend automated tests passing + Discord bot TypeScript build passing

---

## Phase 7 — Personalization & Advanced Outcome Tracking (Planned)
- [ ] Application outcome tracking (interview, rejection, offer)
- [ ] Feedback loop to adjust matching score weights based on outcomes
- [ ] User preference learning based on save/apply patterns

---

## Phase 8 — Zero-Cost Public Production Deployment (Cloudflare Pages, Cloud PaaS, Supabase & Free LLM) (In Progress)
- [x] **8.1 Frontend Cloud-Ready & Cloudflare Pages Deployment (0đ)**:
  - [x] Dynamic `API_BASE` endpoint in `frontend/js/api.js` (support `window.ENV?.API_URL`, local fallback, and production cloud domain)
  - [x] Cloudflare Pages SPA Routing rule in `frontend/_redirects` (`/* /index.html 200`) to prevent 404 on page refresh
  - [x] Verify all static assets (CSS, JS, icons) use relative paths
  - [x] Live API Endpoint management & Ping Health Check controller in System View
  - [x] Create comprehensive deployment guide in `docs/CLOUDFLARE_PAGES_GUIDE.md`
- [ ] **8.2 Cloud Database & Serverless Cache (0đ)**:
  - [ ] Provision **Supabase PostgreSQL** (Free tier 500MB) with `pgvector` extension enabled
  - [ ] Provision **Upstash Redis** (Free 10k commands/day) for queue and caching
  - [ ] Configure cloud `DATABASE_URL` and `REDIS_URL` in environment variables
- [ ] **8.3 Provider-Agnostic AI Architecture, Task-Based Routing & Quality Fallback**:
  - [ ] Standardized `AIProvider` Protocol with `generate_structured(prompt, schema, temperature)`
  - [ ] Provider Adapters: `GeminiProvider` (Gemini 3.6/2.0 Flash), `GroqProvider` (LLaMA 3.3 70B, DeepSeek Distill), `DeepSeekProvider` (DeepSeek V3/R1), `OpenAIProvider`
  - [ ] Task-Based `AIRouter` (`AITask`: `jd_extraction`, `jd_analysis`, `resume_generation`, `resume_unit_regeneration`, `cover_letter`, `explanation`) with configurable provider/model mappings
  - [ ] Multi-tiered Quality Fallback Chain: `LLM Output` $\rightarrow$ `Schema Validation` $\rightarrow$ `ClaimLevelValidator` (Anti-Hallucination) $\rightarrow$ `Unit Regeneration` $\rightarrow$ `Fallback Provider` $\rightarrow$ `Deterministic Composer` (Offline Guaranteed)
- [ ] **8.4 Backend & Discord Bot Deployment (0đ)**:
  - [ ] Deploy FastAPI Backend to **Render.com** (Free Web Service) or **Koyeb** / **Hugging Face Spaces**
  - [ ] Configure CORS middleware in `backend/app/main.py` to allow Cloudflare Pages domain
  - [ ] Deploy Discord Bot to **Hugging Face Spaces (Docker Space)** or **Discloud** for 24/7 WebSocket Gateway connection
  - [ ] Set up **UptimeRobot** keep-alive ping (5-minute interval) against `/api/v1/health` to prevent backend cold sleep
- [ ] **8.5 Cloud Storage & Context Persistence Hardening**:
  - [ ] Persist candidate profile & generated tailored resumes directly in PostgreSQL / Supabase Storage (handling ephemeral container filesystem)

---

## Phase 9 — Comprehensive Responsive Design & Multi-Device SaaS Experience (Planned)
- [ ] **Mobile & Tablet Layouts (320px – 1024px)**:
  - [ ] Off-canvas sliding Drawer Navigation for Mobile / Tablet screens
  - [ ] Resume Workspace: Responsive single-column stacked cards layout for small screens
  - [ ] Mobile-optimized PDF preview & LaTeX code editor views
- [ ] **Touch & Accessibility Optimization**:
  - [ ] Swipe gestures for tab navigation & job card actions
  - [ ] Touch-friendly tap targets (minimum 44x44px per WCAG guidelines)
- [ ] **Dark Mode & Large Screens**:
  - [ ] Full Dark Mode color palette & toggle
  - [ ] Max-width containment for Ultra-Wide (2K/4K) monitors

