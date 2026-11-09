# Saramin Adapter (`SaraminJobCollector`) — thay thế TopDev

Tên file tài liệu được giữ để bảo toàn liên kết cũ. `topdev_adapter.py` không còn là collector hiện hành.

- **Tệp nguồn:** `backend/app/services/collectors/saramin_adapter.py`
- **Source:** `saramin`
- **API:** `GET https://api.saramin.vn/td/v2/jobs`, `job_categories_ids=1`, `page_size=20`.
- **Giới hạn:** mặc định 50 records; `limit <= 0` không chặn số records, nhưng tối đa 200 trang. Dừng khi data rỗng, không có ID hợp lệ mới, hoặc tới `meta.last_page`; nghỉ 0.35s giữa trang, timeout client 20s.

## Validation và parsing

Chỉ nhận ID nguyên dương (không bool), title/company không rỗng và URL HTTPS trên `saramin.vn`/`www.saramin.vn`, cổng mặc định/443, không credentials, path `/detail-jobs/` hoặc `/viec-lam/`. HTTP lỗi và data/pagination sai cấu trúc được raise, không đổi thành thành công rỗng.

Hash tính từ toàn JSON item; khử trùng theo ID trong lượt fetch. `parse_raw()` làm sạch HTML description, dùng title nếu thiếu JD; nhận skills string từ `skills_arr`, địa điểm từ `addresses.address_region_list`. Lương masked/negotiable không được thay bằng ước lượng hoặc 0; chỉ nhận số hữu hạn >0. Published datetime/date định dạng ngày-tháng-năm theo UTC+7; `posted_iso` từ enrichment ưu tiên hơn. Không còn heuristic remote/hybrid của TopDev cũ.

Chỉ status `expired`, `closed`, `hết hạn`, `đã đóng`, `đã hết hạn` hoặc `expired_at` quá hạn là evidence expired; status lạ không tự coi là expired. `expired_at` được xử lý nếu API trả về, không nằm trong danh sách fields yêu cầu hiện tại. Detail enrichment hỗ trợ source `saramin` theo budget chung.

## Dữ liệu lịch sử và giới hạn bằng chứng

Migration `009_rename_topdev_saramin` đổi source trong `raw_jobs` từ TopDev sang Saramin, giữ URL/payload lịch sử; không khẳng định chúng là dữ liệu vừa fetch từ API mới. Xung đột ID làm migration fail thay vì tự merge/xóa.

Probe được ghi nhận ngày 2026-11-09: 96 ID unique dù metadata báo total319; các trang sau lặp ID. Đây là quan sát lịch sử, không phải cam kết coverage hiện tại. Pagination metadata và chế độ full scan không bảo đảm thu đủ mọi tin của upstream. Không bypass access restriction.
