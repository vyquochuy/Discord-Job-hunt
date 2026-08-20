# In Progress

## Goal
Phase 1 — Candidate Profile: Quản lý hồ sơ ứng viên và nguồn bằng chứng xác thực (Source of Truth).

## Current Status
- **Bước 1.1: Tạo Data Models cho Hồ sơ Ứng viên** (Đã hoàn thành)
- **Bước 1.2: Xây dựng Ingestion Parser & Repository Layer** (Đã hoàn thành)
- **Bước 1.3: Xây dựng Service Layer & REST API Endpoints** (Kế tiếp)

## Relevant Files
- `backend/app/services/parser.py` (CandidateProfileParser đọc YAML, TeX, MD)
- `backend/app/repositories/candidate.py` (CandidateRepository async DB operations & sync)
- `backend/app/models/candidate.py` (SQLAlchemy ORM Models)
- `backend/app/schemas/candidate.py` (Pydantic validation schemas)
- `backend/alembic/versions/002_candidate_profile_models.py` (Alembic migration)
- `backend/tests/test_candidate_parser_and_repo.py` (Unit tests)
- `context/candidate-profile.yaml` & `context/master-resume.tex` (Dữ liệu nguồn)

## Acceptance Criteria
- [x] Định nghĩa đầy đủ SQLAlchemy ORM models cho Candidate và các thực thể liên kết (Skills, Experiences, Projects, Certifications)
- [x] Tạo Pydantic schemas xác thực dữ liệu đầu vào / đầu ra
- [x] Tạo file migration Alembic `002_candidate_profile_models.py`
- [x] Parser service đọc và trích xuất dữ liệu từ `candidate-profile.yaml`, `master-resume.tex`, `master-resume.md`
- [x] Repository layer xử lý async CRUD và đồng bộ hóa context vào DB với eager loading
- [x] Toàn bộ 7 unit test cases đều passed 100%
- [ ] REST API endpoints `/api/v1/profile` (GET, PUT, POST sync)
- [ ] Discord Bot Slash Commands (`/profile`, `/profile update`, `/profile sync`)

## Next Step
Triển khai **Bước 1.3: Xây dựng Service Layer & REST API Endpoints** (`CandidateService` và các API endpoints: `GET /api/v1/profile`, `PUT /api/v1/profile`, `POST /api/v1/profile/sync`).
