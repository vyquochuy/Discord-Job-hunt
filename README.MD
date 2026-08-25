# AI Job Hunter: Autonomous Agent & Resume Intelligence System

Nền tảng tự động hóa tìm kiếm việc làm IT, phân tích mức độ phù hợp bằng thuật toán tất định 7 chỉ số (7-Signal Matching), thiết kế hồ sơ theo từng Job Description (JD-Agnostic Resume Tailoring) chuẩn ATS/LaTeX và quản lý ứng tuyển đa kênh qua Web Workspace & Discord Bot.

> **Trạng thái:** Sẵn sàng sử dụng & Đã kiểm thử tự động toàn diện (103/103 backend automated tests passing).

---

## Mục lục

- [Kiến trúc tổng quan](#kiến-trúc-tổng-quan)
- [Yêu cầu môi trường (Prerequisites)](#yêu-cầu-môi-trường-prerequisites)
- [Bước 1: Cấu hình lần đầu (Initial Setup)](#bước-1-cấu-hình-lần-đầu-initial-setup)
  - [1.1. Thiết lập biến môi trường (.env)](#11-thiết-lập-biến-môi-trường-env)
  - [1.2. Thiết lập Hồ sơ ứng viên (Candidate Profile)](#12-thiết-lập-hồ-sơ-ứng-viên-candidate-profile)
- [Cách 1: Khởi chạy nhanh bằng Docker Compose (Khuyến nghị)](#cách-1-khởi-chạy-nhanh-bằng-docker-compose-khuyến-nghị)
- [Cách 2: Khởi chạy thủ công từng phần (Local Development)](#cách-2-khởi-chạy-thủ-công-từng-phần-local-development)
  - [2.1. Khởi động PostgreSQL & Redis](#21-khởi-động-postgresql--redis)
  - [2.2. Cài đặt & Chạy FastAPI Backend](#22-cài-đặt--chạy-fastapi-backend)
  - [2.3. Chạy Background Worker (Tùy chọn)](#23-chạy-background-worker-tùy-chọn)
  - [2.4. Chạy Discord Bot (Tùy chọn)](#24-chạy-discord-bot-tùy-chọn)
- [Hướng dẫn trải nghiệm lần đầu (First-Time User Walkthrough)](#hướng-dẫn-trải-nghiệm-lần-đầu-first-time-user-walkthrough)
- [Danh sách lệnh Discord Bot](#danh-sách-lệnh-discord-bot)
- [Kiểm thử tự động (Automated Tests)](#kiểm-thử-tự-động-automated-tests)
- [Xử lý sự cố thường gặp (Troubleshooting)](#xử-lý-sự-cố-thường-gặp-troubleshooting)
- [Tài liệu kỹ thuật chi tiết](#tài-liệu-kỹ-thuật-chi-tiết)

---

## Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────┐
│                     GIAO DIỆN NGƯỜI DÙNG                │
│  Web Workspace (Vanilla JS SPA)  │  Discord Bot (TS)    │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│              FASTAPI BACKEND & ORCHESTRATOR             │
│  - Ingestion Pipeline (TopCV, ITViec, Remotive, ...)   │
│  - 7-Signal Deterministic Matching Engine               │
│  - Resume Tailoring & TeXLive PDF Compiler Engine       │
│  - RESTful APIs (Auth, Profile, Jobs, Matches, Resumes) │
└──────────────┬───────────────────────────┬──────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────────┐ ┌────────────────────────┐
│     POSTGRESQL + PGVECTOR    │ │   REDIS QUEUE / WORKER │
│  Lưu trữ Jobs, Hồ sơ, Embeds │ │   Tác vụ cào & AI nền  │
└──────────────────────────────┘ └────────────────────────┘
```

Xem chi tiết tại [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.MD).

---

## Yêu cầu môi trường (Prerequisites)

| Thành phần                  | Phiên bản khuyến nghị | Mục đích                                                                           |
| --------------------------- | --------------------- | ---------------------------------------------------------------------------------- |
| **Docker & Docker Compose** | Phiên bản mới nhất    | **Khuyến nghị nhất** để chạy trọn gói Database, Redis, Backend, Worker và TeX Live |
| **Python**                  | 3.11+                 | Chạy Backend và Background Worker (nếu chạy local ngoài Docker)                    |
| **Node.js**                 | 18.0+ & npm           | Chạy Discord Bot (nếu chạy local ngoài Docker)                                     |
| **OpenAI API Key**          | `sk-...`              | Phục vụ trích xuất JD thô, chuẩn hóa kỹ năng và thiết kế nội dung Resume           |
| **Discord Bot Token**       | _(Tùy chọn)_          | Phục vụ điều khiển và nhận thông báo việc làm qua Discord Server                   |
| **TeX Live / pdflatex**     | _(Tùy chọn)_          | Biên dịch file `.tex` ra `.pdf` (Docker backend đã tích hợp sẵn TeX Live)          |

---

## Bước 1: Cấu hình lần đầu (Initial Setup)

### 1.1. Thiết lập biến môi trường (.env)

Tạo file `.env` từ file mẫu `.env.example`:

```bash
# Trên Linux / macOS / Git Bash:
cp .env.example .env

# Trên Windows Command Prompt:
copy .env.example .env

# Trên Windows PowerShell:
Copy-Item .env.example .env
```

Mở file `.env` và điền các thông tin quan trọng:

```env
# 1. BẮT BUỘC: API Key của OpenAI
OPENAI_API_KEY=sk-proj-your_actual_openai_api_key_here

# 2. Secret Key bảo mật giữa Backend & Discord Bot (32 ký tự ngẫu nhiên)
INTERNAL_API_SECRET=your_super_secret_internal_key_32chars_long

# 3. Cấu hình Database & Redis (Nếu dùng Docker Compose thì giữ nguyên mặc định)
POSTGRES_USER=jobhunter
POSTGRES_PASSWORD=jobhunter_secure_password
POSTGRES_DB=jobhunter_db
DATABASE_URL=postgresql+asyncpg://jobhunter:jobhunter_secure_password@postgres:5432/jobhunter_db
DATABASE_URL_SYNC=postgresql://jobhunter:jobhunter_secure_password@postgres:5432/jobhunter_db
REDIS_URL=redis://redis:6379/0

# 4. TÙY CHỌN: Cấu hình Discord Bot (nếu muốn dùng Discord Bot)
DISCORD_TOKEN=your_discord_bot_token_from_developer_portal
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_GUILD_ID=your_discord_server_id
ALLOWED_USER_ID=your_personal_discord_user_id
```

> [!TIP]
> **Lưu ý về Host kết nối:**
>
> - Khi chạy bằng **Docker Compose**: Các biến `DATABASE_URL` và `REDIS_URL` trỏ tới hostname `postgres` và `redis`.
> - Khi chạy **Local trực tiếp bằng Python**: Đổi host từ `postgres` / `redis` thành `127.0.0.1` hoặc `localhost`.

---

### 1.2. Thiết lập Hồ sơ ứng viên (Candidate Profile)

Hệ thống cần dữ liệu hồ sơ gốc của bạn để thực hiện so khớp và thiết kế CV.

1. Đảm bảo bạn đã có thư mục `context/` (nếu chưa có, sao chép từ `context.example/`):
   ```bash
   # Nếu chưa có thư mục context:
   cp -r context.example context
   ```
2. Chỉnh sửa file `context/candidate-profile.yaml`:
   - Điền thông tin cá nhân: Họ tên, Email, Số điện thoại, Vị trí mong muốn (`target_roles`), Địa điểm (`preferred_locations`), Mức lương tối thiểu (`expected_salary_min`).
   - Cập nhật danh sách Kỹ năng (`skills`), Dự án (`projects`), Kinh nghiệm (`experiences`), Học vấn (`education`).
3. _(Tùy chọn)_ Cập nhật mẫu Resume LaTeX tại `context/master-resume.tex`.

---

## Cách 1: Khởi chạy nhanh bằng Docker Compose (Khuyến nghị)

Đây là cách đơn giản và đầy đủ nhất vì Docker đã đóng gói sẵn môi trường Python, Node.js, PostgreSQL (pgvector), Redis và toàn bộ thư viện TeX Live để xuất PDF.

### Bước 1: Khởi động tất cả dịch vụ

```bash
docker compose up -d --build
```

Lệnh này sẽ tự động:

1. Khởi động **PostgreSQL 16** kèm extension `pgvector`.
2. Khởi động **Redis 7** cho hàng đợi tác vụ.
3. Chạy **Alembic migrations** để tự động tạo toàn bộ bảng trong cơ sở dữ liệu.
4. Khởi động **FastAPI Backend** tại cổng `8000`.
5. Khởi động **Background Worker** để xử lý cào tin định kỳ.
6. Khởi động **Discord Bot** (nếu đã điền Token trong `.env`).

### Bước 2: Kiểm tra trạng thái

```bash
# Xem danh sách các container đang chạy
docker compose ps

# Xem log Backend
docker compose logs -f backend
```

### Bước 3: Truy cập ứng dụng

- **Web Workspace UI**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Kiểm tra Healthcheck**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Cách 2: Khởi chạy thủ công từng phần (Local Development)

Nếu muốn phát triển hoặc debug mã nguồn trực tiếp trên máy host:

### 2.1. Khởi động PostgreSQL & Redis

Khởi chạy nhanh 2 dịch vụ phụ trợ bằng Docker:

```bash
docker compose up -d postgres redis
```

### 2.2. Cài đặt & Chạy FastAPI Backend

1. **Tạo và kích hoạt môi trường ảo Python:**

   ```bash
   # Tạo virtual environment
   python -m venv .venv

   # Kích hoạt trên Windows PowerShell:
   .venv\Scripts\activate

   # Kích hoạt trên Linux / macOS:
   source .venv/bin/activate
   ```

2. **Cài đặt dependencies:**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Cập nhật URL kết nối trong `.env` cho Local:**

   Đảm bảo trong `.env` có các dòng sau:

   ```env
   DATABASE_URL=postgresql+asyncpg://jobhunter:jobhunter_secure_password@127.0.0.1:5432/jobhunter_db
   DATABASE_URL_SYNC=postgresql://jobhunter:jobhunter_secure_password@127.0.0.1:5432/jobhunter_db
   REDIS_URL=redis://127.0.0.1:6379/0
   ```

4. **Chạy Migration Database (Alembic):**

   ```bash
   alembic upgrade head
   ```

5. **Khởi chạy máy chủ Backend:**

   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

   Mở trình duyệt tại [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

---

### 2.3. Chạy Background Worker (Tùy chọn)

Worker đảm nhận việc cào tin từ các nguồn tuyển dụng (TopCV, ITViec, Remotive, CareerLink), phân tích chuẩn hóa kỹ năng và chạy chu trình Daily Batch:

```bash
cd backend

# Cách A: Chạy 1 lần cào tin tức thời (nhanh)
python -m app.worker --run-once

# Cách B: Chạy toàn bộ chu trình Daily Batch tự động
# (Đồng bộ Profile -> Cào tin -> So khớp AI -> Sinh đề xuất)
python -m app.worker --daily-batch

# Cách C: Chạy worker ngầm liên tục định kỳ
python -m app.worker
```

---

### 2.4. Chạy Discord Bot (Tùy chọn)

Nếu bạn muốn sử dụng Discord Bot làm giao diện điều khiển:

```bash
cd discord-bot

# Cài đặt thư viện Node.js
npm install

# Khởi chạy bot ở chế độ phát triển
npm run dev
```

---

## Hướng dẫn trải nghiệm lần đầu (First-Time User Walkthrough)

Sau khi hệ thống đã khởi chạy, hãy thực hiện các bước sau để bắt đầu săn việc:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Bước 1     │     │    Bước 2    │     │    Bước 3    │     │    Bước 4    │     │    Bước 5    │
│ Đồng bộ Hồ sơ│ ──> │ Thu thập Tin │ ──> │ Xem So khớp  │ ──> │ thiết kế CV    │ ──> │ Theo dõi     │
│   (Profile)  │     │  (Job Feed)  │     │  (7 Signals) │     │ (Tailor PDF) │     │  (Kanban)    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### Bước 1: Nạp & Đồng bộ Hồ sơ Ứng viên

1. Mở Web UI tại [http://127.0.0.1:8000/](http://127.0.0.1:8000/) và chọn mục **Hồ sơ ứng viên (Profile)** ở sidebar.
2. Bấm nút **"Đồng bộ từ context/"** (Sync Profile). Hệ thống sẽ đọc file `candidate-profile.yaml`, chuẩn hóa kỹ năng và lưu vào Database.
3. _(Hoặc dùng lệnh Discord)_: `/import` hoặc `/profile sync`.

### Bước 2: Thu thập tin tuyển dụng mới

1. Chuyển sang mục **Khám phá việc làm (Jobs)**.
2. Bấm nút **"Cào tin tuyển dụng" (Collect Jobs)**.
3. Hệ thống sẽ cào tin từ các adapter (ITViec, Remotive, TopCV, CareerLink), trích xuất mức lương, địa điểm, yêu cầu kỹ năng và phân loại tự động.
4. _(Hoặc dùng lệnh Discord)_: `/collect limit:15`.

### Bước 3: Xem Đề xuất & Phân tích Độ phù hợp

1. Chuyển sang mục **Đề xuất phù hợp (Recommendations)**.
2. Hệ thống hiển thị điểm Match Score tổng hợp dựa trên 7 tiêu chí:
   - **Title Similarity:** Mức độ trùng khớp chức danh.
   - **Skills Overlap:** Độ bao phủ kỹ năng chính & kỹ năng liên quan.
   - **Experience:** Số năm kinh nghiệm yêu cầu vs thực tế.
   - **Location:** Địa điểm làm việc (Remote / Hybrid / Onsite theo thành phố).
   - **Salary:** Mức lương kỳ vọng vs ngân sách nhà tuyển dụng.
   - **Education:** Trình độ học vấn & chứng chỉ.
   - **Seniority:** Cấp bậc tương ứng (Intern / Junior / Mid / Senior).
3. Xem phân tích **Gap Analysis** để biết kỹ năng còn thiếu và chiến lược ứng tuyển.

### Bước 4: thiết kế CV tự động theo từng JD

1. Tại bất kỳ công việc nào, bấm **"Tạo thiết kế CV" (Tailor Resume)**.
2. AI sẽ tự động:
   - Phân tích từ khóa quan trọng của JD.
   - Tinh chỉnh các bullet points thành tích trong hồ sơ gốc để làm nổi bật thế mạnh phù hợp nhất với JD.
   - Tối ưu hóa theo chuẩn ATS.
   - Biên dịch ra file **PDF** và file mã nguồn **LaTeX** để bạn tải về.

### Bước 5: Quản lý Quá trình Ứng tuyển

1. Chuyển sang mục **Quản lý đơn nộp (Applications)**.
2. Sử dụng bảng Kanban để theo dõi trạng thái: `Đã lưu (Saved)` ➔ `Đã nộp (Applied)` ➔ `Phỏng vấn (Interviewing)` ➔ `Nhận Offer (Offered)` ➔ `Từ chối (Rejected)`.

---

## Danh sách lệnh Discord Bot

Nếu kích hoạt Discord Bot, bạn có thể điều khiển toàn bộ nền tảng thông qua các Slash Commands:

| Lệnh Slash                   | Mô tả tác vụ                                                        |
| ---------------------------- | ------------------------------------------------------------------- |
| `/profile view`              | Xem tóm tắt thông tin hồ sơ ứng viên hiện tại                       |
| `/profile sync`              | Đồng bộ hồ sơ từ thư mục `context/` vào database                    |
| `/import`                    | Hỗ trợ tải trực tiếp file YAML hoặc PDF lên Discord để nạp hồ sơ    |
| `/collect [limit] [source]`  | Kích hoạt chu trình cào tin tuyển dụng theo nguồn                   |
| `/jobs [keyword] [location]` | Tìm kiếm danh sách việc làm đang mở trong kho dữ liệu               |
| `/recommend [min_score]`     | Xem danh sách các công việc có điểm match cao nhất                  |
| `/match <job_id>`            | Xem bảng phân tích chi tiết 7 chỉ số so khớp cho 1 công việc cụ thể |
| `/resume <job_id>`           | Tạo CV thiết kế riêng cho công việc và tải file PDF/LaTeX đính kèm  |
| `/apply <job_id> [status]`   | Cập nhật hoặc theo dõi trạng thái ứng tuyển của công việc           |
| `/ping`                      | Kiểm tra độ trễ và trạng thái kết nối giữa Bot, Backend và Database |

---

## Kiểm thử tự động (Automated Tests)

Bộ test toàn diện gồm 103 test cases bao phủ toàn bộ pipeline từ Parser, Ingestion, Normalizer, 7-Signal Matcher đến Resume Generator:

```bash
# Kích hoạt virtual environment
.venv\Scripts\activate    # Windows
source .venv/bin/activate # Linux/macOS

# Chạy toàn bộ test suite
cd backend
pytest -v
```

---

## Xử lý sự cố thường gặp (Troubleshooting)

### 1. Lỗi kết nối Database (`Connection refused` hoặc `password authentication failed`)

- Đảm bảo container PostgreSQL đang chạy: `docker compose ps`.
- Nếu chạy Backend ngoài Docker (local), kiểm tra file `.env` đã đổi host thành `127.0.0.1` hoặc `localhost` chưa (thay vì `postgres`).
- Thử kết nối thủ công: `docker compose exec postgres psql -U jobhunter -d jobhunter_db`.

### 2. Lỗi chưa tạo bảng Database (`relation "jobs" does not exist`)

- Chạy lệnh migration của Alembic:
  ```bash
  cd backend
  alembic upgrade head
  ```

### 3. Lỗi biên dịch LaTeX (`pdflatex not found`)

- Khi chạy Backend cục bộ trên máy host, nếu máy bạn chưa cài đặt LaTeX distribution (MiKTeX/TeX Live), tính năng xuất PDF có thể báo lỗi thiếu `pdflatex`.
- **Giải pháp:** Chạy Backend thông qua Docker Compose (`docker compose up -d backend`) vì image Docker đã được tích hợp đầy đủ TeX Live.

### 4. Lỗi OpenAI API (`Rate limit exceeded` hoặc `Invalid API key`)

- Kiểm tra lại biến `OPENAI_API_KEY` trong file `.env`.
- Đảm bảo tài khoản OpenAI của bạn còn hạn mức tín dụng (quota).

### 5. Discord Bot không phản hồi lệnh

- Kiểm tra xem bạn đã thêm bot vào Server (Guild) chưa và `DISCORD_GUILD_ID` đã đúng chưa.
- Kiểm tra biến `ALLOWED_USER_ID`: Bot được cấu hình bảo mật chỉ phản hồi duy nhất ID tài khoản Discord của chủ sở hữu.

---

## Tài liệu kỹ thuật chi tiết

| Tài liệu                                       | Nội dung chi tiết                                                         |
| ---------------------------------------------- | ------------------------------------------------------------------------- |
| [`AGENTS.md`](AGENTS.MD)                       | Bộ quy tắc và ngữ cảnh phát triển cho AI Coding Agents                    |
| [`docs/PROJECT.md`](docs/PROJECT.MD)           | Định nghĩa sản phẩm, luồng nghiệp vụ và bài toán giải quyết               |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.MD) | Thiết kế kiến trúc tổng thể, mô hình dữ liệu và các luồng tương tác       |
| [`docs/AI_SYSTEM.md`](docs/AI_SYSTEM.MD)       | Đặc tả chi tiết AI Pipeline, 7-Signal Matching Engine và Prompt Templates |
| [`docs/ROADMAP.md`](docs/ROADMAP.MD)           | Lộ trình phát triển qua các giai đoạn (Phase 1 ➔ Phase 5)                 |
| [`docs/SECURITY.md`](docs/SECURITY.MD)         | Chính sách bảo mật dữ liệu cá nhân, API keys và xác thực                  |
| [`docs/DECISIONS.md`](docs/DECISIONS.MD)       | Nhật ký các quyết định kiến trúc quan trọng (ADRs)                        |

---

_Chúc bạn săn việc thành công với AI Job Hunter! 🚀_
