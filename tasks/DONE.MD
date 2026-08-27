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

| ID         | Vấn đề / Lỗi                                           | Nguyên nhân gốc rễ                                                                         | Giải pháp đã áp dụng                                                                                                       | Trạng thái   |
| :--------- | :----------------------------------------------------- | :----------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- | :----------- |
| **BUG-01** | False Negative trên JD năng lực (Score Cap $\le 50$)   | Engine cũ phạt 0 điểm kỹ năng khi JD không có keyword tag kỹ thuật và áp trần 50 điểm.     | Chuyển sang 4-state `EvidenceStatus`: nếu JD không có tech tags $\rightarrow$ `NOT_REQUIRED` (score `1.0`, không áp trần). | ✅ **FIXED** |
| **BUG-02** | Phạt điểm ứng viên 0 năm kinh nghiệm cho vị trí Intern | Engine cũ mặc định chấm kinh nghiệm 0.5 (insufficient) cho mọi job không có kinh nghiệm.   | Nếu JD là `INTERN` hoặc nêu rõ không yêu cầu kinh nghiệm $\rightarrow$ `NOT_REQUIRED` (score `1.0`).                       | ✅ **FIXED** |
| **BUG-03** | Khách quan hóa khoảng cách Cosine Embedding            | Cosine thô $\in [-1.0, 1.0]$ khiến điểm trừ âm khi so khớp ngữ nghĩa dự án.                | Chuẩn hóa phạm vi Cosine về $[0.0, 1.0]$ bằng công thức $(cos + 1.0) / 2.0$.                                               | ✅ **FIXED** |
| **BUG-04** | Hiển thị Discord "100% Khớp 0/0"                       | Khi JD không có kỹ năng ưu tiên (`preferred_skills == []`), code in `100% (0/0)`.          | Điều chỉnh UI hiển thị `N/A (Không yêu cầu)` và loại bỏ số đếm 0/0.                                                        | ✅ **FIXED** |
| **BUG-05** | Format URL tin tuyển dụng thô                          | URL hiển thị nguyên link dài gây vỡ layout Discord.                                        | Xây dựng hàm `formatJobLink` trích xuất tên miền hiển thị `[topcv.vn/viec-lam/...](url)` và nút Action Button.             | ✅ **FIXED** |
| **BUG-06** | `NameError: name 'EvidenceStatus' is not defined`      | Thiếu import `EvidenceStatus` trong `explanation_service.py` khi sinh template giải thích. | Đã import `EvidenceStatus` và bổ sung unit test `test_explanation_generation_with_evidence`.                               | ✅ **FIXED** |
| **BUG-07** | Lẫn chuỗi rác HTML tag vào `job.skills`                | TopCV cào nhầm cụm text `Không yêu cầu kinh nghiệm soft...+3` thành required skill.        | Thêm bộ lọc `noise_patterns` và hàm `is_known_skill` trong `SkillNormalizer` & `job_to_dto`.                               | ✅ **FIXED** |
| **BUG-08** | Discord `CombinedPropertyError: length <= 1024`        | Toàn bộ 7 tín hiệu và lý do dồn vào 1 embed field vượt quá 1024 ký tự.                     | Chia 7 tín hiệu thành 2 trường embed chuyên môn & bối cảnh, đồng thời áp dụng hàm bảo vệ `safeFieldVal` $\le 1000$ ký tự.  | ✅ **FIXED** |

---

## Phase 4 — Resume Intelligence & Application Automation (Completed)

- [x] **Data Models & Alembic Migration**:
  - `TailoredResume`: Quản lý phiên bản CV LaTeX đã tinh chỉnh, đường dẫn PDF, điểm Provenance, danh sách kỹ năng nổi bật.
  - `EvidenceMap`: Bản đồ kiểm chứng sự thật từng bullet point/claim đối soát với profile.
  - `CoverLetter`: Model lưu trữ thư ứng tuyển Markdown chân thực, khiêm tốn.
  - `ApplicationLog`: Ghi nhận nhật ký nộp đơn, kênh gửi, trạng thái (`DRAFT`, `READY`, `SENT`, `FAILED`, `REJECTED`, `INTERVIEW`).
  - Migration: `006_resume_tailoring_models.py` áp dụng thành công lên PostgreSQL.
- [x] **Zero-Hallucination Provenance Engine (`provenance_verifier.py`)**:
  - Đối soát 100% claim, metric, số liệu định lượng (ví dụ: `45ms`, `200 req/min`, `Argon2id`, `Shamir`) với các sự thật có sẵn từ `master-resume.tex` & `context/candidate-profile.yaml`.
  - Kết hợp `partial_ratio` và `token_set_ratio` để phân tích chính xác câu trích dẫn và câu diễn giải lại.
  - Tự động phát hiện và cảnh báo các con số/thành tích bịa đặt (Hallucinated Metrics).
- [x] **Dynamic LaTeX Generator (`latex_generator.py`)**:
  - Tuân thủ mẫu LaTeX chuẩn mực từ `context/master-resume.tex`.
  - Escape an toàn các ký tự điều khiển TeX (`&`, `%`, `$`, `#`, `_`, `~`, `^`, `{`, `}`).
  - Tái cấu trúc, sắp xếp ưu tiên các kỹ năng và dự án phù hợp nhất với JD lên đầu.
- [x] **LaTeX Compiler (`latex_compiler.py`)**:
  - Quản lý sandbox biên dịch `.tex` sang `.pdf` (`pdflatex` / `xelatex`), tự động dọn dẹp các tệp tin phụ trợ (`.aux`, `.log`, `.out`).
  - Cung cấp cơ chế Fallback an toàn khi chạy trên môi trường chưa cài đặt TeXLive.
- [x] **Cover Letter Generator (`cover_letter_generator.py`)**:
  - Tự động sinh Cover Letter Markdown ngắn gọn, chân thực, khiêm tốn, tập trung vào điểm mạnh thực tế.
  - Lưu trữ đồng thời bản ghi trong Database và tệp tin `cover_letter.md` trên đĩa.
- [x] **Orchestrator Services (`resume_service.py` & `application_service.py`)**:
  - Tự động hóa toàn bộ quy trình: Phân tích so khớp $\rightarrow$ Tinh chỉnh LaTeX $\rightarrow$ Kiểm chứng Provenance $\rightarrow$ Biên dịch PDF $\rightarrow$ Tạo Cover Letter $\rightarrow$ Lưu trữ & Nộp hồ sơ.
  - Cơ chế Idempotent Application: Ngăn chặn gửi email hoặc nộp trùng lặp cho cùng một công việc.
- [x] **REST API Endpoints**:
  - `POST /api/v1/resumes/tailor/{job_id}`: Tinh chỉnh CV và sinh PDF + Cover Letter.
  - `GET /api/v1/resumes/{id}`: Lấy chi tiết bản CV kèm bằng chứng xác thực.
  - `GET /api/v1/resumes/{id}/pdf`: Tải tệp tin PDF đã biên dịch.
  - `GET /api/v1/resumes/{id}/tex`: Lấy mã nguồn LaTeX thô.
  - `GET /api/v1/resumes/job/{job_id}`: Lấy CV đã tạo cho 1 job.
  - `POST /api/v1/applications/apply/{job_id}`: Nộp hồ sơ ứng tuyển.
  - `GET /api/v1/applications`: Xem lịch sử ứng tuyển.
  - `GET /api/v1/applications/{id}`: Xem chi tiết đơn ứng tuyển.
- [x] **Discord Slash Commands & UI**:
  - `/resume <job_id>`: Hiển thị Embed tóm tắt độ tương thích, điểm tin cậy Provenance, trích đoạn Cover Letter, và **đính kèm trực tiếp file PDF CV và file `cover_letter.md` vào tin nhắn Discord**.
  - `/apply <job_id>`: Hỗ trợ nộp hồ sơ hoặc tạo bản nháp (Draft) với đầy đủ thông tin người nhận và nhật ký kiểm toán.
- [x] **Kiểm thử tự động**:
  - **54/54 automated tests PASS 100%** (toàn bộ các test suite từ Phase 0 đến Phase 4).
  - TypeScript build của Discord Bot biên dịch thành công (`0 errors`).

---

## Phase 4.5 — Resume Intelligence Layer (Completed)

### 1. Kiến trúc Resume Intelligence Mới (`backend/app/services/tailoring/resume_intelligence.py`)

- [x] **`RoleClassifier` (Phân loại Role Family tất định)**:
  - Phân loại tự động JD thành các nhóm mục tiêu: `backend`, `system`, `security`, `general` dựa trên Title và Responsibilities.
- [x] **`EvidenceScorer` (Multi-Tier Evidence Scoring)**:
  - Chấm điểm liên quan của từng bullet point trong dự án theo 4 thành phần:
    - 35% Responsibility Match (Rapidfuzz tương đồng ngữ nghĩa với JD)
    - 30% Skill & Capability Match (Exact Tech match + Capability Domain match, không mutate công nghệ)
    - 20% Role Domain Affinity (Trọng số tương thích vai trò)
    - 15% Evidence Strength (Định lượng số liệu & metrics thực tế)
- [x] **`DiverseEvidenceSelector` (Tuyển chọn bằng chứng đa dạng)**:
  - Áp dụng thuật toán lọc đa dạng nhóm năng lực (MMR-style) để Cover Letter và CV phản ánh toàn diện các thế mạnh (vd: 1 API + 1 Database + 1 Crypto/Infrastructure), loại bỏ sự lặp lại đơn điệu.
- [x] **`AdaptiveSummaryBuilder` (Mục tiêu nghề nghiệp thích ứng)**:
  - Xây dựng Career Objective / Summary có định vị phân hóa rõ rệt cho từng domain (Backend vs System vs Security) dựa hoàn toàn trên 100% sự thật và dự án thực tế của ứng viên.
- [x] **`ResumeStrategy` Data Contract**:
  - Cung cấp nguồn sự thật chiến lược duy nhất (Single Source of Strategic Truth) cho cả Resume Generator và Cover Letter Generator.

### 2. Refactoring Generators thành Pure Renderers

- [x] **`latex_generator.py`**:
  - Chuyển thành Pure Renderer: nhận `ResumeStrategy` để render mã LaTeX hoàn chỉnh.
  - Tự động sắp xếp thứ tự các dự án (`ranked_projects`) và thứ tự các bullet points (`ranked_evidence`) theo điểm tương thích cao nhất với JD.
  - Phân nhóm và ưu tiên kỹ năng linh hoạt từ hồ sơ ứng viên (xóa bỏ hoàn toàn hardcoded skills list).
  - Giữ nguyên 100% backward compatibility cho các lệnh gọi cũ.
- [x] **`cover_letter_generator.py`**:
  - Xóa bỏ hoàn toàn hardcoded tên dự án `"VYVYCHAT"` và `"Account Manager"`.
  - Render động đoạn minh chứng dự án từ `strategy.selected_evidence`.
  - Tự động điều chỉnh các gạch đầu dòng Key Technical Alignment theo `role_family`.

### 3. Verification & Zero-Hallucination

- [x] **Kiểm thử kiểm chứng đa vai trò (`backend/tests/test_resume_intelligence.py`)**:
  - Test Relative Evidence Scoring:
    - Backend JD: `db_evidence.score > crypto_evidence.score`
    - System JD: `infra_evidence.score > crypto_evidence.score`
    - Security JD: `pki_evidence.score > db_evidence.score` và dự án EAP-TLS được xếp hạng cao nhất.
  - Test Diverse Evidence Selection: Selected evidence đại diện từ $\ge 2$ nhóm năng lực khác nhau.
  - Test Cross-Role Differentiation: 3 bản CV và 3 bản Cover Letter phân hóa hoàn toàn về câu chữ, thứ tự dự án và bullet point đầu tiên.
  - Test Zero-Hallucination: Provenance Score $\ge 90\%$ trên toàn bộ các bản CV sinh ra.
- [x] **Hồi quy hệ thống**: Toàn bộ test suite Phase 4 (`test_resume_tailoring.py`) và Phase 4.5 (`test_resume_intelligence.py`) đều **PASS 100%**.

---

## Phase 5 — API Contract & Domain Boundary Layer (Completed)

- [x] **Data Models & Database Migration**:
  - `User`: Model xác thực người dùng, thiết lập quan hệ 1–1 với `Candidate`.
  - `SavedJob`: Model quản lý danh sách tin tuyển dụng được người dùng Bookmark / Lưu lại.
  - Migration `007_user_and_saved_jobs_models.py` được tạo và kiểm thử thành công.
- [x] **Authentication & Security Engine (`backend/app/core/security.py`)**:
  - Hash mật khẩu PBKDF2-HMAC-SHA256 với salt ngẫu nhiên 16 bytes.
  - Tạo và giải mã Bearer Token linh hoạt (HMAC-SHA256 Signed Payload).
  - Dependency `get_current_user` và `get_current_user_optional`.
- [x] **REST API Contracts (`backend/app/schemas/` & `endpoints/`)**:
  - Auth: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`.
  - Saved Jobs: `GET /api/v1/jobs/saved`, `POST /api/v1/jobs/{id}/save`, `DELETE /api/v1/jobs/{id}/save`.
  - Applications: `PATCH /api/v1/applications/{id}/status`.
- [x] **Pluggable Notification Abstraction (`notification_service.py`)**:
  - Tách rời hoàn toàn nghiệp vụ khỏi Discord, tạo `NotificationService` điều phối đa kênh (`DiscordNotificationProvider`, `ConsoleNotificationProvider`).
- [x] **Test Suite**:
  - Tạo `backend/tests/test_auth_and_saved_jobs.py` kiểm thử toàn bộ luồng Auth, Bookmarks, và Notification Dispatch (**5/5 PASS**).

---

## Phase 6 — Web Application Frontend (Simple Blue) & Discord Deprecation (Completed)

- [x] **Simple Blue Design System (`frontend/css/index.css`)**:
  - Thiết kế bảng màu Simple Blue (`--primary-600: #2563eb`), typography Plus Jakarta Sans / Inter, glassmorphism, responsive grid, modal animation.
  - Hỗ trợ đầy đủ tương thích trình duyệt (thêm `-webkit-backdrop-filter`), loại bỏ hoàn toàn inline styles và cảnh báo linter.
- [x] **REST API Client (`frontend/js/api.js`)**:
  - Tự động quản lý access token, tích hợp toàn bộ các endpoint v1.
- [x] **SPA View Controllers (`frontend/js/app.js`)**:
  - **Dashboard**: Thống kê số lượng, Top đề xuất, One-click Run Daily Batch.
  - **Job Explorer**: Bộ lọc đa tiêu chí (keyword, work mode, level, location), Job Cards, và Modal chi tiết hiển thị đầy đủ JD & biểu đồ 7-Signal Matching Score.
  - **AI Top Matches**: Bảng xếp hạng các vị trí phù hợp nhất kèm lập luận bằng chứng.
  - **Resume Workspace**: tạo thiết kế CV tức thì, xem trước file PDF trực tiếp, xem Cover Letter, và kiểm tra Provenance Evidence Map.
  - **Applications Tracker**: Quản lý vòng đời đơn ứng tuyển (`DRAFT` $\rightarrow$ `READY` $\rightarrow$ `SENT` $\rightarrow$ `INTERVIEW` $\rightarrow$ `OFFER` $\rightarrow$ `REJECTED`).
  - **Candidate Profile**: Chỉnh sửa thông tin ứng viên trực tiếp lưu vào PostgreSQL và đồng bộ từ context file.
- [x] **FastAPI Mount & Production Serving**:
  - Mount `/static` và trả về `index.html` trực tiếp tại root `/`.
- [x] **Discord Bot Deprecation**:
  - Thêm `webAppUrl` vào `config.ts` và bổ sung thông báo chuyển hướng kèm link về Web App trong các slash commands.
  - TypeScript build `discord-bot` thành công (0 errors).
- [x] **Kiểm thử hồi quy toàn diện**:
  - **103/103 tests PASS 100%** trên toàn bộ test suite backend (bao gồm 10 scenario đa vai trò và adversarial test cases).

---

## Phase 4.5 — JD-Agnostic Strategic Resume Intelligence Engine (Completed)

- [x] **Typed Intermediate Representation (Single Source of Truth)**:
  - Bổ sung data contracts: `MetricFact`, `FactNode`, `JDCapabilityProfile`, `SkillRequirementType`, `ClaimVerificationStatus`, `ScoredEvidenceItem`, `DecomposedClaim`, `LayoutBudget`, `ScoredProjectCandidate`, `ProjectScoringDetail`, `ProjectSelectionResult`, `ResumeStrategy`.
- [x] **Canonical Fact Graph Builder (`fact_graph.py`)**:
  - Bóc tách phân cấp `fact_id` cho từng dự án, bullet, chứng chỉ, học vấn.
  - Regex metric fact extraction (`MetricFact`) trích xuất chính xác các chỉ số (`45ms`, `200 req/min`, `3 tables`,...).
  - Hàm `safe_get_relation` truy cập quan hệ SQLAlchemy an toàn trên cả attached và detached models ngoài session.
- [x] **Multi-Dimensional JD Capability Analyzer (`jd_capability_analyzer.py`)**:
  - Vector năng lực liên tục $[0.0, 1.0]$ trên 10 domain (`backend`, `systems`, `security`, `frontend`, `mobile`, `cloud`, `database`, `realtime`, `data_ai`, `automation`).
  - Word-boundary matching taxonomy loại bỏ hoàn toàn hiện tượng false positive từ các ký tự ngắn (`"c"`, `"db"`, `"ui"`, `"ai"`).
  - Phân loại kỹ năng 4 cấp độ: `REQUIRED`, `PREFERRED`, `IMPLICIT`, `IRRELEVANT`.
- [x] **Strategic Project Selector & Targeted MMR (`project_selector.py`)**:
  - Chấm điểm đa tín hiệu: Evidence Relevance (50%), Role Fit (30%), Direct Tech Overlap (20%), Irrelevance Penalty (-0.10).
  - Thuật toán Targeted MMR: Thưởng Diversity ($\le 0.35$) khi domain được JD yêu cầu ($\ge 0.20$), Phạt Redundancy ($-0.25$) khi năng lực trùng lặp.
  - Sinh Selection Explainability Matrix giải thích minh bạch lý do chọn/bỏ từng dự án.
- [x] **Physical Layout Planner (`layout_planner.py`)**:
  - Độc lập giải bài toán ngân sách hiển thị 1 trang A4 ATS (Max 3 dự án, Max 7 bullets tổng thể, Min 2 dự án, 1-3 bullets/dự án).
- [x] **Deterministic Claim-Level Provenance Verifier (`provenance_verifier.py`)**:
  - Phân rã bullet point thành các mệnh đề nguyên tử (`DecomposedClaim`), đối chiếu cấu trúc `FactNode` và xác thực định lượng `MetricFact`.
- [x] **10-Scenario Multi-Role & Adversarial Test Suite (`backend/tests/test_jd_agnostic_tailoring.py`)**:
  - 10 kịch bản kiểm thử: Backend FastAPI, Cybersecurity, C++ Systems, Frontend React, Mobile Flutter, Hybrid Fintech, General SWE Intern, Mismatched Java Spring Boot (Zero Hallucination), Unseen Rust/K8s (No Phantom Skills), Adversarial Metric Injection (Zero Metric Leakage).
  - **103/103 tests PASS 100%** trong toàn bộ backend test suite.

---

## 🐛 Bug Fixes & Architectural Hardening Log (Phase 4.5)

| ID         | Vấn đề / Lỗi                                                        | Nguyên nhân gốc rễ                                                                                                                                                          | Giải pháp đã áp dụng                                                                                               | Trạng thái   |
| :--------- | :------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------- | :----------- |
| **BUG-09** | Chỉ chọn 1 dự án EAP-TLS trên mọi JD                                | Substring matching `"c"` trong `DOMAIN_KEYWORD_TAXONOMY["systems"]` khiến mọi JD tiếng Việt đều nhận `systems: 0.70`, cộng với `min_projects = 1` và ngưỡng cắt sớm `0.45`. | Chuyển sang **Word-Boundary Matching** (`\bkw\b`), thiết lập `min_projects = 2` và `min_project_threshold = 0.35`. | ✅ **FIXED** |
| **BUG-10** | Lỗi chấm điểm tiếng Việt vs tiếng Anh (`responsibility_score` thấp) | So khớp fuzzy literal giữa JD tiếng Việt và Bullet tiếng Anh cho điểm thấp (~0.25).                                                                                         | Kết hợp trích xuất token kỹ thuật trực tiếp (`tech_overlap_score`) và tăng trọng số `capability_score`.            | ✅ **FIXED** |
| **BUG-11** | Detached SQLAlchemy Model khi build FactGraph                       | Truy cập relationship trên model tách session gây lỗi `MissingGreenlet` trong môi trường async test.                                                                        | Triển khai `safe_get_relation` kiểm tra `__dict__` và thuộc tính an toàn trước khi truy cập relationship.          | ✅ **FIXED** |

---

## Phase 6.1 — Full-Stack SPA Routing, Profile Synchronization & English Resume Standardization (Completed)

- [x] **Full-Stack SPA HTML5 History Routing (`frontend/js/app.js` & `backend/app/main.py`)**:
  - Hỗ trợ URL trực quan và chuyên nghiệp cho toàn bộ 7 chức năng trên thanh Sidebar:
    - 📊 Dashboard: `http://localhost:8000/dashboard` (hoặc `/`)
    - 💼 Khám phá việc làm: `http://localhost:8000/jobs`
    - ✨ Đề xuất phù hợp: `http://localhost:8000/recommendations`
    - 📄 May đo CV: `http://localhost:8000/resume`
    - 🚀 Quản lý đơn nộp: `http://localhost:8000/applications`
    - 👤 Hồ sơ ứng viên: `http://localhost:8000/profile`
    - ⚙️ Hệ thống & Dữ liệu: `http://localhost:8000/system`
  - Chuyển tab mượt mà không reload trang qua `window.history.pushState`.
  - Hỗ trợ đầy đủ nút **Back / Forward** của trình duyệt bằng bộ lắng nghe `window.onpopstate`.
  - Hỗ trợ Deep Linking, Bookmark và **F5 (Refresh)** trực tiếp tại từng trang thông qua FastAPI route `serve_spa_view` (tránh lỗi 404).

- [x] **Candidate Profile YAML Parser & Repository Hardening (`parser.py`, `candidate.py`, `hard_filters.py`, `match_service.py`)**:
  - Nâng cấp `CandidateProfileParser.load_and_merge_context` và `CandidateRepository.sync_from_parsed_context` tương thích hoàn toàn với cấu trúc YAML nâng cao: `identity`, `professional_status`, `career_preferences`, phân loại `skills` dạng dictionary `{skill: {level: ...}}` và `period` dạng dictionary `{start: ..., end: ...}`.
  - Xử lý an toàn trường `minimum_salary` khi ở dạng `int/float`, `None` hoặc dictionary `{value: ..., currency: ...}` trong `hard_filters.py` và `match_service.py`.
  - Đồng bộ thành công 54 skills, 4 projects, 0 experiences vào PostgreSQL qua API `/api/v1/profile/sync`.

- [x] **Resume Tailoring English Standardization (`resume_intelligence.py`, `latex_generator.py`, `cover_letter_generator.py`)**:
  - Tích hợp hàm `normalize_target_title_to_english` tự động chuyển đổi chức danh tiếng Việt từ JD (ví dụ: *"Thực Tập Sinh Phát Triển Phần Mềm"*, *"Thực tập sinh Backend"*, *"Lập trình viên C++"*) sang chức danh tiếng Anh chuẩn (*"Software Engineer Intern"*, *"Backend Developer Intern"*, *"C++ Software Engineer Intern"*).
  - Đảm bảo toàn bộ nội dung CV may đo (Header Title, Objective thích ứng, Bullet Points, Project Headings, Cover Letter) luôn được xuất ra **100% bằng tiếng Anh chuẩn**.
  - Cập nhật Master Resume gốc ([context/master-resume.tex](file:///c:/Game/Job-Hunt/context/master-resume.tex), [context/master-resume.md](file:///c:/Game/Job-Hunt/context/master-resume.md)) với tiêu đề chuẩn **`Software Engineer Intern`** và biên dịch thành công [context/master-resume.pdf](file:///c:/Game/Job-Hunt/context/master-resume.pdf).

- [x] **Docker Container Serving Unification (`docker-compose.yml`, `backend/app/main.py`)**:
  - Gắn volume `./frontend:/frontend:ro` vào container `jobhunter_backend` để 1 container duy nhất phục vụ trọn gói cả Backend API, Database interaction, TeXLive LaTeX compilation và Web Frontend SPA.
  - Bổ sung cơ chế phát hiện đường dẫn frontend linh hoạt (hỗ trợ cả môi trường Local lẫn Docker container).

- [x] **Kiểm thử hồi quy toàn diện**:
  - **103/103 tests PASS 100%** trên toàn bộ test suite backend.

---

## Phase 6.2 — Evidence-Grounded Resume Tailoring Engine & Anti-Hallucination Architectural Refactor (Completed)

- [x] **Pipeline Architecture Transition**:
  - Chuyển đổi toàn diện kiến trúc Resume Tailoring sang mô hình:
    `Candidate Profile` $\rightarrow$ `Evidence & Fact Extraction` $\rightarrow$ `JD Analysis & Gap Detection` $\rightarrow$ `Tailoring Strategy` $\rightarrow$ `Gemini Semantic Resume Writer` $\rightarrow$ `Claim-Level Evidence Validation & Anti-Hallucination` $\rightarrow$ `Structured Resume Model` $\rightarrow$ `Pure LaTeX Resume Renderer` $\rightarrow$ `PDF Output`.
- [x] **Technology Alias Registry (`alias_registry.py`)**:
  - Triển khai `TechnologyAliasRegistry` hỗ trợ trích xuất token theo word-boundary và chuẩn hóa canonical ID (50+ khái niệm công nghệ, loại bỏ triệt để regex false positives).
- [x] **Fact Graph & Single Source of Truth (`fact_graph.py`)**:
  - Triển khai `EvidenceRegistry` trích xuất các atomic `EvidenceFact` với danh sách canonical technologies và quantitative metrics có thật từ profile.
- [x] **JD Capability & Gap Detection (`jd_capability_analyzer.py`)**:
  - Tối ưu hóa bộ phân tích năng lực và phát hiện lỗ hổng ứng viên (`identify_candidate_gaps`), lọc bỏ các stop words miền chung (`server`, `cloud`, `infrastructure`...).
- [x] **Gemini Semantic Resume Writer (`gemini_resume_writer.py` & `resume_prompts.py`)**:
  - Tích hợp Google Gemini REST API với mô hình `gemini-3.6-flash` và cơ chế Pydantic Structured JSON Mode.
  - Phân rã mỗi bullet thành danh sách `claims: list[GeneratedClaimFragment]` kèm `evidence_ids` cụ thể để đạt tính minh bạch tối đa (granular traceability).
- [x] **Deterministic Resume Composer (`deterministic_composer.py`)**:
  - Triển khai bộ lắp ráp CV tất định offline 100% Zero-Token Cost làm fallback khi mất mạng hoặc không có API key.
- [x] **Claim-Level Validator & Unit Regeneration (`evidence_validator.py`)**:
  - Xây dựng bộ kiểm định 6 tầng: `INVALID_EVIDENCE_ID`, `UNSUPPORTED_TECHNOLOGY`, `UNSUPPORTED_METRIC`, `EXPERIENCE_INFLATION`, `UNSUPPORTED_JD_FABRICATION`, và `ARCHITECTURAL_SCOPE_SHIFT` (bảo vệ tính toàn vẹn định ngữ kiến trúc như `client-side` vs `server-side`).
  - Triển khai `UnitRegenerationOrchestrator` khóa chặt các unit hợp lệ (`locked_units`) và chỉ regenerate các unit vi phạm.
- [x] **Pure LaTeX Generator (`latex_generator.py`)**:
  - Cập nhật renderer chấp nhận trực tiếp `StructuredResumeDraft` và xuất ra mã nguồn LaTeX đạt chuẩn 1 trang A4 ATS.
- [x] **Kiểm thử hồi quy toàn diện**:
  - Xây dựng test suite `test_architectural_anti_hallucination.py` với 11 kịch bản kiểm thử nghiêm ngặt.
  - **118/118 tests PASS (100% pass rate)** trên toàn bộ repository.

