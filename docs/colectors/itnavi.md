# ITNavi Adapter (`ITNaviJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/itnavi_adapter.py`
- **Tên nguồn (`source_name`):** `itnavi`
- **Phương thức thu thập:** HTTP GET (HTML Scraping)

---

## 1. Cơ Chế Thu Thập & Phân Trang

- **Base URL:** `https://itnavi.com.vn`
- **Search URL:** `https://itnavi.com.vn/job`
- **Phân trang:** `?page={page}`; `limit > 0`: `min(25, max(1, (limit + 9) // 10))` trang. `limit <= 0`: full scan tối đa **50 trang**, không phải 80; không cam kết số tin cố định.
- **Khoảng nghỉ giữa các trang:** `await asyncio.sleep(0.35)`.
- **Client Timeout:** `httpx.Timeout(10.0, connect=5.0)`.

Listing được fetch tuần tự; timeout listing retry một lần rồi dừng. Mỗi trang chạy `asyncio.gather` cho **tất cả card**, không semaphore/concurrency cap riêng; AJAX `/ajax/get-job-by-id/{id}` có timeout 5s, không retry riêng. AJAX bổ sung canonical slug, full content, salary min/max và skills. URL fallback: `data-copy` → link `/job-detail/` hoặc `/viec-lam-` → URL theo ID → search URL. Khử trùng theo ID và URL; dừng khi trang không thêm record mới. Non-200 dừng; lỗi ngoài cùng được log và trả phần đã fetch, **không bảo đảm báo BLOCKED như TopCV**.

Probe 2026-11-09 timeout sau 240s là quan sát lịch sử chưa giải quyết, không phải timeout toàn collector được code bảo đảm. Full scan không cam kết hoàn tất trong 240s hay bao phủ toàn nguồn.

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

Ưu tiên description từ AJAX; fallback card HTML rồi title/company. Pipeline không chạy detail enrichment chung cho ITNavi. Adapter tự động quét từ khóa trong tiêu đề:
- Nếu chứa `"remote"` $\rightarrow$ `WorkModeEnum.REMOTE`.
- Nếu chứa `"hybrid"` $\rightarrow$ `WorkModeEnum.HYBRID`.
- Mặc định: `WorkModeEnum.ONSITE`.
