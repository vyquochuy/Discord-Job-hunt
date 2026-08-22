# Completed Work

## Phase 0 — Foundation (Completed)
- [x] Initialize repository structure (`discord-bot/`, `backend/`, `workers/`, `database/`, `context/`, `docs/`, `tasks/`)
- [x] Create project documentation system (AGENTS.md, PROJECT.md, ARCHITECTURE.md, AI_SYSTEM.md, ROADMAP.md, SECURITY.md, DECISIONS.md)
- [x] Create candidate profile template (`context/candidate-profile.yaml`) and master resume (`context/master-resume.md`, `master-resume.tex`)
- [x] Create `.gitignore` and `.env.example`
- [x] Create `docker-compose.yml` (PostgreSQL with pgvector, Redis, FastAPI Backend, Background Worker, Discord Bot)
- [x] Create FastAPI backend infrastructure (Pydantic Settings, Async SQLAlchemy + asyncpg, Security middleware, /health check)
- [x] Set up Alembic migration environment with initial `pgvector` activation migration
- [x] Create Discord Bot infrastructure (discord.js v14, TypeScript, API client, Slash command handler, `/ping` command)

---

## Phase 1 — Candidate Profile (Completed)
- [x] Implement SQLAlchemy ORM models (`Candidate`, `CandidateSkill`, `CandidateExperience`, `CandidateProject`, `CandidateCertification`)
- [x] Implement Pydantic validation schemas (`CandidateDetailResponse`, `CandidateCreate`, `CandidateUpdate`, `CandidateSyncResponse`, etc.)
- [x] Create Alembic migration script `002_candidate_profile_models.py`
- [x] Build Ingestion Parser (`CandidateProfileParser`) for `candidate-profile.yaml`, `master-resume.tex`, `master-resume.md`
- [x] Build `CandidateRepository` with asynchronous eager-loading queries and atomic context synchronization
- [x] Build `CandidateService` for profile retrieval, mutation, and sync orchestration
- [x] Expose protected REST API endpoints (`GET /api/v1/profile`, `PUT /api/v1/profile`, `POST /api/v1/profile/sync`)
- [x] Build Discord Bot Slash Command `/profile` (subcommands: `view`, `update`, `sync` with Rich Embeds, Action Buttons, and interactive Modals)
- [x] 100% automated test coverage with 10 unit and API integration test cases passing

---

## Phase 2 — Job Collection (Completed)
- [x] Implement SQLAlchemy models: `RawJob` (Source of Truth), `Job` (Standardized), `Skill` & `SkillAlias` (Canonical Taxonomy), `JobSkill` (Metadata: `is_required`, `confidence`, `source`)
- [x] Create Alembic migration script `003_job_collection_models.py`
- [x] Implement `BaseJobCollector` abstract interface
- [x] Implement real source collectors: `ITViecJobCollector`, `RemotiveJobCollector`, `CareerLinkJobCollector`, `TopCVJobCollector`, and `MockJobCollector`
- [x] Implement Normalization Engine:
  - `SkillNormalizer` (Canonical skills & aliases dictionary)
  - `JobNormalizer` (Title cleanup, Company normalization, Location/WorkMode mapping, Salary & Level inference)
- [x] Implement 3-Tier Deduplication Engine (`dedup_service.py`):
  - Layer 1: Exact Hash Signature
  - Layer 2: RapidFuzz Fuzzy Match (Token Set / Sort ratio with level distinction)
  - Layer 3: Semantic Cosine Similarity (pgvector)
- [x] Implement Ingestion Pipeline (`ingestion_pipeline.py`) with SHA-256 content hashing for 0 LLM cost caching
- [x] Integrate periodic background scheduler in `backend/app/worker.py` (with `--run-once` and daemon mode)
- [x] Expose REST APIs (`GET /api/v1/jobs`, `GET /api/v1/jobs/{id}`, `POST /api/v1/jobs/collect`, `GET /api/v1/jobs/taxonomy/skills`)
- [x] Unit & Integration test suite with 28/28 tests passing and live logging stream

---

## Phase 3 — Evidence-Based Job Intelligence (Completed & Refactored)
- [x] **Data Models & 4-State Evidence Schema**:
  - `EvidenceStatus`: `NOT_REQUIRED`, `SUPPORTED`, `INSUFFICIENT_EVIDENCE`, `MISMATCH`
  - `RequirementType`: `COMPETENCY`, `DOMAIN_KNOWLEDGE`, `BEHAVIORAL`, `HARD_REQUIREMENT`
  - `EvidenceItem`: `source_type`, `source_id`, `title`, `excerpt`
  - Strict tri-state eligibility: `ELIGIBLE`, `BLOCKED`, `UNCERTAIN`
  - Strict recommendation categories: `STRONG_MATCH`, `GOOD_MATCH`, `WEAK_MATCH`, `POOR_MATCH`, `DO_NOT_APPLY`, `REVIEW_REQUIRED`
- [x] **Requirement Matcher (`requirement_matcher.py`)**:
  - Semantic and rule-based evaluation of competencies (Logical thinking, Test-First, AI utilization, Web/Mobile foundation, Problem-solving) against candidate projects, coursework, soft skills, and summaries.
- [x] **Normalized Cosine & Semantic Matcher (`semantic_matcher.py`)**:
  - Cosine normalization $(cos + 1.0) / 2.0 \in [0.0, 1.0]$.
  - Multi-project domain evaluation with automatic keyword and evidence fallback.
- [x] **Strict Tri-State Hard Filters (`hard_filters.py`)**:
  - Explicit `UNKNOWN` semantics (`UNKNOWN != PASS` and `UNKNOWN != FAIL`).
  - Strict employer exclusions (e.g. Intern-only policies rejecting Fresher/Junior).
  - Accurate Remote-only vs. Hybrid/Onsite local target location compatibility.
- [x] **7-Signal Scoring Engine (`scoring_engine.py`)**:
  - Strict weights sum invariant $= 1.0$:
    - `requirement_fit`: 0.30
    - `technical_skill_match`: 0.15
    - `project_relevance`: 0.20
    - `experience_relevance`: 0.10 (Job with no exp required $\rightarrow$ `NOT_REQUIRED`, score `1.0`)
    - `education_match`: 0.05
    - `seniority_match`: 0.05
    - `work_fit`: 0.15
  - **Smart Score Cap**: Only caps score $\le 50$ when JD has explicit required technical skills and candidate has $< 30\%$ coverage. Does NOT penalize competency-focused JDs.
- [x] **Explainable Matching (`explanation_service.py`)**:
  - Structured deterministic template with evidence citations & LLM synthesis option.
- [x] **Discord Bot UI & Commands**:
  - Slash commands registered: `/ping`, `/profile`, `/collect`, `/jobs`, `/job <id>`, `/match <id>`, `/recommend`.
  - Rich embeds with URL domain labels `[domain.com/path...](url)`, Direct Apply Action buttons, and Evidence Trails.
- [x] **Automated Test Suite**:
  - **45/45 tests passing** (100% test coverage across Unit, Integration, Golden Regression, and API lifecycles).

---

## 🐛 Bug Fixes & Architectural Hardening Log (Phase 3)

| ID | Vấn đề / Lỗi | Nguyên nhân gốc rễ | Giải pháp đã áp dụng | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | False Negative trên JD năng lực (Score Cap $\le 50$) | Engine cũ phạt 0 điểm kỹ năng khi JD không có keyword tag kỹ thuật và áp trần 50 điểm. | Chuyển sang 4-state `EvidenceStatus`: nếu JD không có tech tags $\rightarrow$ `NOT_REQUIRED` (score `1.0`, không áp trần). | ✅ **FIXED** |
| **BUG-02** | Phạt điểm ứng viên 0 năm kinh nghiệm cho vị trí Intern | Engine cũ mặc định chấm kinh nghiệm 0.5 (insufficient) cho mọi job không có kinh nghiệm. | Nếu JD là `INTERN` hoặc nêu rõ không yêu cầu kinh nghiệm $\rightarrow$ `NOT_REQUIRED` (score `1.0`). | ✅ **FIXED** |
| **BUG-03** | Khách quan hóa khoảng cách Cosine Embedding | Cosine thô $\in [-1.0, 1.0]$ khiến điểm trừ âm khi so khớp ngữ nghĩa dự án. | Chuẩn hóa phạm vi Cosine về $[0.0, 1.0]$ bằng công thức $(cos + 1.0) / 2.0$. | ✅ **FIXED** |
| **BUG-04** | Hiển thị Discord "100% Khớp 0/0" | Khi JD không có kỹ năng ưu tiên (`preferred_skills == []`), code in `100% (0/0)`. | Điều chỉnh UI hiển thị `N/A (Không yêu cầu)` và loại bỏ số đếm 0/0. | ✅ **FIXED** |
| **BUG-05** | Format URL tin tuyển dụng thô | URL hiển thị nguyên link dài gây vỡ layout Discord. | Xây dựng hàm `formatJobLink` trích xuất tên miền hiển thị `[topcv.vn/viec-lam/...](url)` và nút Action Button. | ✅ **FIXED** |
| **BUG-06** | `NameError: name 'EvidenceStatus' is not defined` | Thiếu import `EvidenceStatus` trong `explanation_service.py` khi sinh template giải thích. | Đã import `EvidenceStatus` và bổ sung unit test `test_explanation_generation_with_evidence`. | ✅ **FIXED** |
| **BUG-07** | Lẫn chuỗi rác HTML tag vào `job.skills` | TopCV cào nhầm cụm text `Không yêu cầu kinh nghiệm soft...+3` thành required skill. | Thêm bộ lọc `noise_patterns` và hàm `is_known_skill` trong `SkillNormalizer` & `job_to_dto`. | ✅ **FIXED** |
| **BUG-08** | Discord `CombinedPropertyError: length <= 1024` | Toàn bộ 7 tín hiệu và lý do dồn vào 1 embed field vượt quá 1024 ký tự. | Chia 7 tín hiệu thành 2 trường embed chuyên môn & bối cảnh, đồng thời áp dụng hàm bảo vệ `safeFieldVal` $\le 1000$ ký tự. | ✅ **FIXED** |
