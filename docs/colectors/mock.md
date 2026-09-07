# Mock Adapter (`MockJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/mock_adapter.py`
- **Tên nguồn (`source_name`):** `mock`
- **Phương thức thu thập:** In-Memory Test Fixtures / Offline Simulation

---

## 1. Mục Đích & Phạm Vi Sử Dụng

`MockJobCollector` là adapter giả lập được thiết kế chuyên biệt phục vụ:
- **Kiểm thử tự động (Automated Pytest Suite):** Cung cấp dữ liệu đầu vào ổn định, có thể dự đoán trước 100% cho các test case của Ingestion Pipeline, Deduplication và Match Engine.
- **Phát triển Offline (Local Development):** Lập trình viên có thể khởi chạy và thử nghiệm toàn bộ hệ thống (Web UI, Matching, Tailoring) khi không có kết nối Internet hoặc khi các cổng thông tin việc làm đang bảo trì.
- **Không gây tải mạng:** 0 network requests, 0 API calls, 0 token costs.

## 2. Dữ Liệu Giả Lập & Đa Dạng Hóa

Bộ dữ liệu giả lập bao gồm 20+ tin tuyển dụng thực tế mô phỏng từ nhiều nguồn khác nhau:
- **Các vị trí:** Senior Python Backend, Junior Frontend React, DevOps/SRE Remote, Mobile Flutter, Java Enterprise, Data Engineer, QA Automation.
- **Mức lương & Tiền tệ:** Mô phỏng cả USD ($800 - $3,500) và VND (15M - 60M).
- **Hình thức làm việc:** Đầy đủ các trường hợp `ONSITE`, `HYBRID`, và `REMOTE`.
- **Nguồn gốc mô phỏng:** Gán nhãn `source_url` giả lập của TopCV, ITViec, Remotive, CareerLink.

## 3. Hoạt Động Trong Pipeline

- Sinh `RawJobData` với `content_hash` tính toán chuẩn theo SHA-256 của từng đối tượng.
- Phương thức `parse_raw()` chuyển đổi trực tiếp sang `JobExtractedData` với độ chính xác cao về kỹ năng bắt buộc (`skills_required`) và kỹ năng ưu tiên (`skills_nice_to_have`).
