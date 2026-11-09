# Hệ Thống Công Nghệ & Kiến Trúc Kỹ Thuật (Tech Stack Specification)

> **Dự án:** Job Hunter Platform — Autonomous Agent & Resume Intelligence System  
> **Đối chiếu mã nguồn:** 2026-11-09. Mô tả cấu hình repository, không khẳng định deployment hay hiệu năng đã kiểm chứng. Simple Blue/Vanilla JS là thiết kế lịch sử; frontend hiện tại là Liquid Glass sáng/tối.

---

## 1. Tổng quan Kiến trúc (Architecture Overview)

Hệ thống được thiết kế theo mô hình **Service-Oriented Decoupled Architecture**, phân tách độc lập giữa **Presentation Layer** (Web SaaS Dashboard & Discord Bot), **Domain Core** (FastAPI Orchestrator, AI Engines, LaTeX Compiler), **Persistence Layer** (PostgreSQL 16 + pgvector, Redis Queue) và **Autonomous Background Workers**.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                              │
│   Web Application (React 18 + TypeScript + Tailwind CSS + Radix + Vite)   │
│   Discord Bot Adapter (Node.js 20 + TypeScript + Discord.js v14)          │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │  HTTPS / REST / Bearer Token
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      CORE API & DOMAIN ORCHESTRATION                      │
│   FastAPI (Python 3.11, async/await, SQLAlchemy 2.0 Async, Pydantic v2)   │
│   - Ingestion Pipeline: Canonical Taxonomy, 3-Tier Deduplication          │
│   - Matching Engine: Tri-State Hard Filter + 7 Deterministic Signals      │
│   - Resume Intelligence: Evidence Graph, Gemini configurable, LaTeX Compiler   │
│   - Application Tracking: Status lifecycle & Audit logging                │
└──────────────────────┬─────────────────────────────┬──────────────────────┘
                       │                             │
                       ▼                             ▼
┌──────────────────────────────────────┐  ┌─────────────────────────────────┐
│          PERSISTENCE LAYER           │  │       BACKGROUND WORKERS        │
│  PostgreSQL 16 + pgvector extension  │  │  Autonomous Ingestion & Crawl   │
│  Single Source of Truth              │  │  Redis 7 Message Queue          │
└──────────────────────────────────────┘  └─────────────────────────────────┘
```

---

## 2. Chi Tiết Ngăn Xếp Công Nghệ (Tech Stack Details)

### 2.1. Frontend Web Application (SaaS Dashboard)

Giao diện Web đã được hiện đại hóa toàn diện từ Vanilla JavaScript sang kiến trúc chuẩn Enterprise SaaS:

| Thành phần | Công nghệ / Thư viện | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Core Framework** | **React 18** | UI Component-driven, Concurrent Rendering, Virtual DOM hiệu năng cao. |
| **Language** | **TypeScript 5.7+** | Type-safety tuyệt đối, kiểm soát chặt chẽ schema DTO tương thích với backend. |
| **Build Tool & Bundler** | **Vite 6** | Dev server HMR; `npm run build` chạy `tsc -b && vite build`, xuất `frontend/dist`. |
| **Styling & Design System** | **Tailwind CSS 3.4** + **PostCSS** | Utility classes dùng semantic tokens trong `src/styles/themes.css`, Liquid Glass sáng/tối. |
| **Iconography** | **Lucide React** | Bộ vector icons nhất quán, chuẩn hóa ngữ cảnh và trạng thái trực quan. |
| **Accessible Primitives** | **@radix-ui/react-dialog**, **@radix-ui/react-tabs**, **@radix-ui/react-dropdown-menu**, **@radix-ui/react-tooltip** | Primitives không phụ thuộc style, đảm bảo WCAG A11y, quản lý focus trap, bàn phím và đóng phím Escape. |
| **Class Utilities** | **clsx**, **tailwind-merge** | Hợp nhất className động và giải quyết xung đột CSS classes linh hoạt. |
| **State & Authentication** | **React Context API** (`AuthContext`, `ToastContext`) | Quản lý Dual-Token Rotation (Access 30m / Refresh 30d), Mutex Promise Queue chống xung đột 401 concurrent refresh, exponential backoff retries. |
| **Routing** | **HTML5 History API Router** | Điều hướng SPA không tải lại trang (`/`, `/jobs`, `/market`, `/recommendations`, `/resume`, `/applications`, `/profile`, `/system`), đồng bộ URL hai chiều. |

#### Design System Tokens

`frontend/src/styles/themes.css` là nguồn token hiện hành; `src/theme/` và script pre-paint chọn `glass`/`glass-dark`, lưu lựa chọn `light`/`dark`. Typography dùng DM Sans/Manrope. Bảng màu Simple Blue và font Inter/JetBrains trong đặc tả trước đây là lịch sử, không phải token runtime. Một component tree phục vụ cả hai appearance.

---

### 2.2. Backend & Core Engine (FastAPI & Python)

Backend đóng vai trò trung tâm điều phối dữ liệu, thuật toán tất định và an toàn hệ thống:

| Thành phần | Công nghệ / Thư viện | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Runtime & Language** | **Python 3.11** | Hiệu năng xử lý async I/O và hỗ trợ type annotations mạnh mẽ. |
| **Web Framework** | **FastAPI** | Framework bất đồng bộ chuẩn ASGI, tích hợp sẵn Swagger/OpenAPI docs và validation tự động. |
| **ASGI Web Server** | **Uvicorn** | Máy chủ HTTP bất đồng bộ chuẩn ASGI phục vụ production. |
| **Validation & Schema** | **Pydantic v2** | Kiểm định tính hợp lệ của dữ liệu đầu vào/ra (DTO), serialization tốc độ cao viết bằng Rust. |
| **Database ORM** | **SQLAlchemy 2.0 (Async)** | Ánh xạ đối tượng dữ liệu với cơ chế bất đồng bộ `AsyncSession`, hỗ trợ connection pooling. |
| **Database Migrations** | **Alembic** | Quản lý lịch sử và áp dụng các thay đổi cấu trúc bảng cơ sở dữ liệu. |
| **Database Driver** | **asyncpg** | Trình điều khiển kết nối PostgreSQL bất đồng bộ có tốc độ hàng đầu trong hệ sinh thái Python. |
| **Vector Storage** | **pgvector** | Extension lưu trữ và truy vấn tương đồng cosine/L2 trên vector embeddings trực tiếp trong PostgreSQL. |
| **In-Memory Cache & Queue**| **Redis 7** (`redis-py`) | Bộ đệm lưu trữ phiên làm việc, rate-limiting, và hàng đợi tác vụ cho workers. |
| **Fuzzy Matching** | **RapidFuzz** | Thuật toán so khớp chuỗi nhanh phục vụ tầng khử trùng lặp L2. |
| **Web Scraping & Ingestion**| **httpx**, **BeautifulSoup4**, **lxml** | Thu thập dữ liệu việc làm từ đa nguồn (ITViec, TopCV, Saramin, VietnamWorks, CareerLink, ITNavi, GrowUpWork, Remotive, Upwork, Mock; TopDev chỉ còn dữ liệu lịch sử/migration). |
| **PDF Compilation** | **TeXLive Minimal (`pdflatex`)** | Trình biên dịch mã nguồn LaTeX thành file PDF 1 trang A4 chuẩn ATS trực tiếp trong container. |
| **Bảo mật & Mã hóa** | **Argon2id**, **PBKDF2-HMAC-SHA256**, **python-jose** | Băm mật khẩu an toàn chuẩn NIST, ký và giải mã JWT Token (Access & Refresh). |

---

### 2.3. AI Intelligence & Pipeline Khử Ảo Giác (Anti-Hallucination)

| Khối chức năng | Thuật toán / Công nghệ | Vai trò & Đặc điểm |
| :--- | :--- | :--- |
| **Generative AI** | **Google Gemini REST API** (`GEMINI_MODEL`, mặc định `gemini-flash-latest`; cascade trong `gemini_resume_writer.py`, chi tiết `AI_SYSTEM.MD`) | Trích xuất thông tin JD và viết bản thảo CV với chế độ Structured JSON Mode. |
| **Matching Algorithm** | **7-Signal Deterministic Engine** | Thuật toán chấm điểm mức độ tương thích tất định (tổng trọng số = 1.0) kết hợp Hard Filters tri-state (`ELIGIBLE`, `UNCERTAIN`, `BLOCKED`). |
| **Anti-Hallucination** | **Claim-Level Validator (6 tầng)** | Kiểm định từng claim của CV với đồ thị dữ kiện (`FactGraph`), cấm hoàn toàn bịa đặt số liệu hay kỹ năng ngoài hồ sơ. |
| **Unit Regeneration** | **UnitRegenerationOrchestrator** | Cơ chế tái tạo lại từng bullet point bị lỗi mà vẫn giữ nguyên các phần hợp lệ. |
| **Deduplication Engine** | **3-Tier Deduplication Pipeline** | L1: SHA-256 Signature $\rightarrow$ L2: RapidFuzz $\rightarrow$ L3: pgvector Cosine similarity. |

---

### 2.4. Discord Bot Adapter

| Thành phần | Công nghệ / Thư viện | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Runtime** | **Node.js 20 LTS** | Môi trường thực thi JavaScript/TypeScript cho bot. |
| **Framework** | **Discord.js v14** | Thư viện giao tiếp Discord Gateway API, hỗ trợ Interaction và Slash Commands. |
| **TypeScript Engine** | **tsx** (watch mode) | Thực thi TypeScript không cần biên dịch trước trong quá trình phát triển. |
| **Vai trò kiến trúc** | **Adapter mỏng (Thin Adapter)** | Chuyển tiếp tương tác người dùng về REST API Backend, không chứa business logic hay trạng thái độc lập. |

---

### 2.5. DevOps, Hạ Tầng & Containerization

| Công cụ | Cấu hình | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Container Engine** | **Docker Engine & Docker Compose v2** | `postgres`, `redis`, `backend`, `workers`, `discord-bot` và one-shot `frontend-build` (Node 22, `npm ci && npm run build`) trước backend. |
| **Base Images** | `python:3.11-slim`, `node:20-alpine` (bot), `node:22-alpine` (frontend build), `redis:7-alpine`, `pgvector/pgvector:pg16` | Tối ưu hóa kích thước image, giảm thiểu attack surface bảo mật. |
| **Container user** | Kiểm tra Dockerfile và Compose riêng | Compose backend/workers hiện override `user: root`; không khẳng định non-root hay sandbox isolation trong cấu hình local. |
| **Health Checks** | Docker Native Healthchecks | Đảm bảo Postgres và Redis hoàn toàn sẵn sàng trước khi Backend và Workers khởi động (`condition: service_healthy`). |
| **Serving Static Assets** | FastAPI StaticFiles Integration | Chỉ phục vụ bundle `frontend/dist/` đã build, không fallback về Vite source/legacy. Rebuild: `docker compose run --rm frontend-build`, sau đó `docker compose restart backend`. |

---

## 3. Ma Trận Tương Thích & Giao Tiếp (Compatibility Matrix)

```
[Web Browser] ──── (HTTP/5173 - Dev hoặc HTTP/8000 - Docker) ────► [FastAPI Backend]
                                                                        │
[Discord User] ─── (WebSocket) ───► [Discord Bot] ─── (HTTP) ───────────┤
                                                                        ▼
                                                             [PostgreSQL + Redis]
                                                                        ▲
                                                                        │
                                   [Background Workers] ────────────────┘
```
