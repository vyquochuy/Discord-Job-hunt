# In Progress

## Goal
Phase 2 — Job Collection: Thu thập tự động và chuẩn hóa tin tuyển dụng từ các nguồn (Job Collectors).

## Context
Phase 1 (Candidate Profile) đã hoàn thành xuất sắc toàn bộ các bước từ Database Models, Parser, Repository, Service, REST APIs cho tới Discord Slash Command `/profile`. Dự án sẵn sàng bước sang Phase 2 để xây dựng cơ chế thu thập tin tuyển dụng.

## Relevant Files
- `docs/ROADMAP.MD`
- `docs/ARCHITECTURE.MD`
- `backend/app/models/`
- `workers/`

## Acceptance Criteria
- [ ] Xây dựng Job và Company database models
- [ ] Thiết kế JobCollector abstract interface
- [ ] Triển khai collector cho nguồn dữ liệu đầu tiên
- [ ] Chuẩn hóa tin tuyển dụng về Common Schema
- [ ] Xây dựng bộ lọc trùng lặp tin tuyển dụng (Deduplication Layer 1-3)
- [ ] Thiết lập lịch thu thập tự động qua Worker
- [ ] Theo dõi và ghi log sức khỏe của collector (Health Tracking)

## Next Step
Bắt đầu **Phase 2: Bước 2.1 (Tạo Data Models cho Job & Company)**.
