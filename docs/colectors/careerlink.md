# CareerLink Adapter (`CareerLinkJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/careerlink_adapter.py`
- **Tên nguồn (`source_name`):** `careerlink`
- **Phương thức thu thập:** HTTP GET (HTML Scraping)

---

## 1. Cơ Chế Thu Thập & Phân Trang

- **Base URL:** `https://www.careerlink.vn`
- **Search URL (Chính thức ngành CNTT - Phần mềm / Category 19):** 
  `https://www.careerlink.vn/viec-lam/cntt-phan-mem/19`
- **URL thay thế theo từ khóa (Keyword Search Fallback):**
  `https://www.careerlink.vn/vieclam/tim-kiem-viec-lam?keyword=C%C3%B4ng+Ngh%E1%BB%87+Th%C3%B4ng+Tin`
- **Quy tắc phân trang:**
  - Trang 1: `https://www.careerlink.vn/viec-lam/cntt-phan-mem/19`
  - Trang 2+: `https://www.careerlink.vn/viec-lam/cntt-phan-mem/19?page={page}` (duyệt tối đa 25 trang hoặc khi đủ giới hạn `limit`).
  *(Lưu ý: Đối với URL tìm kiếm theo từ khóa thì phân trang sử dụng tham số `&page={page}`).*
- **Khoảng nghỉ giữa các trang:** `await asyncio.sleep(0.35)` để tránh kích hoạt cơ chế chống quét IP của hệ thống.

## 2. DOM Selectors & Bóc Tách

Tương tự cơ chế của TopCV/ITViec, CareerLink bóc tách trực tiếp từ cây DOM:

| Trường dữ liệu | Bộ chọn CSS |
| :--- | :--- |
| **Job Card** | `.job-item`, `.list-group-item.job-item`, `div.media` |
| **Tiêu đề & URL** | `a.job-link`, `a.clickable-outside`, `h2 a`, `h3 a` |
| **Công ty** | `a.job-company`, `.job-company`, `a[href*='/nha-tuyen-dung/']` |
| **Địa điểm** | `.job-location`, `div.list-with-comma`, `.mobile-disabled-link` |
| **Mức lương** | `.job-salary`, `span.text-primary` |
| **Vị trí / Kỹ năng** | `.job-position` |
| **Job ID** | Bóc tách bằng Regex: `re.search(r"/(\d+)(?:\?|$)", url)` |

## 3. Xử Lý Dữ Liệu

- **Content Hash:** SHA-256 từ `title|company|location|url`.
- **`parse_raw()`:** Bóc tách text mô tả từ card HTML, chuẩn hóa thành `JobExtractedData` với `work_mode = ONSITE`, `level = UNKNOWN`.
