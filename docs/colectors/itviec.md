# ITViec Adapter (`ITViecJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/itviec_adapter.py`
- **Tên nguồn (`source_name`):** `itviec`
- **Phương thức thu thập:** HTTP GET (HTML Scraping)

---

## 1. Cơ Chế Thu Thập & Phân Trang

- **Base URL:** `https://itviec.com`
- **Search URL:** `https://itviec.com/it-jobs`
- **Phân trang:** Duyệt vòng lặp đa trang qua query parameter `?page={page}`:
  - Trang 1: `https://itviec.com/it-jobs`
  - Trang 2+: `https://itviec.com/it-jobs?page={page}`
  - `limit <= 0`: tối đa 80 trang; positive limit: `max(1, (limit + 19) // 20)`. Dừng khi đủ limit/không card hoặc 15 expired cards liên tiếp; không bảo đảm coverage toàn nguồn.
- **Khoảng nghỉ giữa các trang:** `await asyncio.sleep(0.35)`; không bảo đảm tránh rate limit.

## 2. HTTP Headers

Sử dụng header giả lập trình duyệt:
```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
}
```

## 3. DOM Selectors & Bóc Tách

| Trường dữ liệu | Bộ chọn CSS chính & Dự phòng (Fallback) |
| :--- | :--- |
| **Job Card** | `.job-card`, `.job_content`, `div[data-search--job-selection-target='jobCard']` (Fallback: `div[class*='job']`) |
| **Tiêu đề** | `h3 a`, `.job-card__title a`, `a[href*='/it-jobs/']` |
| **Đường dẫn (URL)** | Lấy `href` từ tiêu đề, chuẩn hóa tiền tố `https://itviec.com` nếu là link tương đối |
| **Công ty** | `div.imy-3`, `a[href*='/companies/']`, `span.text-hover-underline`, `.job-card__company-name` |
| **Địa điểm** | `div.text-rich-grey.text-truncate`, `.job-card__location`, `.city`, `.address` (mặc định: "Vietnam") |
| **Kỹ năng (Tags)** | `a.itag`, `.job-card__skills a`, `.tag-list a` (đặc trưng của ITViec là class `.itag`) |
| **Mức lương** | `.job-card__salary`, `.salary` |
| **Job ID** | Bóc tách phần đuôi URL sau dấu `/` cuối cùng |

## 4. Xử Lý Dữ Liệu & Pipeline

- **Content Hash:** SHA-256 từ `title|company|location|url`, nối thêm `|posted_at_text` khi có text ngày đăng.
- **`parse_raw()`:** Ưu tiên payload description từ enrichment, rồi card HTML, rồi title/company. Posted ưu tiên `posted_iso` → relative `posted_at_text` → UTC now; expiry từ `expires_iso`. Gán `work_mode = ONSITE`, `level = UNKNOWN` để pipeline chuẩn hóa tiếp.
- Non-200 dừng fetch; exception được log và trả phần đã fetch, không có cam kết BLOCKED reporting riêng như TopCV.
