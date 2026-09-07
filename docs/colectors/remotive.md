# Remotive Adapter (`RemotiveJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/remotive_adapter.py`
- **Tên nguồn (`source_name`):** `remotive`
- **Phương thức thu thập:** HTTP GET (Public REST API)

---

## 1. Cơ Chế Thu Thập (Public API)

Remotive cung cấp API chính thức phục vụ việc làm Remote quốc tế, không yêu cầu API key:

- **API Endpoint:** `https://remotive.com/api/remote-jobs`
- **Danh mục quét (Categories):**
  - `software-dev` (Lập trình phần mềm)
  - `devops-sysadmin` (Hạ tầng, Cloud & DevOps)
- **Tham số Query:** `?category={cat}&limit={limit}`
- **User-Agent:**
  ```
  JobHunterBot/1.0 (https://github.com/vyquochuy/Discord-Job-hunt; job-matching-bot)
  ```

## 2. Cấu Trúc Dữ Liệu & Bóc Tách

Dữ liệu trả về dạng JSON chuẩn:
- **Mã tin (`id`):** Dùng trực tiếp làm `source_job_id` và khử trùng lặp qua tập `seen_ids`.
- **Tiêu đề (`title`):** Tên vị trí tuyển dụng.
- **Tên công ty (`company_name`):** Tên doanh nghiệp tuyển dụng Remote.
- **Đường dẫn (`url`):** Link bài đăng trực tiếp hoặc `https://remotive.com/job/{id}`.
- **Địa điểm (`candidate_required_location`):** Mặc định `"Worldwide"` nếu không yêu cầu khu vực cụ thể.
- **Hình thức làm việc (`work_mode`):** Mặc định 100% `WorkModeEnum.REMOTE`.
- **Ngày đăng (`publication_date`):** Phân tích định dạng ISO 8601 sang `datetime` UTC.
- **Thẻ kỹ năng (`tags`):** Mảng các từ khóa kỹ thuật (ví dụ `["python", "docker", "aws"]`).
- **Nội dung mô tả (`description`):** Được làm sạch các thẻ HTML bằng `BeautifulSoup`.
