# In Progress

## Goal
Phase 3 — Job Intelligence: Phân tích mô tả công việc (JD) và thực hiện so khớp ứng viên ↔ tin tuyển dụng (Candidate-Job Matching) với hệ thống tính điểm minh bạch (Deterministic Scoring).

## Context
Phase 1 (Candidate Profile) và Phase 2 (Job Collection) đã hoàn thành xuất sắc toàn bộ:
- Đã có hồ sơ ứng viên chuẩn hóa với skills, experiences, projects.
- Đã có cơ sở dữ liệu tin tuyển dụng với `raw_jobs` làm source of truth, `jobs` chuẩn hóa, từ điển `skills & skill_aliases` canonical dùng chung, deduplication 3 tầng và vector embeddings (`pgvector`).
- Đã có các adapters thu thập thực tế từ ITViec, Remotive, CareerLink, TopCV.

Hệ thống đã sẵn sàng 100% để bước vào Phase 3 (Matching Engine).

## Relevant Files
- `docs/ROADMAP.MD`
- `docs/AI_SYSTEM.MD`
- `docs/ARCHITECTURE.MD`
- `backend/app/models/candidate.py`
- `backend/app/models/job.py`
- `backend/app/services/normalization/skill_normalizer.py`

## Acceptance Criteria Phase 3
- [ ] Trích xuất yêu cầu JD chuyên sâu (Job Requirements Structured Output)
- [ ] Triển khai Hard Filters (Location, Work Mode, Target Roles, Minimum Salary)
- [ ] Triển khai Match Signals (Exact Skill Overlap, Semantic Fit via pgvector)
- [ ] Xây dựng Deterministic Scoring Algorithm với trọng số có thể cấu hình
- [ ] Sinh giải thích điểm số minh bạch (Match Explanation)
- [ ] Xếp hạng và phân loại độ phù hợp (Job Ranking & Recommendations)
- [ ] Tích hợp Discord Slash Commands: `/jobs`, `/job <id>`, `/match <id>`

## Next Step
Bắt đầu **Phase 3: Bước 3.1 (Thiết kế Matching Models, Hard Filters & Match Score Schemas)**.
