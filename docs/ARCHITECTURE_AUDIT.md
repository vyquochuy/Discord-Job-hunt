# BÁO CÁO AUDIT KIẾN TRÚC & KẾ HOẠCH MIGRATION
## CHUYỂN ĐỔI TỪ DISCORD BOT-FIRST SANG WEB APPLICATION-FIRST

---

## 1. Hiện Trạng Hệ Thống (Current Architecture)

### 1.1 Tổng quan
Hệ thống AI Job Hunter hiện tại đã hoàn thành các giai đoạn nền tảng (Phase 0 đến Phase 4.5), bao gồm:
- **Backend Core (FastAPI + Async SQLAlchemy + asyncpg + PostgreSQL 16 pgvector)**:
  - `Candidate Profile & Context Synchronization`: Quản lý hồ sơ ứng viên, kỹ năng phân loại, dự án, kinh nghiệm và chứng chỉ (`candidates`, `candidate_skills`, `candidate_projects`, `candidate_experiences`, `candidate_certifications`).
  - `Job Ingestion & Deduplication`: Thu thập từ ITViec, Remotive, CareerLink, TopCV, Mock; chuẩn hóa chức danh/công ty/địa điểm; từ điển Canonical Skills Taxonomy (80+ kỹ năng); Deduplication 3 tầng (SHA-256 Signature -> RapidFuzz -> pgvector Cosine).
  - `Job Intelligence & Deterministic Scoring (Phase 3)`: Tri-state Hard Filters (`ELIGIBLE`, `BLOCKED`, `UNCERTAIN`), 7-Signal Scoring Engine với trọng số chuẩn hóa $= 1.0$, giải thích so khớp đa tầng (Evidence Trails + Deterministic Template + LLM synthesis fallback).
  - `Resume Intelligence Layer (Phase 4 & 4.5)`: `RoleClassifier` (phân loại Backend/System/Security/General), `EvidenceScorer` (chấm điểm 4 thành phần), `DiverseEvidenceSelector` (lựa chọn đa dạng năng lực MMR), `AdaptiveSummaryBuilder`, `ProvenanceVerifier` (Zero-Hallucination đối soát fact/metric 100%), `latex_generator.py` (Pure LaTeX renderer), `latex_compiler.py` (sandbox `pdflatex` build PDF), `cover_letter_generator.py`.
  - `Daily Batch Runner`: Điều phối chu kỳ cào tin và chấm điểm tự động hàng ngày (`daily_runner.py`).

- **Interface Layer Hiện Tại (Discord Bot - TypeScript / discord.js v14)**:
  - Discord Bot đóng vai trò là giao diện người dùng **duy nhất** của toàn bộ sản phẩm.
  - Toàn bộ trải nghiệm tương tác (xem tin tuyển dụng, xem chi tiết, xem giải thích match, xem gợi ý top jobs, xem/sửa hồ sơ ứng viên qua Modals, tạo CV PDF & tải trực tiếp qua file đính kèm, nộp đơn ứng tuyển qua `/apply`) đều diễn ra trong Discord.
  - Kết nối với Backend qua HTTP Client (`api-client.ts`) với header `X-Internal-Secret`.

---

## 2. Các Vấn Đề Kiến Trúc & Điểm Ghép Nối Cần Giải Quyết (Problems & Coupling)

| Hạng mục | Hiện trạng (Discord-First) | Vấn đề & Rủi ro | Giải pháp mục tiêu (Web-First) |
| :--- | :--- | :--- | :--- |
| **Giao diện người dùng (User Interface)** | 100% trong Discord (Slash commands, embeds, modals, buttons, file attachments). | Bị giới hạn nghiêm ngặt bởi Discord API (1024 ký tự/field embed, giao diện chat khó so sánh nhiều tin, không có dashboard trực quan, không có bảng Kanban/Table ứng tuyển). | Xây dựng **Web Application** độc lập (Blue theme, thông tin cô đọng, responsive, hỗ trợ đầy đủ Dashboard, Job Explorer, Match Breakdown, Profile Editor, Resume Workspace, Application Tracker). |
| **Xác thực & Danh tính (Auth & Identity)** | Dùng 1 `X-Internal-Secret` tĩnh chia sẻ giữa Discord Bot và FastAPI. Không có định danh User. | API không phân biệt được danh tính người dùng độc lập trên Web. | Thiết kế quan hệ **1–1 giữa User và Candidate Profile**. Xây dựng tầng Auth linh hoạt (Session/Token Auth), không hard-code sớm kiến trúc JWT phức tạp, vẫn hỗ trợ service-to-service key. |
| **Domain Boundary & API Contract** | Route handlers và Discord commands gắn chặt với các schema response hiện thời. | Chưa có tầng API Contract / Domain Boundary rõ ràng phân định ranh giới giữa Domain Services và UI/Web Presentation. | Bổ sung phase **API Contract / Domain Boundary**: chuẩn hóa DTOs, Error Contracts, phân tách rạch ròi Domain Layer khỏi Web Presentation và Notification. |
| **Nguồn Chân lý Hồ sơ (Source of Truth)** | `candidate-profile.yaml` và `master-resume.md` được sync vào database. | Dễ gây mơ hồ về runtime source of truth nếu người dùng chỉnh sửa hồ sơ qua Web UI. | **PostgreSQL Database là Source of Truth tuyệt đối** cho Candidate Profile tại runtime. Tệp tin `context/` đóng vai trò seed/import/export. |
| **Mô hình Thông báo (Notifications)** | Bot phản hồi trực tiếp các lệnh slash command hoặc gửi tin nhắn DM. | Không có abstraction layer cho Notification. Backend không thể tự động phát tín hiệu thông báo sang các kênh khác ngoài Discord. | Xây dựng **`NotificationService`** với abstraction interface `NotificationProvider` (`DiscordNotificationProvider`, `EmailNotificationProvider`, `WebPushProvider`). Backend chỉ gọi `NotificationService.notify()`. |
| **Lộ trình Discord Bot** | Discord Bot xử lý tất cả lệnh. | Nếu xóa ngay sẽ làm gián đoạn thói quen sử dụng. | **Chuyển dần Discord commands sang Deprecated**: các lệnh `/jobs`, `/job`, `/recommend`, `/resume` chuyển sang hiển thị bản tóm tắt ngắn và đính kèm direct link dẫn về Web App. |
| **Tài liệu & Triết lý Thiết kế (Documentation & ADRs)** | `AGENTS.MD`, `PROJECT.MD`, `ARCHITECTURE.MD`, `ROADMAP.MD`, `DECISIONS.MD` đều tuyên bố "Discord is the primary interface", "Web UI is out of scope". | Mâu thuẫn với định hướng kiến trúc mới, gây sai lệch cho các agent và kỹ sư phát triển tiếp theo. | Audit và viết lại toàn bộ documentation, bổ sung `ADR-011: Web Application-First Architecture`. |

---

## 3. Kiến Trúc Mục Tiêu (Target Architecture)

```
                            ┌─────────────────────────────────┐
                            │          Web Frontend           │
                            │        (Simple Blue UI)         │
                            │  Dashboard • Jobs • Match       │
                            │  Profile • Resumes • Apps       │
                            └────────────────┬────────────────┘
                                             │ HTTPS (REST API)
                                             ▼
                            ┌─────────────────────────────────┐
                            │      API Contract & Auth        │
                            │ ├── Auth & Identity (1-1 User)  │
                            │ ├── Profile (/api/v1/profile)   │
                            │ ├── Jobs (/api/v1/jobs)         │
                            │ ├── Matches (/api/v1/matches)   │
                            │ ├── Resumes (/api/v1/resumes)   │
                            │ └── Apps (/api/v1/applications) │
                            └────────────────┬────────────────┘
                                             │ Domain Boundary
                                             ▼
                            ┌─────────────────────────────────┐
                            │     Application & Domain Core   │
                            │  Candidate • Matching • Resume  │
                            │  Applications • Ingestion       │
                            └────────────────┬────────────────┘
                                             │
                      ┌──────────────────────┼──────────────────────┐
                      │                      │                      │
                      ▼                      ▼                      ▼
               PostgreSQL 16            AI Services            Job Pipeline
             ├── users (1-1)          ├── Role Classifier    ├── Ingestion
             ├── candidates (Truth)   ├── Evidence Scorer    ├── Normalization
             ├── jobs & raw_jobs      ├── Diverse Selector   ├── Deduplication
             ├── job_matches          ├── LaTeX Generator    └── Daily Runner
             ├── tailored_resumes     └── Provenance Verifier       │
             ├── saved_jobs                                         ▼
             └── application_logs                          ┌─────────────────┐
                                                           │  Notification   │
                                                           │     Service     │
                                                           └────────┬────────┘
                                                                    │
                                                            ┌───────┴───────┐
                                                            ▼               ▼
                                                         Discord          Email
                                                       (deprecated     (future)
                                                        commands +
                                                        notifications)
```

### Nguyên tắc cốt lõi:
1. **Business logic KHÔNG BAO GIỜ phụ thuộc vào Discord.**
2. **Web Frontend là Product Interface chính thức.**
3. **Database (PostgreSQL) là Source of Truth duy nhất** tại runtime cho toàn bộ dữ liệu ứng dụng, bao gồm cả Candidate Profile.
4. **Mối quan hệ 1–1 giữa User và Candidate Profile**: Đơn giản, rõ ràng, không phức tạp hóa multi-tenancy khi chưa cần thiết.
5. **API Contract & Domain Boundary rõ ràng**: Định nghĩa chặt chẽ REST API interface trước khi dựng UI.
6. **Discord commands chuyển sang deprecated dần**: Giữ vai trò notification adapter và quick redirect về Web App.
7. **Frontend Stack linh hoạt**: Không khóa cứng cấu trúc thư mục trước khi chọn công nghệ phù hợp.

---

## 4. Bản Đồ Chuyển Đổi Thành Phần (Migration Map)

| Module / Tệp tin | Hiện trạng | Hành động | Vai trò trong Kiến trúc mới |
| :--- | :--- | :--- | :--- |
| `backend/app/models/candidate.py` | Quản lý profile, skills, projects | **GIỮ NGUYÊN & MỞ RỘNG** | Database là Source of Truth. Quan hệ 1–1 với `User`. |
| `backend/app/models/user.py` | Chưa có | **TẠO MỚI** | Quản lý tài khoản người dùng (1–1 với Candidate). |
| `backend/app/models/job.py` | Quản lý raw_jobs, jobs, skills | **GIỮ NGUYÊN & MỞ RỘNG** | Thêm bảng `saved_jobs` để user lưu tin quan tâm trên Web. |
| `backend/app/models/match.py` | Quản lý job_matches, 7 signals | **GIỮ NGUYÊN** | Đã sẵn sàng phục vụ hiển thị chi tiết Match trên Web. |
| `backend/app/models/resume.py` | Quản lý tailored_resumes, evidence | **GIỮ NGUYÊN & MỞ RỘNG** | Mở rộng status lifecycle cho Application tracking. |
| `backend/app/core/security.py` | Chỉ kiểm tra `X-Internal-Secret` | **REFACTOR & MỞ RỘNG** | Thêm cơ chế Authentication linh hoạt cho Web, duy trì service-to-service key. |
| `backend/app/services/notifications/` | Chưa có abstraction | **TẠO MỚI** | `NotificationService`, `DiscordNotificationProvider` (Webhook/Bot API). |
| `backend/app/services/matching/` | Scoring engine, hard filters | **GIỮ NGUYÊN 100%** | Giữ nguyên logic tính điểm tất định và evidence trails. |
| `backend/app/services/tailoring/` | Resume intelligence, LaTeX, compiler | **GIỮ NGUYÊN 100%** | Độc lập hoàn toàn với UI, sinh PDF và Cover Letter phục vụ Web API. |
| `backend/app/api/v1/endpoints/auth.py` | Chưa có | **TẠO MỚI** | Endpoints authentication và user profile. |
| `backend/app/api/v1/endpoints/jobs.py` | Lọc, xem chi tiết, collect | **MỞ RỘNG** | Thêm endpoint lưu/bỏ lưu tin tuyển dụng (`/jobs/{id}/save`). |
| `backend/app/api/v1/endpoints/applications.py` | Nộp và xem lịch sử | **MỞ RỘNG** | Thêm endpoint cập nhật trạng thái đơn ứng tuyển (`PATCH /{id}/status`). |
| `frontend/` | Chưa có | **TẠO MỚI SAU KHI CHỌN STACK** | Web App (Simple Blue UI): Dashboard, Jobs, Job Detail, Recommendations, Profile, Resumes, Applications. |
| `discord-bot/` | Giao diện chính | **DEPRECATE DẦN LỆNH & CHUYỂN THÀNH ADAPTER** | Gửi thông báo & quick link về Web, deprecate dần các slash commands cũ. |
| Documentation (`AGENTS.MD`, `ARCHITECTURE.MD`, v.v.) | Mô tả Discord-first | **RE-BASELINE 100%** | Cập nhật phản ánh Web-first architecture và loại bỏ các mâu thuẫn. |

---

## 5. Đánh Giá Rủi Ro (Risk Assessment)

| Rủi ro | Mức độ | Biện pháp giảm thiểu |
| :--- | :---: | :--- |
| **Gãy tương thích ngược với dữ liệu đã có** | **THẤP** | Giữ nguyên toàn bộ cấu trúc bảng hiện tại (`jobs`, `candidates`, `job_matches`, `tailored_resumes`), chỉ tạo thêm bảng mới (`users`, `saved_jobs`) bằng Alembic migrations độc lập. |
| **Gây ảnh hưởng tới tính tất định của Matching & Zero-Hallucination** | **KHÔNG CÓ** | Logic tính điểm trong `scoring_engine.py`, `requirement_matcher.py` và `resume_intelligence.py` được giữ nguyên vẹn 100%, không bị sửa đổi bởi migration UI. |
| **Khóa sớm cấu trúc Frontend / Auth** | **THẤP** | Đặt phase API Contract / Domain Boundary lên trước; lựa chọn stack frontend và cơ chế auth đơn giản, tinh gọn trước khi tạo thư mục chi tiết. |
| **Gián đoạn trải nghiệm người dùng Discord hiện tại** | **THẤP** | Không xóa đột ngột Discord commands, chuyển dần sang trạng thái deprecated và dẫn link về Web. |

---

## 6. Lộ Trình Triển Khai Cập Nhật (Updated Implementation Order)

1. **Phase 1 — Documentation Re-baseline & Architecture Re-alignment**:
   - Cập nhật `AGENTS.MD`, `docs/ARCHITECTURE.MD`, `docs/PROJECT.MD`, `docs/ROADMAP.MD`, `docs/DECISIONS.MD`, `docs/SECURITY.MD`.
2. **Phase 2 — API Contract & Domain Boundary Definition**:
   - Định nghĩa ranh giới domain và API Contracts (Request/Response DTOs, Error Contracts, Status Enums).
   - Thiết lập User 1–1 Candidate Profile model và SavedJob model.
   - Triển khai Auth layer linh hoạt (không khóa sớm JWT phức tạp).
   - Xây dựng `NotificationService` và `NotificationProvider` abstraction.
   - Mở rộng các endpoints còn thiếu (`/jobs/{id}/save`, `/applications/{id}/status`).
3. **Phase 3 — Frontend Stack Selection & Web Application MVP**:
   - Chọn stack frontend tối ưu (Simple Blue Theme, fast, responsive).
   - Xây dựng các trang MVP: Dashboard, Jobs, Job Detail, Recommendations, Profile Editor, Resume Workspace, Application Tracker.
4. **Phase 4 — Discord Notification Adapter & Command Deprecation**:
   - Tinh chỉnh Discord Bot thành Notification Channel: khi có Daily Digest / Strong Match, gửi thông báo ngắn gọn kèm link dẫn về Web App.
   - Thêm thông báo deprecation trên các slash command cũ kèm link điều hướng sang Web.
5. **Phase 5 — Automated Testing, E2E Validation & Cleanup**:
   - Chạy toàn bộ test suites hiện có + test suites mới cho API Contracts & Auth.
   - Kiểm tra E2E flow trên Web.
   - Dọn dẹp dead code và cập nhật `tasks/DONE.MD`.
