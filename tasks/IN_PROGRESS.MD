# In Progress

## Goal
Tiếp tục hoàn thiện các chốt chặn bảo mật nâng cao còn lại (SSRF DNS transport pinning `SEC-05`, cô lập test LLM `SEC-07`, lộ trình di chuyển Token sang HttpOnly Cookie `SEC-06`) và tiếp tục triển khai Phase 8 (Cloud Production Hardening: Supabase PostgreSQL pgvector, Upstash Redis Serverless, & Render Zero-Cost Deployment).

## Context
Các giai đoạn trọng yếu của hệ thống đã hoàn thành xuất sắc và được kiểm chứng toàn diện:
- **Phase 1 (Candidate Profile)**: Hồ sơ ứng viên chuẩn hóa, đồng bộ ngữ cảnh 2 chiều.
- **Phase 2 & 2.5 (Job Collection & Ad-hoc Ingestion)**: Thu thập đa nguồn tự động & nhập liệu thủ công URL/Text tức thì, deduplication 3 tầng, chuẩn hóa taxonomy.
- **Phase 3 (Job Intelligence)**: Hard filters 3 trạng thái, thuật toán tính điểm deterministic 7 tín hiệu, giải thích minh bạch.
- **Phase 4 & 4.5 & 6.2 (Evidence-Grounded Resume Tailoring Engine & Anti-Hallucination Refactor)**: Fact Graph & Evidence Registry, Canonical Technology Alias Registry, Gemini Semantic Writer (`gemini-3.6-flash`), ClaimLevelValidator (6-stage validation + Architectural Scope Shift protection), Deterministic Composer Fallback, Pure LaTeX Renderer.
- **Phase 5 & 6 (API Boundaries & Web Application Workspace)**: Kiến trúc Web-First (Simple Blue UI), phân quyền User 1-1 Candidate, Saved Jobs, Notification Service, tích hợp đầy đủ quy trình từ Job Discovery đến Dispatch.
- **Phase 8.1 & 8.2 (Cloudflare Pages Frontend & Render Backend Cloud-Ready)**: SPA routing `_redirects`, multi-tier dynamic `API_BASE` resolution, JIT PDF recompilation cho ephemeral storage của cloud container, idempotent retry safe.
- **Security Remediation (Phases 1, 2, 3 Hoàn thành & Xác thực 100%)**:
  - *Phase 1 (Tenant Isolation & Authorization)*: Đã vá hoàn toàn lỗ hổng BOLA/IDOR tại `/resumes/{id}/pdf` (`SEC-01`, hỗ trợ Bearer & Query token cho iframe), xóa bỏ lỗi chiếm đoạt candidate profile và xung đột email registration (`SEC-02`).
  - *Phase 2 (Authentication Hardening & Identity Boundaries)*: Loại bỏ cơ chế implicit masquerading `User 1` khi dùng `X-Internal-Secret` (`SEC-03`), định danh Service Principal tường minh, kiểm thử chặt chẽ vòng đời JWT (expired token, signature tampering).
  - *Phase 3 (Frontend Security & CORS)*: Gỡ bỏ wildcard regex `*.vercel.app` (`SEC-04`), whitelist nghiêm ngặt domain chỉ định; áp dụng `escapeHtml()` trong template string frontend chống DOM XSS; lập tài liệu kỹ thuật di chuyển token storage sang `HttpOnly` Cookie (`SEC-06`).
  - *Regression Test Suite*: 8/8 test bảo mật chuyên biệt pass (`test_phase1_authorization_regression.py`, `test_phase2_auth_hardening.py`, `test_phase3_cors_xss.py`).
- **Phase 9.1 (HOÀN THÀNH — 2026-11-06): Khôi phục 3 Design Theme từ Figma Make (`frontendv2/Redesign`)**:
  - **A. Modern Enterprise** (mặc định, light, phẳng, sidebar trắng, card 14px), **B. Liquid Glass** (light, `backdrop-filter: blur(26px) saturate(1.5)`, sidebar 24px, card 19px, ambient gradient), **C. AI Intelligence** (dark, `#080d1c`, card 12px gradient, glow, grid overlay 30px).
  - **Một component tree duy nhất, ba bộ token**: theme chỉ là CSS custom properties gắn qua `data-theme` trên `<html>`; không nhân bản component, không fork layout/content/business logic.
  - **Semantic migration (không phải CSS shim)**: thay toàn bộ `bg-white` / `bg-slate-*` / `text-slate-*` / tint trạng thái bằng token ngữ nghĩa (`bg-surface`, `border-border`, `text-text-muted`, `bg-success-50`…) trên ~28 file; Tailwind map `rgb(var(--*-rgb) / <alpha-value>)`.
  - **Chuyển theme runtime + không nháy**: `localStorage['jh_theme']`, script inline pre-hydration trong `index.html` set `data-theme` + `color-scheme` trước first paint; switcher A/B/C ở Topbar và mục "Giao diện" trong SystemPage.
  - **Typography bất biến**: DM Sans (body) / Manrope (display) giống hệt Figma ở cả 3 theme.
  - **Accessibility**: 4 giá trị Figma không đạt WCAG AA được nudge tối thiểu (A `--text-muted` `#697386`→`#677184`; B `--text-muted` `#607983`→`#586f79`, `--primary` `#087fba`→`#0772a7`), ghi chú inline trong `themes.css`; 28/28 cặp màu audit đạt ≥ 4.5:1.
  - **Bug thật đã vá trong quá trình verify**: overlay theme B bị tile do `background-size` hardcode (→ token `--page-overlay-size`); `Button` thiếu `whitespace-nowrap`; `Input`/`Select` wrapper thiếu `min-w-0`; `DialogHeader` thiếu `pr-14` (nút X đè badge); sidebar 244px làm nhãn "Hệ thống & Dữ liệu" + badge `Admin` tràn 1px (→ 252px); iframe PDF kế thừa `color-scheme: dark` (→ `.app-pdf-frame`); thanh accent `::after` ở nav item không có trong Figma và bị cắt thành nửa viên thuốc ở mép sidebar (→ gỡ bỏ); nhãn stat card Dashboard bị `truncate` 1 dòng (→ `line-clamp-2`); `ResumePage` nhận response không phải JSON (API base cấu hình sai) và render iframe với `undefined` trong URL (→ guard shape + toast lỗi rõ ràng).
  - **Ma trận xác minh**: 8 route × 3 theme + job-detail modal + mobile drawer, chuyển theme không reload, reload không nháy, 0 layout drift, 0 tràn ngang, 0 console error. `npm run build` xanh (1697 modules).

## Relevant Files
- `backend/app/api/v1/endpoints/resumes.py` (Vá BOLA PDF & Query Token Auth)
- `backend/app/api/v1/endpoints/auth.py` & `backend/app/repositories/candidate.py` (Vá Candidate Stealing & Race Condition)
- `backend/app/core/security.py` (Service Principal cách ly & Token Verification)
- `backend/app/main.py` (CORS domain whitelist)
- `frontend/legacy/js/` (`dashboard.page.js`, `recommendations.page.js`, `job-detail-modal.js` XSS escaping)
- `security/REVIEW_BASELINE.md` & `security/FINDINGS.md` (Hồ sơ kiểm toán & trạng thái lỗ hổng)
- `backend/tests/test_phase1_authorization_regression.py`
- `backend/tests/test_phase2_auth_hardening.py`
- `backend/tests/test_phase3_cors_xss.py`
- `docs/AUTHENTICATION_AND_JWT.md` & `MIGRATION_PLAN.md`
- `frontend/src/styles/themes.css` (Nguồn chân lý duy nhất cho 3 bộ token + treatment classes)
- `frontend/tailwind.config.js` (Map token ngữ nghĩa → CSS vars, DM Sans/Manrope)
- `frontend/src/theme/` (`tokens.ts`, `ThemeContext.tsx`, `ThemeSwitcher.tsx`)
- `frontend/index.html` (script pre-hydration chống nháy theme)
- `frontend/src/components/layout/` (`AppShell.tsx`, `Sidebar.tsx`, `Topbar.tsx`)
- `frontend/src/pages/SystemPage.tsx` (SECTION 0 "Giao diện" chọn theme)

## Next Steps
1. **SEC-05 SSRF Defense Hardening**: Bổ sung transport IP pinning cho `URLFetcher` để triệt tiêu cửa sổ Time-Of-Check to Time-Of-Use (TOCTOU) DNS rebinding.
2. **SEC-07 Test Suite Hygiene**: Mock hoàn toàn các network call tới Gemini API trong test suite để tránh timeout 429 và leak credential.
3. **Triển khai di chuyển Token sang HttpOnly Cookie** theo lộ trình đã lập tại `MIGRATION_PLAN.md`.
4. Tiếp tục hoàn thiện Phase 8.2 / 8.4 trên môi trường Cloud Production.
5. **Phase 2.7 (HOÀN THÀNH — 2026-11-04)**: Detail Page Enrichment cho Ingestion Pipeline (JSON-LD + DOM + richer-record merge, 27 tests pass) — chi tiết tại `docs/INGESTION_HARDENING.md`.
6. **Phase 2.8 (HOÀN THÀNH — 2026-11-04)**: Full Unexpired Scanning & Expiry Detection cho 5 nền tảng VN (ITViec, TopCV, TopDev, VietnamWorks, CareerLink) — `full_scan`, smart stop, `EXPIRED` status, `expire_outdated_jobs`, 18 tests pass.
7. **Phase 2.9 candidate — Expiry UX**: Ẩn job `EXPIRED` khỏi danh sách mặc định (toggle "Hiện tin đã hết hạn"), widget "tin sắp hết hạn trong 3 ngày" trên Dashboard.
8. Phase 2.9 candidate: Taxonomy 4 chiều (title/seniority/location/work-model) cho UI filter & scoring.
9. **Phase 9.1 (HOÀN THÀNH — 2026-11-06)**: Khôi phục 3 theme thiết kế Figma Make (A Modern Enterprise / B Liquid Glass / C AI Intelligence) vào `frontend/` bằng semantic CSS tokens, switcher runtime, không fork codebase — chi tiết tại `docs/DECISIONS.MD` ADR-013.
10. **Phase 9.1 follow-up (tùy chọn)**: Commit toàn bộ thay đổi theme (hiện còn uncommitted ~37 file) và chụp lại ảnh so sánh 3 theme cho tài liệu.
