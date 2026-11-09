# CareerLink Adapter (`CareerLinkJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/careerlink_adapter.py`
- **Tên nguồn (`source_name`):** `careerlink`
- **Phương thức thu thập:** HTTP GET (HTML Scraping)

---

## 1. Cơ Chế Thu Thập & Phân Trang

- **Base URL:** `https://www.careerlink.vn`
- **Search URL (Chính thức ngành CNTT - Phần mềm / Category 19):** 
  `https://www.careerlink.vn/viec-lam/cntt-phan-mem/19`
- Không có keyword-search URL fallback trong code hiện tại.
- **Quy tắc phân trang:**
  - Trang 1: category URL + `?sort=date`; trang 2+: `?sort=date&page={page}`.
  - `limit <= 0`: tối đa 80 trang; positive limit: `max(1, (limit + 19) // 20)`; dừng khi đủ limit/không card hoặc 15 expired cards liên tiếp ở nhánh DOM. Nhánh JSON-LD không áp dụng expired streak.
- **Khoảng nghỉ giữa các trang:** `await asyncio.sleep(0.35)`; không bảo đảm tránh rate limit.
- HTTP 401/403/407/429 hoặc marker `xác nhận bạn không phải robot` raise `RuntimeError` BLOCKED, không retry/bypass; non-200 khác dừng. Đây không phải detector mọi loại WAF.

## 2. DOM Selectors & Bóc Tách

Ưu tiên JSON-LD `mainEntity.ItemList.itemListElement` (title/URL, company/location placeholder). Nếu đã có items thì sang trang kế tiếp; chỉ fallback DOM khi không có items:

| Trường dữ liệu | Bộ chọn CSS |
| :--- | :--- |
| **Job Card** | `[data-testid='job-result-row']`, `.job-item`, `.list-group-item.job-item`, `li.tlp-job`, `div.media` |
| **Tiêu đề & URL** | `a[class*='__jobLink']`, `a.job-link`, `a.clickable-outside`, `h5.job-name`, `h2 a`, `h3 a` |
| **Công ty** | `a.job-company`, `.job-company`, `a[href*='/nha-tuyen-dung/']` |
| **Địa điểm** | `.job-location`, `div.list-with-comma`, `.mobile-disabled-link` |
| **Mức lương** | `.job-salary`, `span.text-primary` |
| **Vị trí / Kỹ năng** | `.job-position` |
| **Job ID** | Bóc tách bằng Regex: `re.search(r"/(\d+)(?:\?|$)", url)` |

## 3. Xử Lý Dữ Liệu

- **Content Hash:** DOM: SHA-256 từ `title|company|location|url`; JSON-LD: `title|url`.
- **`parse_raw()`:** Ưu tiên payload description từ detail enrichment, rồi card HTML; map posted/expiry, `work_mode = ONSITE`, `level = UNKNOWN`.
- Probe 415 records ngày 2026-11-09 là kết quả fetch lịch sử, không phải cam kết toàn nguồn hoặc số ACTIVE trong DB.
