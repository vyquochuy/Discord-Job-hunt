# Upwork Adapter (`UpworkJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/upwork_adapter.py`
- **Tên nguồn (`source_name`):** `upwork`
- **Phương thức thu thập:** HTTP GET (RSS XML Feed)

---

## 1. Cơ Chế Thu Thập (Public RSS Feeds)

Adapter thử các RSS URL dưới đây mà không cần tài khoản; chúng có thể lỗi/bị Cloudflare chặn. Không có cam kết RSS luôn truy cập được và không bypass restriction:

- **RSS Feeds cấu hình sẵn:**
  1. Danh mục Phần mềm: `https://www.upwork.com/ab/feed/jobs/rss?category2_uid=531770282580668418&sort=recency`
  2. Từ khóa công nghệ: `https://www.upwork.com/ab/feed/jobs/rss?q=python+OR+golang+OR+fastapi+OR+react+OR+devops&sort=recency`
- **Accept Header:** `application/rss+xml, application/xml, text/xml, */*`.

## 2. Bóc Tách Cấu Trúc RSS XML & Metadata Regex

Adapter phân tích cú pháp thẻ `<item>` bằng `BeautifulSoup(response.text, "xml")`:
- `<title>`: Tiêu đề công việc Freelance / Contract.
- `<link>`: URL bài đăng trên Upwork.
- `<pubDate>`: Ngày đăng tin (chuyển đổi theo định dạng RFC 2822).
- `<description>`: Khối HTML chứa metadata chi tiết của dự án.

### Bóc tách Regex từ `<description>`:
- **Dải lương theo giờ:** `re.search(r"Hourly Range:\s*([^<\n]+)", raw_desc)` $\rightarrow$ Ví dụ: `"Hourly: $30.00-$60.00"`.
- **Ngân sách cố định:** `re.search(r"Budget:\s*([^<\n]+)", raw_desc)` $\rightarrow$ Ví dụ: `"Budget: $1,000"`.
- **Kỹ năng yêu cầu:** `re.search(r"Skills:\s*([^<\n]+)", raw_desc)` $\rightarrow$ Tách mảng kỹ năng bằng dấu phẩy.
- **Quốc gia khách hàng:** `re.search(r"Country:\s*([^<\n]+)", raw_desc)` $\rightarrow$ Mặc định `"Worldwide"`.

## 3. Synthetic fallback còn tồn tại

Nếu không fetch được record RSS nào, code hiện gọi `_get_curated_fallback_jobs(limit)` để tạo dữ liệu curated synthetic, không phải tin live đã xác minh. Không dùng số trả về đó làm bằng chứng nguồn khỏe/coverage. Đây là hành vi cũ còn tồn tại ở Upwork, **khác GrowUpWork đã bỏ fallback**. Upwork không thuộc Vietnam Market whitelist.

## 4. Đặc Điểm Trong `parse_raw()`

- **Hình thức làm việc (`work_mode`):** Mặc định 100% `WorkModeEnum.REMOTE`.
- **Cấp bậc (`level`):** Bóc tách các từ khóa `Expert`, `Intermediate`, `Entry Level` có trong mô tả bài đăng Upwork.
