# Upwork Adapter (`UpworkJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/upwork_adapter.py`
- **Tên nguồn (`source_name`):** `upwork`
- **Phương thức thu thập:** HTTP GET (RSS XML Feed)

---

## 1. Cơ Chế Thu Thập (Public RSS Feeds)

Upwork được cào thông qua các luồng RSS XML chính thức, giúp tránh 100% rào cản Cloudflare / Bot Detection mà không cần tài khoản:

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

## 3. Đặc Điểm Trong `parse_raw()`

- **Hình thức làm việc (`work_mode`):** Mặc định 100% `WorkModeEnum.REMOTE`.
- **Cấp bậc (`level`):** Bóc tách các từ khóa `Expert`, `Intermediate`, `Entry Level` có trong mô tả bài đăng Upwork.
