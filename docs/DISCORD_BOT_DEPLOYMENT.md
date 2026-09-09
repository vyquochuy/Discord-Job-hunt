# Hướng dẫn Khởi chạy & Triển khai Discord Bot (24/7 Deployment Guide)

Tài liệu này hướng dẫn chi tiết quy trình thiết lập, cấu hình và triển khai **AI Job Hunter Discord Bot** hoạt động 24/7 hoặc chạy thử nghiệm cục bộ (Local).

---

## 1. Chuẩn bị Token từ Discord Developer Portal

1. Truy cập [Discord Developer Portal](https://discord.com/developers/applications).
2. Nhấn **New Application** và đặt tên cho Bot (ví dụ: `AI Job Hunter`).
3. Đi tới mục **Bot** trong menu bên trái:
   - Nhấn **Reset Token** để lấy `DISCORD_TOKEN`. Lưu token này an toàn.
   - Bật các mục trong **Privileged Gateway Intents**:
     - ✅ **Message Content Intent**
     - ✅ **Server Members Intent**
4. Đi tới mục **OAuth2** -> **General**:
   - Sao chép **Application ID** (đây chính là `DISCORD_CLIENT_ID`).
5. Đi tới **OAuth2** -> **URL Generator**:
   - Chọn Scopes: `bot`, `applications.commands`.
   - Chọn Bot Permissions: `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`, `Use Slash Commands`.
   - Sao chép liên kết được tạo và mở trên trình duyệt để mời Bot vào Server Discord của bạn.
6. Lấy ID Server & User ID của bạn:
   - Trong Discord, bật **User Settings -> Advanced -> Developer Mode**.
   - Chuột phải vào tên Server của bạn -> Chọn **Copy Server ID** (`DISCORD_GUILD_ID`).
   - Chuột phải vào tài khoản Discord của bạn -> Chọn **Copy User ID** (`ALLOWED_USER_ID`).

---

## 2. Cấu hình biến môi trường (`.env`)

Mở tệp `.env` ở thư mục gốc của dự án hoặc trong thư mục `discord-bot/` và điền:

```bash
# ------------------------------------------------------------------------------
# Cấu hình Discord Bot
# ------------------------------------------------------------------------------
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_CLIENT_ID=your_client_id_here
DISCORD_GUILD_ID=your_guild_id_here
ALLOWED_USER_ID=your_discord_user_id_here

# Địa chỉ API của Backend (mặc định nếu chạy local)
BACKEND_API_URL=http://localhost:8000
INTERNAL_API_SECRET=your_32_chars_random_secret_matching_backend
```

---

## 3. Khởi chạy Bot

### Cách 1: Chạy Local trực tiếp bằng Node.js / tsx (Khuyên dùng khi dev)

```bash
# Di chuyển vào thư mục bot
cd discord-bot

# Cài đặt thư viện
npm install

# Khởi chạy chế độ dev (tự động đồng bộ Slash Commands và reload khi sửa code)
npm run dev

# Hoặc biên dịch sang JavaScript và chạy bản production
npm run build
npm start
```

### Cách 2: Khởi chạy bằng Docker Compose (Cùng hệ sinh thái Backend)

Tại thư mục gốc dự án:

```bash
# Khởi động dịch vụ bot trong docker
docker compose up -d discord-bot

# Xem nhật ký hoạt động của bot
docker compose logs -f discord-bot
```

---

## 4. Triển khai 24/7 Miễn phí (0 VNĐ)

Do Discord Bot kết nối qua WebSocket Gateway liên tục (không phải HTTP request-response thông thường), các nền tảng serverless ngủ đông như Render Free Web Service sẽ làm ngắt kết nối WebSocket sau 15 phút. Dưới đây là các giải pháp 24/7 hoàn toàn miễn phí:

### Lựa chọn A: Hugging Face Spaces (Docker Space - Khuyên dùng)
- **Ưu điểm**: 100% miễn phí, chạy liên tục 24/7, không bao giờ ngủ đông (always-on container).
- **Cách làm**:
  1. Tạo Space mới trên [Hugging Face](https://huggingface.co/spaces) -> Chọn **Docker**.
  2. Đẩy thư mục `discord-bot` lên kho lưu trữ Git của Space:
     ```dockerfile
     # Dockerfile đã có sẵn trong thư mục discord-bot/
     FROM node:20-alpine
     WORKDIR /app
     COPY package*.json ./
     RUN npm install
     COPY . .
     RUN npm run build
     CMD ["npm", "start"]
     ```
  3. Vào tab **Settings** của Space -> **Variables and secrets** -> Thêm các biến `DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, `ALLOWED_USER_ID`, `BACKEND_API_URL` (URL backend Render của bạn), `INTERNAL_API_SECRET`.
  4. Space sẽ build và giữ bot online 24/7.

### Lựa chọn B: Discloud (Nền tảng chuyên dụng cho Discord Bot)
- **Ưu điểm**: Chuyên biệt cho discord.js / Node.js bot, hỗ trợ free tier.
- **Cách làm**:
  1. Đăng ký tài khoản trên [Discloud](https://discloudbot.com).
  2. Tạo tệp `discloud.config` trong `discord-bot/`:
     ```ini
     NAME=JobHunterBot
     AVATAR=https://i.imgur.com/example.png
     TYPE=bot
     MAIN=dist/index.js
     RAM=100
     AUTORESTART=false
     VERSION=latest
     APT=tools
     ```
  3. Nén mã nguồn `dist/`, `package.json` và tải lên bảng điều khiển Discloud.

---

## 5. Danh sách các Slash Commands khả dụng

Khi bot khởi động thành công và báo:
`🤖 Discord Bot đã đăng nhập thành công dưới tên: ...`
`✅ Đã đăng ký thành công 10 Slash Command cho Server (...)`

Bạn có thể gõ các lệnh sau trong Discord:

| Lệnh | Mô tả chức năng |
| :--- | :--- |
| `/ping` | Kiểm tra độ trễ (latency) kết nối giữa Discord Gateway và Backend API. |
| `/profile view` | Xem thẻ hồ sơ ứng viên, danh sách kỹ năng chuẩn hóa và dự án tiêu biểu. |
| `/profile sync` | Đồng bộ hồ sơ từ context file (`context/candidate_profile.md`). |
| `/jobs` | Tìm kiếm và xem danh sách việc làm IT mới nhất kèm bộ lọc trình độ, địa điểm. |
| `/job <id>` | Xem chi tiết tin tuyển dụng, yêu cầu công nghệ và nút mở liên kết gốc. |
| `/match <id>` | Phân tích độ khớp 7 chỉ số tất định giữa hồ sơ và JD, chỉ ra điểm mạnh & thiếu hụt. |
| `/recommend` | Nhận bảng xếp hạng các công việc phù hợp nhất theo điểm số Match Score. |
| `/collect [source] [limit]` | Kích hoạt quét cào tin tự động từ CareerLink, TopDev, ITNavi hoặc Mock. |
| `/resume <job_id>` | Tự động thiết kế CV chuẩn ATS bằng LaTeX và Cover Letter, gửi trực tiếp file PDF vào channel. |
| `/import url <link>` | Nạp và phân tích nhanh tin tuyển dụng từ link bất kỳ ngoài hệ thống. |
