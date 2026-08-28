# Hướng dẫn Triển khai Web Frontend lên Cloudflare Pages (Chi phí 0đ)

Tài liệu này hướng dẫn chi tiết quy trình đưa giao diện Web Frontend của hệ sinh thái **AI Job Hunter Platform** lên mạng phân phối toàn cầu **Cloudflare Pages** với chi phí hoàn toàn **0đ**, băng thông không giới hạn, hỗ trợ SSL tự động và tốc độ tải trang cao cấp (Edge CDN).

---

## 1. Tổng quan Kiến trúc Triển khai

```
+-------------------------------------------------------------+
|               Cloudflare Pages (Frontend 0đ)                |
|  - Global CDN & Anycast Edge Caching                        |
|  - SPA Routing Rule via `_redirects` (`/* /index.html 200`)  |
|  - HTTPS / SSL Certificate tự động                          |
|  - Dynamic API Resolver (`window.ENV` / `localStorage`)     |
+------------------------------+------------------------------+
                               |
                   REST API (HTTPS / JSON)
                               |
                               v
+-------------------------------------------------------------+
|           Cloud Backend API (FastAPI / 0đ)                  |
|  - Render.com / Koyeb / Hugging Face Spaces                 |
|  - CORS Middleware: allow_origins=["*"]                     |
|  - Database: Supabase PostgreSQL (pgvector)                 |
|  - Cache & Queue: Upstash Redis Serverless                  |
+-------------------------------------------------------------+
```

---

## 2. Chuẩn bị Trước khi Triển khai

1. **Tài khoản Cloudflare**: Đăng ký miễn phí tại [dash.cloudflare.com](https://dash.cloudflare.com).
2. **Kho lưu trữ GitHub / GitLab**: Đẩy mã nguồn dự án lên GitHub cá nhân (hoặc tổ chức).
3. **Địa chỉ Cloud Backend API**: URL máy chủ FastAPI đã triển khai (ví dụ: `https://job-hunter-api.onrender.com/api/v1`).

---

## 3. Các bước Triển khai qua Giao diện Cloudflare Dashboard

### Bước 1: Tạo Dự án Cloudflare Pages
1. Đăng nhập vào [Cloudflare Dashboard](https://dash.cloudflare.com).
2. Tại menu bên trái, chọn **Workers & Pages** $\rightarrow$ bấm **Create application** $\rightarrow$ chọn tab **Pages**.
3. Bấm **Connect to Git** và ủy quyền liên kết với tài khoản GitHub của bạn.
4. Chọn repository `Job-Hunt` (hoặc tên repo của bạn) và bấm **Begin setup**.

### Bước 2: Cấu hình Build Settings
Thiết lập các thông số chính xác như sau:
- **Project name**: `job-hunter` (hoặc tên tùy thích, sẽ tạo domain `https://job-hunter.pages.dev`).
- **Production branch**: `main` (hoặc nhánh chính của bạn).
- **Framework preset**: `None` (Dự án sử dụng Pure HTML5, CSS3 và Vanilla JS).
- **Build command**: _(Để trống)_.
- **Build output directory**: `frontend` (Thư mục chứa `index.html`, `css/`, `js/`, `_redirects`, `env.js`).

### Bước 3: Hoàn tất Triển khai (Deploy)
1. Bấm nút **Save and Deploy**.
2. Cloudflare Pages sẽ thu thập thư mục `frontend/`, kích hoạt SSL và xuất bản website toàn cầu trong khoảng 10–20 giây.
3. Truy cập địa chỉ web được cấp: `https://<your-project-name>.pages.dev`.

---

## 4. Cấu hình Kết nối Backend API

Có 3 cách linh hoạt để kết nối Frontend trên Cloudflare Pages với Cloud Backend:

### Cách 1: Cấu hình trực tiếp trên Giao diện Web (Khuyên dùng - Nhanh nhất)
1. Mở trang Web `https://<your-project-name>.pages.dev`.
2. Truy cập tab **Hệ thống & Cơ sở dữ liệu** (`/system`).
3. Tại thẻ **"Cấu hình Máy chủ Backend & Cloud API Endpoint"**, nhập URL Backend:
   ```
   https://job-hunter-api.onrender.com/api/v1
   ```
4. Bấm **Lưu Endpoint** $\rightarrow$ Bấm **Kiểm tra kết nối (Ping Health)** để xác nhận kết nối thành công.

### Cách 2: Cấu hình qua tệp `frontend/env.js` (Tĩnh trong Git)
Chỉnh sửa tệp `frontend/env.js` trước khi commit git:
```javascript
window.ENV = {
  API_URL: 'https://job-hunter-api.onrender.com/api/v1',
  ENVIRONMENT: 'production',
};
```

### Cách 3: Thẻ Meta trong `frontend/index.html`
Thêm thẻ meta vào phần `<head>`:
```html
<meta name="api-base" content="https://job-hunter-api.onrender.com/api/v1" />
```

---

## 5. Triển khai Nhanh bằng Wrangler CLI (Tùy chọn)

Nếu bạn muốn deploy trực tiếp từ dòng lệnh cục bộ mà không cần thông qua Git:

```powershell
# 1. Cài đặt Cloudflare Wrangler
npm install -g wrangler

# 2. Đăng nhập tài khoản Cloudflare
wrangler login

# 3. Deploy thư mục frontend trực tiếp
wrangler pages deploy frontend --project-name=job-hunter
```

---

## 6. Kiểm tra & Xử lý sự cố (Troubleshooting)

| Vấn đề | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| **Lỗi 404 khi F5 / Reload trang** | Thiếu file `_redirects` trên Cloudflare Pages | Đảm bảo file `frontend/_redirects` tồn tại với nội dung `/* /index.html 200`. |
| **Lỗi CORS (`Cross-Origin Request Blocked`)** | Backend chưa cho phép domain `*.pages.dev` | Kiểm tra middleware CORS trong `backend/app/main.py` (`allow_origins=["*"]`). |
| **Mất kết nối Backend khi mở trên điện thoại/máy khác** | Endpoint đang trỏ về `localhost` | Mở tab **Hệ thống & Dữ liệu** (`/system`) và nhập đúng Public URL Cloud Backend (HTTPS). |
| **Tệp tin PDF không mở được trong iframe** | Backend chặn frame hoặc CORS header PDF | Đảm bảo `API_URL` trả về đúng định dạng URL tuyệt đối từ `api.getResumePdfUrl()`. |
