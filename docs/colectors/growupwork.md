# GrowUpWork Adapter (`GrowUpWorkJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/growupwork_adapter.py`
- **Tên nguồn (`source_name`):** `growupwork`
- **Phương thức thu thập:** HTTP GET (HTML Scraping) + Curated Market Fallback

---

## 1. Cơ Chế Thu Thập & Thị Trường Mục Tiêu

GrowUpWork là nền tảng việc làm chuyên biệt cho các doanh nghiệp Nhật Bản (Japan IT & Vietnam Offshoring), các vị trí BrSE (Kỹ sư cầu nối), IT Comtor và lập trình viên có năng lực Nhật ngữ (N1, N2, N3).

- **Base URL:** `https://growupwork.com`
- **Search URL:** `https://growupwork.com/tim-viec`
- **Phân trang:** Query parameter `?page={page}` (tối đa 25 trang).
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

## 3. Cơ Chế Curated Fallback (Bảo Vệ Độ Sẵn Sàng Cao)

Nếu máy chủ GrowUpWork bảo trì hoặc trả về danh sách rỗng, adapter kích hoạt hàm `_get_curated_fallback_jobs()`:
- Nạp danh mục việc làm IT tiêu biểu thị trường Nhật Bản (BrSE Tokyo, Fullstack Developer N3, IT Comtor N1/N2, DevOps AWS).
- Đảm bảo hệ thống luôn có dữ liệu phong phú để đánh giá độ phù hợp với ứng viên có kỹ năng tiếng Nhật.
