# ITNavi Adapter (`ITNaviJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/itnavi_adapter.py`
- **Tên nguồn (`source_name`):** `itnavi`
- **Phương thức thu thập:** HTTP GET (HTML Scraping)

---

## 1. Cơ Chế Thu Thập & Phân Trang

- **Base URL:** `https://itnavi.com.vn`
- **Search URL:** `https://itnavi.com.vn/job`
- **Phân trang:** Query parameter `?page={page}` (tối đa 25 trang).
- **Khoảng nghỉ giữa các trang:** `await asyncio.sleep(0.35)`.
- **Client Timeout:** `httpx.Timeout(10.0, connect=5.0)`.

## 2. DOM Selectors & Bóc Tách

| Trường dữ liệu | Bộ chọn CSS |
| :--- | :--- |
| **Job Card** | `.jsl-item`, `.jsl_item`, `.job-item`, `.item-job`, `.card-job`, `.job-card` |
| **Tiêu đề** | `.jsl-item__name`, `h2`, `h3`, `a[class*='title']`, `a[href*='/job/']` |
| **Đường dẫn (URL)** | Ưu tiên lấy từ `a[href*='/job/']`, nếu không có sẽ dựng URL theo thuộc tính `data-id` hoặc `id` của thẻ card |
| **Công ty** | `.jsl-item__cpn`, `.company-name`, `a[class*='company']`, `.employer-name` |
| **Địa điểm** | `.jsl-item__location`, `.location`, `.address`, `span[class*='city']` |
| **Mức lương** | `.jsl-item__sm`, `.salary`, `span[class*='salary']`, `.text-salary`, `.price` |
| **Kỹ năng (Tags)** | `.tag`, `.skill-tag`, `.skill-item`, `span[class*='tag']`, `.jsl-item__tag` |
| **Job ID** | Lấy từ thuộc tính `data-id` của card hoặc Regex trích xuất ID số từ URL |

## 3. Đặc Điểm Trong `parse_raw()`

Tương tự TopDev, ITNavi adapter tự động quét từ khóa trong tiêu đề:
- Nếu chứa `"remote"` $\rightarrow$ `WorkModeEnum.REMOTE`.
- Nếu chứa `"hybrid"` $\rightarrow$ `WorkModeEnum.HYBRID`.
- Mặc định: `WorkModeEnum.ONSITE`.
