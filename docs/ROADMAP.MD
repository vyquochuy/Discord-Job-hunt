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

## Phase 4 & 4.5 — Evidence-Grounded Strategic Resume Tailoring Engine & Anti-Hallucination Refactor

**Status:** COMPLETED

**Goal:** Chuyển đổi toàn diện công cụ tạo thiết kế hồ sơ thành một **Evidence-Grounded Resume Tailoring Engine** đa chiều, bảo đảm nguyên tắc _Evidence-Locked + Zero-Hallucination + Strategic Positioning + Granular Claim-Level Traceability_.

- [x] **Typed Intermediate Representation**: Single Source of Truth cho toàn bộ pipeline (`ResumeStrategy`, `EvidenceFact`, `EvidenceBundle`, `StructuredResumeDraft`, `GeneratedClaimFragment`, `ValidationReport`, `LayoutBudget`).
- [x] **Canonical Technology Alias Registry (`alias_registry.py`)**: Token boundary extraction và chuẩn hóa canonical ID (50+ tech terms, triệt tiêu regex false positives).
- [x] **Fact Graph & Evidence Registry (`fact_graph.py`)**: Trích xuất các nút sự thật bất biến kèm canonical technologies và định lượng `MetricFact` phục vụ đối chiếu chính xác.
- [x] **Multi-Dimensional JD Capability & Gap Analyzer (`jd_capability_analyzer.py`)**: Vector năng lực 10 domain, phát hiện lỗ hổng (`unsupported_requirements`) và lọc stop words miền chung.
- [x] **Strategic Project Selector & Targeted MMR**: Multi-signal scoring, diversity bonus cho domain JD yêu cầu, redundancy penalty cho năng lực trùng lặp.
- [x] **Physical Layout Planner (1-Page ATS)**: Độc lập giải bài toán ngân sách hiển thị A4 ATS (Max 3 dự án, Max 7 bullets, Min 2 dự án).
- [x] **Gemini Semantic Resume Writer (`gemini_resume_writer.py`)**: Tích hợp Google Gemini REST API (`gemini-3.6-flash`) với Structured JSON Mode và phân rã atomic claims kèm `evidence_ids`.
- [x] **Deterministic Resume Composer (`deterministic_composer.py`)**: Bộ lắp ráp tất định 100% offline fallback khi mất mạng hoặc không có API key.
- [x] **Claim-Level Validator & Unit Regeneration (`evidence_validator.py`)**: Bộ kiểm tra 6 tầng (`INVALID_EVIDENCE_ID`, `UNSUPPORTED_TECHNOLOGY`, `UNSUPPORTED_METRIC`, `EXPERIENCE_INFLATION`, `UNSUPPORTED_JD_FABRICATION`, `ARCHITECTURAL_SCOPE_SHIFT`) và cơ chế `UnitRegenerationOrchestrator` khóa chặt các unit hợp lệ.
- [x] **Pure LaTeX Generator & pdflatex Compiler**: Xuất bản PDF 1 trang A4 ATS và Markdown Cover Letter chuẩn mực.
- [x] **11-Scenario Multi-Role & Adversarial Test Suite**: 118/118 tests pass 100% trên toàn bộ repository.

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

---

## Phase 8 — Zero-Cost Public Production Deployment (Cloudflare Pages, Cloud PaaS, Supabase & Free LLM)

**Status:** IN PROGRESS

**Goal:** Đưa toàn bộ hệ sinh thái AI Job Hunter lên môi trường Public Production với chi phí 0đ, tối ưu hiệu năng toàn cầu (Cloudflare CDN), đảm bảo tính sẵn sàng cao và giải quyết triệt để các rào cản về hạ tầng / AI Token.

- [x] **Phase 8.1: Cloudflare Pages Frontend Deployment (0đ)**:
  - Cấu hình dynamic `API_BASE` endpoint đa tầng trong [api.js](file:///frontend/js/api.js) (hỗ trợ `window.ENV?.API_URL`, `localStorage`, meta-tag, port fallback và relative `/api/v1`).
  - Thêm quy tắc định tuyến SPA `_redirects` (`/* /index.html 200`) cho Cloudflare Pages để loại bỏ hoàn toàn lỗi 404 khi người dùng tải lại trang.
  - Chuẩn hóa toàn bộ đường dẫn static assets sang relative paths.
  - Bổ sung bộ điều khiển cấu hình Cloud API Endpoint và kiểm tra độ trễ (Ping Health Check) trên giao diện Web.
  - Tài liệu hướng dẫn chi tiết tại [CLOUDFLARE_PAGES_GUIDE.md](file:///docs/CLOUDFLARE_PAGES_GUIDE.md).
- [ ] **Phase 8.2: Cloud Database & Serverless Cache (0đ)**:
  - Khởi tạo **Supabase PostgreSQL** (Free Tier 500MB) có tích hợp sẵn extension `pgvector`.
  - Khởi tạo **Upstash Redis** (Free 10,000 commands/ngày) phục vụ message queue và caching.
- [ ] **Phase 8.3: Provider-Agnostic AI Architecture, Task-Based Routing & Quality Fallback**:
  - Xây dựng chuẩn giao tiếp `AIProvider` (Protocol) thống nhất với phương thức `generate_structured(prompt, schema, temperature)`.
  - Triển khai các Provider Adapters: `GeminiProvider` (Gemini 3.6/2.0 Flash), `GroqProvider` (LLaMA 3.3 70B, DeepSeek R1/V3 Distill), `DeepSeekProvider` (DeepSeek Chat/Reasoner), `OpenAIProvider`.
  - Xây dựng trung tâm điều phối `AIRouter`: Định tuyến động theo năng lực tác vụ (`AITask`: `jd_extraction`, `jd_analysis`, `resume_generation`, `resume_unit_regeneration`, `cover_letter`, `explanation`) với chính sách Retry, Circuit Breaker và Provider Fallback Chain.
  - Chuỗi kiểm định chất lượng (Validation-First Fallback): `LLM Output` $\rightarrow$ `JSON Schema Validation` $\rightarrow$ `ClaimLevelValidator` (Anti-Hallucination) $\rightarrow$ `Unit Regeneration` $\rightarrow$ `Fallback Provider` $\rightarrow$ `Deterministic Composer` (Offline Guaranteed).
- [ ] **Backend & Discord Bot 24/7 Deployment (0đ)**:
  - Deploy FastAPI Backend lên **Render.com** (Free Web Service) hoặc **Koyeb** / **Hugging Face Spaces**.
  - Cấu hình CORS cho phép domain Cloudflare Pages truy cập bảo mật.
  - Deploy Discord Bot lên **Hugging Face Spaces (Docker Space)** hoặc **Discloud** để duy trì kết nối WebSocket Gateway liên tục.
  - Thiết lập keep-alive ping (UptimeRobot 5 phút/lần) chống cold-sleep cho backend.
- [ ] **Cloud Storage & Persistence Hardening**:
  - Lưu trữ Profile và Tailored Resumes vào PostgreSQL / Supabase Storage để dữ liệu không bị mất khi container khởi động lại (ephemeral filesystem).

---

## Phase 9 — Enterprise SaaS Dashboard Modernization & Comprehensive Responsive Architecture (React + TypeScript + Tailwind CSS)

**Status:** COMPLETED

**Goal:** Hiện đại hóa toàn bộ giao diện Web của Job Hunter thành một SaaS dashboard production-grade đẳng cấp (Linear / Vercel-inspired), chuyển đổi sang kiến trúc React + TypeScript + Tailwind CSS + Lucide + Radix Primitives, tối ưu trải nghiệm đa thiết bị và bảo toàn 100% logic nghiệp vụ:

- [x] **Project Foundation & Modern Stack**:
  - Khởi tạo kiến trúc hiện đại: React 18, TypeScript 5.7+, Tailwind CSS 3.4, Vite 6, Lucide React, và Radix UI Primitives.
  - Cấu hình path mapping `@/*`, loại bỏ hoàn toàn dependency bloat (không dùng Redux/Zustand nặng nề).
  - Sao lưu toàn bộ mã nguồn cũ vào `frontend/legacy/` đảm bảo tính an toàn và khả năng phục hồi (recoverability).
- [x] **Design System & Reusable Component Primitives**:
  - Xây dựng Design Tokens chuẩn mực: Primary `#2563EB`, Surface `#FFFFFF`, Background `#F8FAFC`, Border `#E2E8F0`, Semantic (Success, Warning, Danger, Critical).
  - Phân tầng Typography nhất quán: `Inter` (UI/Nội dung) và `JetBrains Mono` (LaTeX/Monospace code).
  - Thư viện UI Primitives tái sử dụng: `Button` (6 biến thể), `Card`, `Badge`, `Input`, `Select`, `Dialog` (Radix), `Sheet` (Slide-out Drawer), `Tabs`, `Skeleton`, `EmptyState`, `MatchScoreBadge`.
  - `DangerConfirmDialog`: Loại bỏ hoàn toàn `window.confirm()`, bắt buộc người dùng gõ chính xác chữ `DELETE` mới mở khóa thao tác phá hủy.
- [x] **AppShell & Responsive-First Architecture (320px – 1440px)**:
  - Sidebar Desktop 240px phân chia rõ ràng các khối TỔNG QUAN, ỨNG TUYỂN & HỒ SƠ, CẤU HÌNH, kèm khu vực định danh người dùng.
  - Topbar tinh gọn chỉ chứa thông tin ngữ cảnh, trạng thái kết nối và menu tài khoản.
  - Mobile Drawer với Backdrop làm mờ, mở bằng nút Hamburger, hỗ trợ đóng bằng phím Escape và chống tràn ngang (zero horizontal overflow).
- [x] **Migrate Toàn Bộ 7 Trang Chức Năng**:
  - `/dashboard`: 4 thẻ KPI nhanh, danh sách đề xuất hàng đầu, kết nối trực tiếp database (2,300+ jobs).
  - `/jobs`: Tìm kiếm tức thì có debounce, bộ lọc đa năng (Work Mode, Level, Source), hỗ trợ Mobile Sheet Filter.
  - `/recommendations`: Bảng xếp hạng theo thuật toán tất định 7 chỉ số, nhãn phân loại Eligibility (`ELIGIBLE`, `BORDERLINE`, `INELIGIBLE`).
  - `/resume`: Resume Hub quản lý danh sách CV + Workspace 4 tabs (Bản xem PDF live, Trình soạn thảo LaTeX kèm nút lưu/biên dịch, Bảng đối soát Evidence Map, và Trình tạo Cover Letter).
  - `/applications`: Bảng quản lý ứng tuyển cho desktop và tự động chuyển sang thẻ Card cho mobile kèm dropdown đổi trạng thái trực tiếp.
  - `/profile`: Single Source of Truth cho ứng viên, tích hợp Dropzone kéo thả file CV tự động trích xuất thông tin.
  - `/system`: Phân chia 3 khối rõ ràng: Infrastructure (Ping health, latency ms), Maintenance (Dọn cache, reset điểm), Danger Zone (Purge DB có xác nhận nghiêm ngặt).
- [x] **Bảo Toàn Cơ Chế Xác Thực & API Client (Behaviorally Identical)**:
  - Giữ nguyên 100% cơ chế 30m Access Token + 30d Refresh Token Rotation (`localStorage`).
  - Bảo tồn Refresh Mutex Queue (`refreshPromise`) giải quyết triệt để xung đột 401 từ các API gọi đồng thời.
  - Tự động thử lại với Exponential Backoff khi gặp các mã lỗi tạm thời (502/503/504) và phát hiện cold-start backend.
- [x] **Docker & Production Serving**:
  - Tối ưu hóa bundle Vite (`dist/index.html`, `dist/assets/`).
  - Tích hợp FastAPI StaticFiles tự động mount `/assets` và phục vụ trực tiếp bản build production qua Docker container backend port 8000.

---

## Phase 10 — Train Model LLM Chuyên Biệt Cho Viết CV & Cover Letter

**Status:** PLANNED (Backlog)

**Goal:** Tự train / fine-tune mô hình ngôn ngữ mã nguồn mở chuyên biệt để viết CV và cover letter dựa theo JD thu thập được và profile người dùng cung cấp, tối ưu hóa chi phí token và nâng cao độ tự nhiên của văn phong.

