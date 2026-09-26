# AI Job Hunter: Autonomous Agent & Resume Intelligence System

Nền tảng tự động hóa tìm kiếm việc làm IT, phân tích mức độ phù hợp bằng thuật toán tất định 7 chỉ số (7-Signal Deterministic Matching), thiết kế hồ sơ theo từng Job Description chuẩn ATS/LaTeX (Evidence-Grounded Resume Tailoring) và quản lý ứng tuyển đa kênh qua Web SaaS Dashboard hiện đại & Discord Bot Adapter.

> **Trạng thái:** Sẵn sàng sử dụng & Đã kiểm thử tự động toàn diện (118/118 tests pass 100% trên toàn bộ repository).

---

## Mục lục

- [Điểm nổi bật của hệ thống (Key Features)](#điểm-nổi-bật-của-hệ-thống-key-features)
- [Kiến trúc tổng quan (Architecture Overview)](#kiến-trúc-tổng-quan-architecture-overview)
- [Ngăn xếp công nghệ (Tech Stack)](#ngăn-xếp-công-nghệ-tech-stack)
- [Yêu cầu môi trường (Prerequisites)](#yêu-cầu-môi-trường-prerequisites)
- [Bước 1: Cấu hình ban đầu (Initial Setup)](#bước-1-cấu-hình-ban-đầu-initial-setup)
  - [1.1. Thiết lập biến môi trường (.env)](#11-thiết-lập-biến-môi-trường-env)
  - [1.2. Thiết lập Hồ sơ ứng viên (Candidate Profile)](#12-thiết-lập-hồ-sơ-ứng-viên-candidate-profile)
- [Cách 1: Khởi chạy nhanh bằng Docker Compose (Khuyến nghị)](#cách-1-khởi-chạy-nhanh-bằng-docker-compose-khuyến-nghị)
- [Cách 2: Khởi chạy thủ công từng phần (Local Development)](#cách-2-khởi-chạy-thủ-công-từng-phần-local-development)
  - [2.1. Khởi động PostgreSQL & Redis](#21-khởi-động-postgresql--redis)
  - [2.2. Khởi chạy FastAPI Backend](#22-khởi-chạy-fastapi-backend)
  - [2.3. Khởi chạy Frontend Web App (Vite Dev Server)](#23-khởi-chạy-frontend-web-app-vite-dev-server)
  - [2.4. Khởi chạy Background Worker (Tùy chọn)](#24-khởi-chạy-background-worker-tùy-chọn)
  - [2.5. Khởi chạy Discord Bot (Tùy chọn)](#25-khởi-chạy-discord-bot-tùy-chọn)
- [Hướng dẫn trải nghiệm lần đầu (First-Time User Walkthrough)](#hướng-dẫn-trải-nghiệm-lần-đầu-first-time-user-walkthrough)
- [Danh sách lệnh Discord Bot](#danh-sách-lệnh-discord-bot)
- [Kiểm thử tự động (Automated Tests)](#kiểm-thử-tự-động-automated-tests)
- [Xử lý sự cố thường gặp (Troubleshooting)](#xử-lý-sự-cố-thường-gặp-troubleshooting)
- [Tài liệu kỹ thuật chi tiết](#tài-liệu-kỹ-thuật-chi-tiết)

---

## Điểm nổi bật của hệ thống (Key Features)

1. **Dashboard Doanh Nghiệp (Enterprise SaaS Dashboard):**
   * Xây dựng bằng **React 18 + TypeScript + Tailwind CSS + Lucide + Radix Primitives**.
   * Phong cách thiết kế tinh giản, chuyên nghiệp lấy cảm hứng từ Linear & Vercel.
   * Responsive 100% trên mọi kích thước màn hình (Mobile Drawer Sheet, Desktop 240px Sidebar, Tablet Collapsible Rail).
2. **Cơ chế Thu thập & Khử trùng lặp 3 Tầng (Job Ingestion Pipeline):**
   * Tự động cào tin định kỳ từ ITViec, TopCV, Remotive, CareerLink, ITNavi, GrowUpWork.
   * **Nạp JD thủ công tức thì:** Hỗ trợ dán văn bản thô (Facebook, Zalo, Email) hoặc dán link URL bất kỳ.
   * Khử trùng lặp 3 tầng: L1 (SHA-256 Exact Signature) $\rightarrow$ L2 (RapidFuzz Chuỗi) $\rightarrow$ L3 (pgvector Cosine Similarity).
3. **Thuật toán So khớp 7 Chỉ số Tất định (7-Signal Deterministic Matching):**
   * Phân loại cứng Tri-State: `ELIGIBLE`, `BORDERLINE`, `INELIGIBLE`.
   * Chấm điểm 7 tín hiệu có trọng số chuẩn hóa: Yêu cầu cốt lõi, Kỹ năng kỹ thuật, Dự án liên quan, Kinh nghiệm, Học vấn, Cấp bậc, Hình thức làm việc.
   * Hoàn toàn giải thích được (Explainable AI) với chuỗi bằng chứng xác thực (`EvidenceFact`).
4. **Tạo thiết kế CV Chuẩn ATS Khử Ảo giác (Anti-Hallucination Resume Engine):**
   * Tích hợp **Google Gemini Flash** (Structured JSON Mode) kết hợp **Deterministic Composer** 100% offline fallback.
   * **Claim-Level Validator (6 tầng):** Kiểm tra từng bullet point so với hồ sơ thật, ngăn chặn hoàn toàn việc bịa đặt kỹ năng hoặc số liệu.
   * Trình biên dịch **TeXLive pdflatex** xuất bản PDF 1 trang A4 chuẩn ATS kèm mã nguồn LaTeX và văn bản Cover Letter chuyên nghiệp.
5. **Bảo mật & Định danh Doanh nghiệp (Enterprise Authentication):**
   * Kiến trúc **Dual-Token Rotation (RTR)**: Access Token 30 phút + Refresh Token 30 ngày.
   * **Refresh Mutex Queue**: Xử lý triệt để xung đột khi nhận nhiều response 401 đồng thời, tự động retry với exponential backoff.
   * Hash mật khẩu chuẩn NIST với **Argon2id** và PBKDF2-HMAC-SHA256.

---

## Kiến trúc tổng quan (Architecture Overview)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           GIAO DIỆN NGƯỜI DÙNG                            │
│  Web SaaS Dashboard (React 18 + TS + Tailwind) │ Discord Bot Adapter (TS) │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │  HTTPS / REST / Bearer Token
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND & ORCHESTRATOR                       │
│  - Ingestion Pipeline: Canonical Skill Taxonomy, 3-Tier Deduplication     │
│  - Deterministic Matching Engine: Tri-State Filter + 7 Weighted Signals   │
│  - Resume Intelligence: Evidence Graph, Gemini 2.0/3.6, LaTeX Compiler    │
│  - RESTful APIs: Auth (RTR), Profile, Jobs, Matches, Resumes, System      │
└──────────────────────┬─────────────────────────────┬──────────────────────┘
                       │                             │
                       ▼                             ▼
┌──────────────────────────────────────┐  ┌─────────────────────────────────┐
│        POSTGRESQL 16 + PGVECTOR      │  │      REDIS QUEUE / WORKERS      │
│  Lưu trữ Jobs, Hồ sơ, Embeddings     │  │  Tác vụ cào định kỳ & AI nền    │
│  Single Source of Truth              │  │  Tự động điều phối theo lịch    │
└──────────────────────────────────────┘  └─────────────────────────────────┘
```

Xem phân tích kiến trúc chi tiết tại [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.MD) và danh mục công nghệ tại [`docs/TECH_STACK.md`](docs/TECH_STACK.md).

---

## Ngăn xếp công nghệ (Tech Stack)

| Phân vùng | Công nghệ chính | Ghi chú & Vai trò |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript 5.7+, Tailwind CSS 3.4, Vite 6, Lucide React, Radix UI | Dashboard SaaS hiện đại, data-dense, 7 views chức năng, quản lý state qua React Context + HTML5 History API |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0 (Async), Alembic, Pydantic v2 | API bất đồng bộ, ORM kết nối asyncpg, validation DTO chặt chẽ |
| **Database** | PostgreSQL 16 + pgvector | Lưu trữ quan hệ ACID kết hợp tìm kiếm tương đồng vector (Cosine similarity) |
| **In-Memory** | Redis 7 (`redis-py`) | Message broker cho workers và caching tạm thời |
| **AI & NLP** | Google Gemini Flash (`gemini-2.0-flash`, `gemini-3.6-flash`), OpenAI API | Trích xuất JD thô, sinh bản thảo CV với Structured Outputs |
| **Biên dịch**| TeXLive Minimal (`pdflatex`) | Biên dịch file `.tex` ra `.pdf` chuẩn 1 trang A4 ATS trực tiếp trong container |
| **Discord** | Discord.js v14, TypeScript, Node.js 20 LTS | Adapter giao tiếp ngoại vi, hỗ trợ 10 Slash Commands |
| **DevOps** | Docker, Docker Compose v2 | Đóng gói toàn diện 5 services (`postgres`, `redis`, `backend`, `workers`, `discord-bot`) |

---

## Yêu cầu môi trường (Prerequisites)

| Thành phần | Phiên bản khuyến nghị | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Docker & Docker Compose** | Phiên bản mới nhất | **Khuyến nghị nhất** để chạy trọn gói Database, Redis, Backend, Workers, Discord Bot và TeXLive |
| **Python** | 3.11+ | Chạy Backend và Background Worker nếu phát triển cục bộ ngoài Docker |
| **Node.js & npm** | Node.js 18.0+ & npm 9+ | Chạy Frontend Vite Dev Server hoặc Discord Bot cục bộ |
| **Google Gemini API Key** | `AIzaSy...` | Phục vụ trích xuất JD, phân tích khoảng cách năng lực và sinh bản thảo CV |
| **OpenAI API Key** | `sk-...` | _(Tùy chọn)_ Tương thích với các tác vụ trích xuất hoặc provider fallback |
| **Discord Bot Token** | _(Tùy chọn)_ | Phục vụ tương tác và nhận thông báo việc làm qua Discord Server |

---

## Bước 1: Cấu hình ban đầu (Initial Setup)

### 1.1. Thiết lập biến môi trường (.env)

Tạo file `.env` từ file mẫu `.env.example`:

```bash
# Trên Linux / macOS / Git Bash:
cp .env.example .env

# Trên Windows PowerShell:
Copy-Item .env.example .env
```

Mở file `.env` và thiết lập các tham số:

```env
# 1. API Keys cho AI Models
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
OPENAI_API_KEY=your_openai_api_key_here

# 2. Secret Key bảo mật & JWT (32 ký tự ngẫu nhiên)
INTERNAL_API_SECRET=your_super_secret_internal_key_32chars_long
JWT_SECRET_KEY=your_jwt_secret_key_32chars_long

# 3. Tài khoản Quản trị viên khởi tạo lần đầu
ADMIN_EMAIL=admin@jobhunter.local
ADMIN_INITIAL_PASSWORD=JobHunterAdmin2026!

# 4. Cấu hình Database & Redis (Nếu dùng Docker Compose thì giữ nguyên mặc định)
POSTGRES_USER=jobhunter
POSTGRES_PASSWORD=jobhunter_secure_password
POSTGRES_DB=jobhunter_db
DATABASE_URL=postgresql+asyncpg://jobhunter:jobhunter_secure_password@postgres:5432/jobhunter_db
DATABASE_URL_SYNC=postgresql://jobhunter:jobhunter_secure_password@postgres:5432/jobhunter_db
REDIS_URL=redis://redis:6379/0

# 5. TÙY CHỌN: Cấu hình Discord Bot
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_GUILD_ID=your_discord_server_id
ALLOWED_USER_ID=your_personal_discord_user_id
```

> [!TIP]
> **Lưu ý về Host kết nối:**
> - Khi chạy bằng **Docker Compose**: `DATABASE_URL` và `REDIS_URL` trỏ tới hostname `postgres` và `redis`.
> - Khi chạy **Local trực tiếp ngoài Docker**: Đổi hostname từ `postgres`/`redis` thành `127.0.0.1` hoặc `localhost`.

---

### 1.2. Thiết lập Hồ sơ ứng viên (Candidate Profile)

Hệ thống cần dữ liệu hồ sơ gốc của bạn làm Single Source of Truth để đối chiếu:

1. Đảm bảo bạn đã có thư mục `context/` (sao chép từ `context.example/` nếu chưa có):
   ```bash
   cp -r context.example context
   ```
2. Chỉnh sửa file `context/candidate-profile.yaml`:
   - Điền thông tin cá nhân: Họ tên, Email, Số điện thoại, Vị trí mong muốn (`target_roles`), Địa điểm (`preferred_locations`), Mức lương kỳ vọng.
   - Cập nhật danh sách Kỹ năng (`skills`), Dự án (`projects`), Kinh nghiệm làm việc (`experiences`), Học vấn (`education`).
3. Bạn cũng có thể kéo thả trực tiếp file CV dạng PDF/DOCX trên trang **Hồ sơ ứng viên (`/profile`)** của giao diện Web để tự động trích xuất thông tin.

---

## Cách 1: Khởi chạy nhanh bằng Docker Compose (Khuyến nghị)

Docker Compose là phương thức triển khai trọn gói, chuẩn hóa môi trường tự động:

### Bước 1: Khởi động tất cả dịch vụ

```bash
docker compose up -d --build
```

Lệnh này sẽ tự động:
1. Khởi động **PostgreSQL 16 (pgvector)** và kiểm tra sức khỏe.
2. Khởi động **Redis 7** cho hàng đợi tác vụ.
3. Chạy **Alembic migrations** tạo toàn bộ cấu trúc bảng và tài khoản admin ban đầu.
4. Khởi động **FastAPI Backend** tại cổng `8000` (tự động phục vụ Web App production bundle).
5. Khởi động **Background Workers** cào tin và tính toán ngầm.
6. Khởi động **Discord Bot** (nếu token hợp lệ).

### Bước 2: Kiểm tra trạng thái containers

```bash
# Xem trạng thái hoạt động của 5 containers
docker compose ps

# Xem log Backend
docker compose logs -f backend
```

### Bước 3: Truy cập ứng dụng

* **Web SaaS Dashboard:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Swagger API Interactive Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Kiểm tra Healthcheck:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Cách 2: Khởi chạy thủ công từng phần (Local Development)

Dành cho phát triển tính năng, kiểm thử giao diện với Hot Module Replacement (HMR):

### 2.1. Khởi động PostgreSQL & Redis

```bash
docker compose up -d postgres redis
```

### 2.2. Khởi chạy FastAPI Backend

1. **Khởi tạo và kích hoạt virtual environment:**
   ```bash
   python -m venv .venv

   # Trên Windows PowerShell:
   .venv\Scripts\activate

   # Trên Linux / macOS:
   source .venv/bin/activate
   ```
2. **Cài đặt thư viện backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. **Chạy Migration Database:**
   ```bash
   alembic upgrade head
   ```
4. **Khởi động server Backend:**
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

### 2.3. Khởi chạy Frontend Web App (Vite Dev Server)

Mở một cửa sổ Terminal mới:

```bash
cd frontend

# Cài đặt dependencies (React, TypeScript, Tailwind, Radix)
npm install

# Khởi chạy Vite dev server với Hot Module Replacement
npm run dev
```

Truy cập giao diện phát triển tại: [http://127.0.0.1:5173/](http://127.0.0.1:5173/)  
*(Vite tự động kết nối API Backend tại `http://127.0.0.1:8000`)*.

Để đóng gói bản build production:
```bash
npm run build
```

### 2.4. Khởi chạy Background Worker (Tùy chọn)

```bash
cd backend

# Cách A: Chạy cào tin một lần tức thời
python -m app.worker --run-once

# Cách B: Chạy trọn vẹn chu trình Daily Batch (Sync -> Crawl -> Score -> Recommend)
python -m app.worker --daily-batch

# Cách C: Chạy worker liên tục theo chu kỳ định thời
python -m app.worker
```

### 2.5. Khởi chạy Discord Bot (Tùy chọn)

```bash
cd discord-bot
npm install
npm run dev
```

---

## Hướng dẫn trải nghiệm lần đầu (First-Time User Walkthrough)

Sau khi hệ thống khởi chạy, trải nghiệm luồng làm việc khép kín qua 5 bước:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Bước 1      │     │     Bước 2      │     │     Bước 3      │     │     Bước 4      │     │     Bước 5      │
│ Đồng bộ Hồ sơ   │ ──> │ Thu thập & Nạp  │ ──> │ Xem So khớp 7   │ ──> │ Thiết kế CV     │ ──> │ Quản lý Tiến độ │
│ (/profile)      │     │ Tin (/jobs)     │     │ Tín hiệu        │     │ Chuẩn ATS       │     │ Đơn (/apps)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Bước 1: Đồng bộ Hồ sơ Ứng viên (`/profile`)
1. Truy cập mục **Hồ sơ ứng viên**. Đăng nhập với tài khoản của bạn (hoặc tài khoản Admin).
2. Bấm nút **"Đồng bộ từ context/"** hoặc kéo thả file CV hiện tại của bạn vào khung dropzone.
3. Hệ thống sẽ tự động phân tích, chuẩn hóa danh mục kỹ năng và lưu vào PostgreSQL.

### Bước 2: Thu thập & Nạp Tin Tuyển Dụng (`/jobs`)
1. Chuyển sang mục **Khám phá việc làm**.
2. **Cách A (Quét tự động):** Bấm nút **"Quét tin tuyển dụng"** để cào hàng loạt từ ITViec, TopCV, Remotive...
3. **Cách B (Nạp JD tức thì):** Bấm nút **"Nhập JD"**, dán đoạn văn bản tuyển dụng bất kỳ từ Facebook/Email hoặc dán link URL. Hệ thống tự động bóc tách thành công việc có cấu trúc ngay lập tức.

### Bước 3: Xem Đề xuất & Phân tích Tương thích (`/recommendations`)
1. Chuyển sang mục **Đề xuất phù hợp**.
2. Hệ thống xếp hạng công việc theo điểm **Match Score** tổng hợp và gắn nhãn: `ELIGIBLE`, `BORDERLINE`, `INELIGIBLE`.
3. Bấm vào từng tin để mở modal phân tích radar **7 chỉ số**: Yêu cầu cốt lõi, Kỹ năng kỹ thuật, Dự án liên quan, Kinh nghiệm, Học vấn, Cấp bậc, Hình thức làm việc.

### Bước 4: Thiết kế CV Chuyên Biệt Theo Từng JD (`/resume`)
1. Tại tin tuyển dụng mong muốn, bấm nút **"Tạo thiết kế CV"**.
2. Hệ thống chuyển sang **Resume Workspace**:
   * **Bản xem PDF:** Xem trực tiếp file PDF 1 trang A4 đã được biên dịch qua TeXLive.
   * **Mã LaTeX:** Tinh chỉnh trực tiếp mã nguồn LaTeX và bấm **"Lưu & Biên dịch lại"**.
   * **Evidence Map:** Kiểm tra bảng đối soát độ tin cậy của các luận điểm.
   * **Cover Letter:** Sao chép nội dung thư ứng tuyển đã được tối ưu hóa.

### Bước 5: Quản lý Quá trình Ứng tuyển (`/applications`)
1. Chuyển sang mục **Quản lý đơn nộp**.
2. Theo dõi trạng thái đơn qua bảng dữ liệu hoặc thẻ di động: `DRAFT` $\rightarrow$ `READY` $\rightarrow$ `SENT` $\rightarrow$ `INTERVIEW` $\rightarrow$ `OFFER` $\rightarrow$ `REJECTED`.

---

## Danh sách lệnh Discord Bot

Nếu kích hoạt Discord Bot, bạn có thể điều khiển toàn bộ nền tảng qua Slash Commands:

| Lệnh Slash | Mô tả tác vụ |
| :--- | :--- |
| `/profile view` | Xem tóm tắt thông tin hồ sơ ứng viên hiện tại |
| `/profile sync` | Đồng bộ hồ sơ từ thư mục `context/` vào database |
| `/import` | Hỗ trợ tải trực tiếp file YAML hoặc PDF lên Discord để nạp hồ sơ |
| `/collect [limit] [source]` | Kích hoạt chu trình cào tin tuyển dụng theo nguồn |
| `/jobs [keyword] [location]` | Tìm kiếm danh sách việc làm đang mở trong kho dữ liệu |
| `/recommend [min_score]` | Xem danh sách các công việc có điểm match cao nhất |
| `/match <job_id>` | Xem bảng phân tích chi tiết 7 chỉ số so khớp cho 1 công việc cụ thể |
| `/resume <job_id>` | Tạo CV thiết kế riêng cho công việc và tải file PDF/LaTeX đính kèm |
| `/apply <job_id> [status]` | Cập nhật hoặc theo dõi trạng thái ứng tuyển của công việc |
| `/ping` | Kiểm tra độ trễ và trạng thái kết nối giữa Bot, Backend và Database |

---

## Kiểm thử tự động (Automated Tests)

Repository tích hợp bộ test tự động toàn diện gồm **118 test cases** bao phủ toàn bộ pipeline từ Parser, Ingestion, Canonical Skill Normalizer, 7-Signal Deterministic Matcher đến Anti-Hallucination Resume Engine:

```bash
# Kích hoạt virtual environment
.venv\Scripts\activate    # Windows
source .venv/bin/activate # Linux / macOS

# Chạy toàn bộ test suite
cd backend
pytest -v
```

Kiểm tra biên dịch Type-Check & đóng gói Frontend:
```bash
cd frontend
npm run build
```

---

## Xử lý sự cố thường gặp (Troubleshooting)

### 1. Lỗi kết nối Database (`Connection refused` hoặc `password authentication failed`)
* Đảm bảo container PostgreSQL đang chạy và ở trạng thái healthy: `docker compose ps`.
* Nếu chạy Backend ngoài Docker (local host), đảm bảo file `.env` đã cấu hình host là `127.0.0.1` hoặc `localhost` (thay vì `postgres`).

### 2. Lỗi chưa tạo bảng Database (`relation "jobs" does not exist`)
* Chạy lệnh migration của Alembic:
  ```bash
  cd backend
  alembic upgrade head
  ```

### 3. Lỗi biên dịch LaTeX (`pdflatex not found`)
* Khi chạy Backend trực tiếp trên máy host, nếu máy chưa cài đặt LaTeX distribution (MiKTeX/TeX Live), tính năng xuất PDF sẽ báo lỗi thiếu `pdflatex`.
* **Khuyến nghị:** Khởi chạy Backend qua Docker Compose (`docker compose up -d backend`) vì image Docker đã được đóng gói sẵn bộ TeX Live tối giản.

### 4. Lỗi Quá Hạn Mức AI (`Rate limit exceeded` hoặc `Invalid API key`)
* Kiểm tra lại biến `GEMINI_API_KEY` hoặc `OPENAI_API_KEY` trong file `.env`.
* Đảm bảo key còn hạn mức sử dụng và không bị chặn IP.

### 5. Discord Bot không phản hồi lệnh
* Đảm bảo bạn đã mời Bot vào Discord Server và cấu hình chính xác `DISCORD_GUILD_ID`.
* Kiểm tra biến `ALLOWED_USER_ID`: Bot được cấu hình bảo mật chỉ nhận lệnh từ đúng ID tài khoản của chủ sở hữu.

---

## Tài liệu kỹ thuật chi tiết

| Tài liệu | Nội dung chi tiết |
| :--- | :--- |
| [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | **Ngăn xếp công nghệ toàn diện & đặc tả kiến trúc kỹ thuật mới** |
| [`docs/ROADMAP.md`](docs/ROADMAP.MD) | **Lộ trình phát triển qua các giai đoạn (Phase 0 ➔ Phase 9 Completed)** |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.MD) | Thiết kế kiến trúc tổng thể, mô hình dữ liệu và luồng tương tác |
| [`docs/AUTHENTICATION_AND_JWT.md`](docs/AUTHENTICATION_AND_JWT.md) | Đặc tả bảo mật Dual-Token Rotation (RTR) và Mutex Refresh Queue |
| [`docs/AI_SYSTEM.md`](docs/AI_SYSTEM.MD) | Đặc tả AI Pipeline, 7-Signal Matching Engine và Prompt Templates |
| [`docs/SECURITY.md`](docs/SECURITY.MD) | Chính sách bảo mật dữ liệu cá nhân, API keys và phân quyền RBAC |
| [`docs/DECISIONS.md`](docs/DECISIONS.MD) | Nhật ký các quyết định kiến trúc quan trọng (ADRs) |
| [`AGENTS.md`](AGENTS.MD) | Bộ quy tắc và ngữ cảnh phát triển cho AI Coding Agents |

---

_Chúc bạn săn việc thành công với AI Job Hunter! 🚀_
