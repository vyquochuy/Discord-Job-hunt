# In Progress

## Goal
Phase 8.2 — Cloud Database & Serverless Cache (0đ): Khởi tạo Supabase PostgreSQL (pgvector) & Upstash Redis Serverless phục vụ môi trường Production không chi phí.

## Context
Các giai đoạn trọng yếu của hệ thống đã hoàn thành xuất sắc và được kiểm chứng toàn diện (118/118 tests pass):
- **Phase 1 (Candidate Profile)**: Hồ sơ ứng viên chuẩn hóa, đồng bộ ngữ cảnh 2 chiều.
- **Phase 2 & 2.5 (Job Collection & Ad-hoc Ingestion)**: Thu thập đa nguồn tự động & nhập liệu thủ công URL/Text tức thì, deduplication 3 tầng, chuẩn hóa taxonomy.
- **Phase 3 (Job Intelligence)**: Hard filters 3 trạng thái, thuật toán tính điểm deterministic 7 tín hiệu, giải thích minh bạch.
- **Phase 4 & 4.5 & 6.2 (Evidence-Grounded Resume Tailoring Engine & Anti-Hallucination Refactor)**: Fact Graph & Evidence Registry, Canonical Technology Alias Registry, Gemini Semantic Writer (`gemini-3.6-flash`), ClaimLevelValidator (6-stage validation + Architectural Scope Shift protection), Deterministic Composer Fallback, Pure LaTeX Renderer.
- **Phase 5 & 6 (API Boundaries & Web Application Workspace)**: Kiến trúc Web-First (Simple Blue UI), phân quyền User 1-1 Candidate, Saved Jobs, Notification Service, tích hợp đầy đủ quy trình từ Job Discovery đến Dispatch.
- **Phase 8.1 (Frontend Cloud-Ready & Cloudflare Pages Deployment 0đ)**: Hoàn thành cấu hình SPA routing `_redirects`, multi-tier dynamic `API_BASE` resolution (`window.ENV`, `localStorage`, meta-tag, port fallback), chuẩn hóa relative asset paths, bộ điều khiển quản lý và test Ping kết nối Cloud Backend trên giao diện System, tài liệu hướng dẫn triển khai `docs/CLOUDFLARE_PAGES_GUIDE.md`.

## Relevant Files
- `frontend/_redirects`
- `frontend/env.js.example` & `frontend/env.js`
- `frontend/js/api.js` & `frontend/js/app.js`
- `frontend/index.html`
- `backend/app/main.py`
- `docs/CLOUDFLARE_PAGES_GUIDE.md`
- `docs/ROADMAP.MD`

## Next Steps
1. Tiếp tục triển khai Phase 8.2 (Cloud Database Supabase + Upstash Redis) hoặc Phase 8.3 (Zero-Cost AI Engine Migration).
2. Kiểm thử luồng ứng dụng trên live Cloudflare Pages.
