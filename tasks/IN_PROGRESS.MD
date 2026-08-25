# In Progress

## Goal
Phase 7 — Personalization & Advanced Outcome Tracking: Tối ưu hóa vòng lặp phản hồi từ kết quả ứng tuyển thực tế (Application Outcomes), học hỏi từ hành vi tương tác và hoàn thiện các tính năng nâng cao.

## Context
Các giai đoạn trọng yếu của hệ thống đã hoàn thành xuất sắc và được kiểm chứng toàn diện (103/103 tests pass):
- **Phase 1 (Candidate Profile)**: Hồ sơ ứng viên chuẩn hóa, đồng bộ ngữ cảnh 2 chiều.
- **Phase 2 & 2.5 (Job Collection & Ad-hoc Ingestion)**: Thu thập đa nguồn tự động & nhập liệu thủ công URL/Text tức thì, deduplication 3 tầng, chuẩn hóa taxonomy.
- **Phase 3 (Job Intelligence)**: Hard filters 3 trạng thái, thuật toán tính điểm deterministic 7 tín hiệu, giải thích minh bạch.
- **Phase 4 & 4.5 (JD-Agnostic Strategic Resume Intelligence)**: Hệ thống định vị chiến lược độc lập với JD, Canonical Fact Graph, Capability Analyzer đa chiều, Targeted MMR Project Selection, 1-page ATS Layout Planner, Deterministic Provenance Verifier (Zero Hallucination).
- **Phase 5 & 6 (API Boundaries & Web Application Workspace)**: Kiến trúc Web-First (Simple Blue UI), phân quyền User 1-1 Candidate, Saved Jobs, Notification Service, tích hợp đầy đủ quy trình từ Job Discovery đến Dispatch.

## Relevant Files
- `docs/ROADMAP.MD`
- `docs/AI_SYSTEM.MD`
- `docs/ARCHITECTURE.MD`
- `docs/DECISIONS.MD`
- `backend/app/services/tailoring/resume_intelligence.py`
- `backend/app/services/tailoring/project_selector.py`
- `backend/app/services/tailoring/provenance_verifier.py`
- `backend/app/services/tailoring/jd_capability_analyzer.py`

## Next Steps
1. Tiếp tục thu thập và kiểm thử chất lượng Resume trên các tin tuyển dụng thực tế (Live Ingestion Jobs).
2. Xây dựng cơ chế theo dõi tiến trình phỏng vấn / phản hồi tuyển dụng (Phase 7).

