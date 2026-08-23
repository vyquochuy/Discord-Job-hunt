# Roadmap

---

## Phase 0 — Foundation
**Status:** COMPLETED

**Goal:** Repository structure, documentation, development environment, infrastructure.
- [x] Docker Compose (PostgreSQL with pgvector, Redis, FastAPI Backend, Background Worker, Discord Bot)
- [x] Database configuration with asyncpg and Alembic migrations
- [x] Security middleware and health check endpoints (`/health`)

---

## Phase 1 — Candidate Profile
**Status:** COMPLETED

**Goal:** Store and manage candidate data so the system can use it for matching and generation.
- [x] Candidate profile database models (`Candidate`, `CandidateSkill`, `CandidateExperience`, `CandidateProject`, `CandidateCertification`)
- [x] Context synchronization parser (`candidate-profile.yaml`, `master-resume.tex`)
- [x] CRUD/Sync REST APIs (`GET /api/v1/profile`, `PUT /api/v1/profile`, `POST /api/v1/profile/sync`)

---

## Phase 2 — Job Collection
**Status:** COMPLETED

**Goal:** Automatically discover and store normalized job postings from multiple sources.
- [x] Job database models (`raw_jobs`, `jobs`, `skills`, `skill_aliases`, `job_skills`)
- [x] Source collectors (ITViec, Remotive, CareerLink, TopCV, Mock)
- [x] Canonical skill taxonomy & normalization engine
- [x] 3-tier deduplication (Exact Signature, RapidFuzz, pgvector Cosine)
- [x] Ingestion pipeline with SHA-256 caching for 0 LLM cost hit
- [x] Background scheduler loop in `worker.py` and REST APIs

---

## Phase 3 — Job Intelligence
**Status:** COMPLETED

**Goal:** Analyze job descriptions and produce candidate-job matches with deterministic scores.
- [x] Tri-state Hard Filters (`ELIGIBLE`, `BLOCKED`, `UNCERTAIN`)
- [x] 7-signal deterministic scoring engine (weights sum $= 1.0$)
- [x] Explainable matching service with verified evidence trails
- [x] Top job ranking & recommendations endpoints (`/api/v1/matches/recommendations/top`)

---

## Phase 4 & 4.5 — Resume Intelligence & Tailoring
**Status:** COMPLETED

**Goal:** Generate job-specific tailored resumes grounded in candidate evidence and automate dispatch.
- [x] `RoleClassifier`, multi-tier `EvidenceScorer`, `DiverseEvidenceSelector` (MMR), `AdaptiveSummaryBuilder`
- [x] Zero-Hallucination `ProvenanceVerifier` (fact-checking every bullet point against candidate profile)
- [x] Pure `latex_generator.py` and sandbox `pdflatex` compilation wrapper
- [x] Authentic Markdown `cover_letter_generator.py`
- [x] REST APIs for CV generation, LaTeX source, and PDF downloads (`/api/v1/resumes/*`)

---

## Phase 5 — API Contract & Domain Boundary Definition
**Status:** IN PROGRESS

**Goal:** Cleanly separate Domain Core from presentation layers, establish User 1–1 Candidate identity, implement SavedJobs, flexible Auth, and Notification Service abstraction.

**Scope:**
- [ ] Model `User` with 1–1 relationship to `Candidate`
- [ ] Model `SavedJob` for user bookmarks
- [ ] Alembic migration `007_user_and_saved_jobs_models.py`
- [ ] Flexible Authentication Layer (Token/Bearer support + `verify_internal_secret`)
- [ ] REST API Endpoints:
  - Auth: `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/me`
  - Saved Jobs: `POST /api/v1/jobs/{id}/save`, `DELETE /api/v1/jobs/{id}/save`, `GET /api/v1/jobs/saved`
  - Applications: `PATCH /api/v1/applications/{id}/status`
- [ ] `NotificationService` abstraction layer with `DiscordNotificationProvider`

**Acceptance Criteria:**
- [ ] User and CandidateProfile linked 1–1 cleanly
- [ ] Database acts as runtime Source of Truth for Candidate Profile
- [ ] Notification service sends notifications without business logic depending on Discord
- [ ] Automated tests for API contracts and auth pass 100%

---

## Phase 6 — Web Application Frontend (Simple Blue UI) & Discord Deprecation
**Status:** NOT STARTED

**Goal:** Build the primary Web Application interface with clean, information-dense Blue UI, and transition Discord slash commands to deprecated status with web redirect links.

**Scope:**
- [ ] Web Application Frontend (Simple Blue Design System with CSS variables):
  - `/login` & `/register`
  - `/dashboard`: "What is worth applying today?"
  - `/jobs` & `/jobs/:id`: Multi-criteria search, JD analysis, match explanations, actions (Apply/Save/Tailor)
  - `/recommendations`: Top recommended jobs view
  - `/profile`: Profile management and context sync
  - `/resume`: Tailored resume workspace, PDF viewer, Provenance inspector, Cover Letter
  - `/applications`: Application lifecycle tracking table
- [ ] Discord Bot Adapter updates:
  - Deprecate slash commands (`/jobs`, `/job`, `/match`, `/resume`, `/apply`) by providing short summaries with links to Web App
  - Receive automated notifications from `NotificationService`

**Acceptance Criteria:**
- [ ] User can complete full job hunting workflow directly on the Web App without opening Discord
- [ ] Web UI is fast, responsive, and adheres to the Simple Blue theme
- [ ] Discord bot serves as an optional notification channel

---

## Phase 7 — Personalization & Advanced Outcome Tracking
**Status:** NOT STARTED

**Goal:** Learn from application outcomes to refine matching accuracy.
- [ ] Application outcome tracking (interview, rejection, offer)
- [ ] Feedback loop to adjust matching score weights
- [ ] User preference learning based on save/apply actions

