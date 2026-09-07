# Danh Mục Tài Liệu Thu Thập Dữ Liệu Tuyển Dụng (Collectors)

Thư mục này chứa tài liệu kỹ thuật chi tiết về cơ chế cào (scraping / ingestion) dữ liệu từ các cổng thông tin việc làm trong dự án AI Job Hunter Platform.

Tất cả các adapter đều tuân theo kiến trúc chung kế thừa từ lớp cơ sở [`BaseJobCollector`](backend/app/services/collectors/base.py) và nguyên tắc **Zero-LLM Cost Ingestion** (bóc tách cấu trúc 100% bằng giải thuật tất định, không tiêu tốn token AI).

---

## Danh Sách Chi Tiết Từng Adapter

| STT | Cổng Tuyển Dụng | Tệp Tài Liệu | Phương Thức | Đặc Điểm Kỹ Thuật Chính |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **TopCV** | [topcv.md](topcv.md) | HTML Scraping | Đa trang IT, Browser-like Headers, Fallback DOM selectors đa tầng |
| 2 | **ITViec** | [itviec.md](itviec.md) | HTML Scraping | Chuyên IT Việt Nam, bóc tách thẻ kỹ năng `.itag`, phân trang `?page=` |
| 3 | **TopDev** | [topdev.md](topdev.md) | HTML Scraping | Danh mục `it-jobs`, tự động nhận diện Remote/Hybrid qua tiêu đề |
| 4 | **VietnamWorks** | [vietnamworks.md](vietnamworks.md) | REST API + Fallback | Gọi Search API nội bộ Navigos Group (`ms.vietnamworks.com`) |
| 5 | **Remotive** | [remotive.md](remotive.md) | Public REST API | Việc làm Remote quốc tế (Software Dev, DevOps), JSON chuẩn |
| 6 | **Upwork** | [upwork.md](upwork.md) | RSS XML Feeds | RSS Feed việc làm Freelance/Contract quốc tế, không bị Cloudflare chặn |
| 7 | **CareerLink** | [careerlink.md](careerlink.md) | HTML Scraping | Quét Category 19 (CNTT - Phần mềm), phân trang đa trang |
| 8 | **ITNavi** | [itnavi.md](itnavi.md) | HTML Scraping | Việc làm IT, bóc tách `data-id` và từ khóa kỹ thuật |
| 9 | **GrowUpWork** | [growupwork.md](growupwork.md) | HTML + Curated Fallback | Thị trường Nhật Bản & Việt Nam, bóc tách BrSE và chứng chỉ N1-N3 |
| 10 | **Mock Source** | [mock.md](mock.md) | In-memory Fixtures | Dữ liệu giả lập 20+ tin phục vụ Unit Test và phát triển Offline |

---

## Luồng Tích Hợp Ingestion Pipeline Chung

Mỗi adapter sau khi thu thập sẽ đẩy dữ liệu qua [`JobIngestionPipeline`](backend/app/services/ingestion_pipeline.py):
1. **Kiểm tra Content Hash SHA-256:** Bỏ qua tin không đổi để tiết kiệm chi phí.
2. **Lưu dữ liệu gốc vào `raw_jobs`:** Source of Truth.
3. **Deterministic Parsing:** Chuyển đổi thành `JobExtractedData`.
4. **Quét kỹ năng bổ sung:** Dùng `skill_normalizer` quét thêm canonical skills từ text.
5. **Trích xuất thông tin liên hệ HR:** Email, apply URL.
6. **Chuẩn hóa thực thể:** Tiêu đề, công ty, địa điểm, cấp bậc, mức lương.
7. **Khử trùng lặp 3 tầng:** Exact Signature $\rightarrow$ Fuzzy RapidFuzz $\rightarrow$ Semantic pgvector.
8. **Vector Embedding:** Sinh vector đặc trưng và lưu vào PostgreSQL.
9. **Lưu bảng `jobs` & `job_skills`:** Kích hoạt sẵn sàng cho Matching Engine.
