# GrowUpWork Adapter (`GrowUpWorkJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/growupwork_adapter.py`
- **Tên nguồn (`source_name`):** `growupwork`
- **Phương thức thu thập:** HTTP GET (embedded public JSON, fallback DOM selectors)

---

## 1. Cơ Chế Thu Thập & Thị Trường Mục Tiêu

GrowUpWork là nền tảng việc làm chuyên biệt cho các doanh nghiệp Nhật Bản (Japan IT & Vietnam Offshoring), các vị trí BrSE (Kỹ sư cầu nối), IT Comtor và lập trình viên có năng lực Nhật ngữ (N1, N2, N3).

- **Base URL:** `https://growupwork.com`
- **Search URL:** `https://growupwork.com/tim-viec`
- **Phân trang:** `?page={page}`; `limit <= 0`: tối đa 80 trang; positive limit: `min(25, max(1, (limit + 19) // 20))`. Dừng khi không có record mới hoặc đạt `last_page` của embedded JSON.
- **Ngôn ngữ chấp nhận:** `Accept-Language: vi-VN,vi;q=0.9,ja;q=0.8,en-US;q=0.7`.

## 2. DOM Selectors & Bóc Tách

| Trường dữ liệu | Bộ chọn CSS |
| :--- | :--- |
| **Job Card** | `.job-item`, `.card-job`, `.job-card`, `div.box-job` |
| **Tiêu đề & URL** | `h3 a`, `h2 a`, `a[class*='title']`, `a[href*='/viec-lam/']` |
| **Công ty** | `.company-name`, `a[class*='company']`, `.company`, `.employer` |
| **Địa điểm** | `.job-location`, `.location`, `.address` (Hà Nội, Tokyo, TP.HCM, Đà Nẵng) |
| **Mức lương** | `.job-salary`, `.salary`, `.money` (thường theo dải USD hoặc JPY) |
| **Kỹ năng & Nhật ngữ** | `.job-tag`, `.tag`, `.skill`, `.language-tag` (bóc tách N1, N2, N3, BrSE) |
| **Job ID** | Bóc tách bằng Regex từ URL: `re.search(r"[-/](\d+)(?:\.html\|\?\|$)", url)` |

## 3. Embedded JSON và lỗi nguồn

Ưu tiên `search-job-component[:search_jobs]`, đọc categories từ `:all_job_categories` để dựng URL category/title/ID. Payload lấy company, location, salary và ghép `job_description`, `required_experience_and_skill`, `welfare`; release/finish date map sang posted/expiry. Hash theo JSON item, dedup theo ID. Bảng DOM ở trên chỉ là fallback nếu không có embedded data.

`parse_raw()` ưu tiên payload description đã làm sạch, rồi card HTML, cuối cùng title/company. Timeout client 10s/connect 5s; nghỉ 0.35s giữa trang. Non-200 dừng; exception được log và trả phần fetch được (có thể rỗng), không bảo đảm báo BLOCKED riêng.

**Không còn `_get_curated_fallback_jobs()` hay tạo việc làm synthetic khi nguồn lỗi/rỗng.** Các record lịch sử `growupwork-curated-*` không bị xóa nhưng bị loại khỏi Market analytics; việc này không phải bộ lọc xóa toàn hệ thống. Probe 800 records ngày 2026-11-09 chỉ là số fetch lịch sử, không phải tổng ACTIVE đã ingest hoặc coverage guarantee.
