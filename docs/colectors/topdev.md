# TopDev Adapter (`TopDevJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/topdev_adapter.py`
- **Tên nguồn (`source_name`):** `topdev`
- **Phương thức thu thập:** HTTP GET (HTML Scraping)

---

## 1. Cơ Chế Thu Thập & Phân Trang

- **Base URL:** `https://topdev.vn`
- **Search URL:** `https://topdev.vn/it-jobs`
- **Phân trang:** Query parameter `?page={page}` (tối đa 25 trang, dừng sớm khi đủ `limit`).
- **Khoảng nghỉ giữa các trang:** `await asyncio.sleep(0.35)`.
- **Client Timeout:** `httpx.Timeout(10.0, connect=5.0)`.

## 2. HTTP Headers

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://topdev.vn/",
}
```

## 3. DOM Selectors & Bóc Tách

| Trường dữ liệu | Bộ chọn CSS chính & Dự phòng (Fallback) |
| :--- | :--- |
| **Job Card** | `.job-item`, `.job-card`, `.job-item-info`, `div[data-job-id]`, `article.item` |
| **Tiêu đề** | `h3 a`, `.job-title a`, `a.title`, `a[href*='/detail-jobs/']`, `a[href*='/viec-lam/']` |
| **Đường dẫn (URL)** | Lấy `href`, tự động thêm tiền tố `https://topdev.vn` nếu là URL tương đối |
| **Công ty** | `.company-name`, `a.company`, `.employer-name`, `p.company` |
| **Địa điểm** | `.address`, `.location`, `.city`, `span.location` |
| **Mức lương** | `.salary`, `.text-salary`, `span.salary`, `.salary-text` |
| **Kỹ năng (Tags)** | `.tag`, `.skill-tag`, `.tag-item`, `a.tag`, `span.skill`, `.badge` |
| **Job ID** | Bóc tách bằng biểu thức chính quy: `re.search(r"[-/](\d+)(?:\.html\|\?\|$)", url)` |

## 4. Xử Lý Đặc Thù Trong `parse_raw()`

Khác với các adapter thông thường, TopDev hỗ trợ phát hiện sớm hình thức làm việc ngay tại bước phân tích tiêu đề:
- Nếu tiêu đề chứa từ khóa `"remote"` $\rightarrow$ `work_mode = WorkModeEnum.REMOTE`.
- Nếu tiêu đề chứa từ khóa `"hybrid"` $\rightarrow$ `work_mode = WorkModeEnum.HYBRID`.
- Mặc định: `WorkModeEnum.ONSITE`.
