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

## Phase 2.5 — Manual & Ad-hoc Job Ingestion (URL / Raw Text Parsing)

**Status:** COMPLETED

**Goal:** Allow users to instantly import any external job posting via direct URL or by pasting raw unformatted job text (social media posts, Facebook, Telegram, emails) into structured jobs for immediate matching and resume tailoring.

**Scope:**

- [x] **Dual-Mode Ingestion API (`POST /api/v1/jobs/ingest-manual`):**
  - **Mode A: Raw Text Ingestion:** Parse free-form, unformatted job post text (with emojis, bullet points, salary, contact info, job descriptions, requirements).
  - **Mode B: Direct URL Ingestion:** Fetch and extract job postings directly from arbitrary web links (TopCV, LinkedIn, company career pages, Facebook, etc.) via `URLFetcher` with `JS_REQUIRED` fallback detection.
- [x] **Intelligent Job Extractor Engine:**
  - Fast rule-based + Canonical Skill Taxonomy extraction with per-field confidence scoring (`FieldConfidence`) and threshold-based LLM fallback.
  - Normalize extracted skills against Canonical Skill Taxonomy (`SkillNormalizer`).
- [x] **Instant Action Pipeline:**
  - Auto-save to `raw_jobs` (with full provenance metadata, confidence, and raw text) and `jobs` table (`source="manual"`).
  - Lazy deduplication (L1 Exact Signature -> L2 RapidFuzz) & lazy vector embedding.
  - Trigger immediate 7-signal deterministic matching (`JobMatchService`).
  - Provide 1-click action to tailor Resume & Cover Letter for the imported job.
- [x] **User Interface (Web & Discord Bot):**
  - **Web App:** Modal **"➕ Nhập JD thủ công"** with Textarea & URL input field, extraction confidence bar, field checklist, match score preview, and 1-click Tailor Resume button.
  - **Discord Bot:** Slash command `/import url <link>` and `/import text` with interactive Modal form for pasting job text directly in chat.

**Acceptance Criteria:**

- [x] User can paste raw post text (e.g., recruitment posts from Facebook/Zalo/Email) or input a URL and get a structured job entry.
- [x] Candidate can view match score and generate a tailored CV & Cover Letter for the imported job immediately without waiting for daily crawl.

---

## Phase 3 — Job Intelligence

**Status:** COMPLETED

**Goal:** Analyze job descriptions and produce candidate-job matches with deterministic scores.

- [x] Tri-state Hard Filters (`ELIGIBLE`, `BLOCKED`, `UNCERTAIN`)
- [x] 7-signal deterministic scoring engine (weights sum $= 1.0$)
- [x] Explainable matching service with verified evidence trails
- [x] Top job ranking & recommendations endpoints (`/api/v1/matches/recommendations/top`)

---

---

## Phase 4 & 4.5 — JD-Agnostic Strategic Resume Intelligence & Tailoring

**Status:** COMPLETED

**Goal:** Chuyển đổi công cụ tạo thiết kế hồ sơ thành một JD-Agnostic Strategic Resume Intelligence Engine đa chiều, bảo đảm nguyên tắc _Evidence-Locked + Zero-Hallucination + Strategic Positioning_.

- [x] **Typed Intermediate Representation**: Single Source of Truth cho toàn bộ pipeline (`ResumeStrategy`, `FactNode`, `JDCapabilityProfile`, `LayoutBudget`).
- [x] **Canonical Fact Graph & Metric Grounding**: Trích xuất nút sự thật bất biến và định lượng `MetricFact` phục vụ đối chiếu chính xác.
- [x] **Multi-Dimensional JD Capability Analyzer**: Continuous vector $[0.0, 1.0]$ trên 10 domain với word-boundary taxonomy matching chống false positives.
- [x] **Strategic Project Selector & Targeted MMR**: Multi-signal scoring, diversity bonus cho domain JD yêu cầu, redundancy penalty cho năng lực trùng lặp và Selection Explainability Matrix.
- [x] **Physical Layout Planner (1-Page ATS)**: Độc lập giải bài toán ngân sách hiển thị A4 ATS (Max 3 dự án, Max 7 bullets, Min 2 dự án).
- [x] **Claim-Level Provenance Verifier**: Phân rã mệnh đề nguyên tử (`DecomposedClaim`) và xác thực 4 trạng thái (`VERIFIED`, `PARTIALLY_VERIFIED`, `UNVERIFIED`, `CONFLICTING`).
- [x] Pure LaTeX Generator & authentic Markdown Cover Letter Generator.
- [x] 10-Scenario multi-role & adversarial test suite passing 100% (103/103 tests pass).

---

## Phase 5 — API Contract & Domain Boundary Definition

**Status:** COMPLETED

**Goal:** Phân tách rõ ràng Domain Core khỏi presentation layer, thiết lập định danh User 1–1 Candidate, lưu trữ SavedJobs, bảo mật Authentication và Notification Service abstraction.

- [x] Model `User` liên kết 1–1 với `Candidate`, model `SavedJob` lưu bookmark tin tuyển dụng.
- [x] Alembic migration `007_user_and_saved_jobs_models.py`.
- [x] Flexible Authentication Layer (`PBKDF2-HMAC-SHA256` + Bearer Token + `verify_internal_secret`).
- [x] REST API Endpoints: Auth (`/api/v1/auth/*`), Saved Jobs (`/api/v1/jobs/saved`), Application status update (`PATCH /api/v1/applications/{id}/status`).
- [x] `NotificationService` abstraction layer với `DiscordNotificationProvider` và `ConsoleNotificationProvider`.

---

## Phase 6 — Web Application Frontend (Simple Blue UI) & Discord Deprecation

**Status:** COMPLETED

**Goal:** Xây dựng Web Application hoàn chỉnh với giao diện Simple Blue UI hiện đại, biến Web thành giao diện chính và chuyển Discord Bot thành kênh thông báo phụ.

- [x] **Web Application Frontend (Simple Blue Design System)**:
  - `/login` & `/register`: Đăng nhập & Đăng ký tài khoản.
  - `/dashboard`: Tổng quan số liệu, Top gợi ý việc làm, One-click Run Daily Batch.
  - `/jobs` & `/jobs/:id`: Tìm kiếm đa tiêu chí, xem JD chi tiết, biểu đồ radar 7-Signal Matching, và nút tương tác (_Apply_, _Save_, _Tailor_).
  - `/recommendations`: Bảng xếp hạng các vị trí phù hợp nhất kèm lập luận bằng chứng.
  - `/profile`: Chỉnh sửa hồ sơ và đồng bộ context files hai chiều.
  - `/resume`: Không gian tạo thiết kế CV, xem trực tiếp PDF, Cover Letter, và kiểm tra Provenance Map.
  - `/applications`: Bảng theo dõi tiến trình ứng tuyển.
  - Modal **"➕ Nhập JD thủ công"**: Hỗ trợ dán text hoặc paste URL tin tuyển dụng bất kỳ để phân tích tức thì.
- [x] **Discord Bot Deprecation**:
  - Bổ sung thông báo kèm link chuyển hướng về Web App trong các lệnh chat.
  - Tích hợp nhận thông báo tự động từ `NotificationService`.

---

## Phase 7 — Personalization & Advanced Outcome Tracking

**Status:** IN PROGRESS

**Goal:** Tối ưu hóa vòng lặp phản hồi từ kết quả ứng tuyển thực tế (Application Outcomes), học hỏi từ hành vi tương tác và hoàn thiện các tính năng nâng cao.

- [ ] Application outcome tracking (interview, rejection, offer)
- [ ] Feedback loop to adjust matching score weights based on outcomes
- [ ] User preference learning based on save/apply patterns
