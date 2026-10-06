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

## Next Steps
1. **SEC-05 SSRF Defense Hardening**: Bổ sung transport IP pinning cho `URLFetcher` để triệt tiêu cửa sổ Time-Of-Check to Time-Of-Use (TOCTOU) DNS rebinding.
2. **SEC-07 Test Suite Hygiene**: Mock hoàn toàn các network call tới Gemini API trong test suite để tránh timeout 429 và leak credential.
3. **Triển khai di chuyển Token sang HttpOnly Cookie** theo lộ trình đã lập tại `MIGRATION_PLAN.md`.
4. Tiếp tục hoàn thiện Phase 8.2 / 8.4 trên môi trường Cloud Production.
