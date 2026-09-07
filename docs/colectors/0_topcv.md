# Hướng Dẫn Kỹ Thuật: Cơ Chế Thu Thập Dữ Liệu Tuyển Dụng (Job Collector) - TopCV & Hệ Thống Nguồn

Tài liệu này mô tả chi tiết kiến trúc và phương thức cào (scraping / ingestion) dữ liệu tuyển dụng trong dự án AI Job Hunter Platform, lấy **TopCV (`TopCVJobCollector`)** làm trường hợp nghiên cứu chuyên sâu, đồng thời tổng hợp cơ chế thu thập của toàn bộ 10 nguồn tuyển dụng trong hệ thống.

---

## 1. Tổng Quan Kiến Trúc Thu Thập Dữ Liệu (Collector Architecture)

Trong hệ thống AI Job Hunter Platform, thu thập dữ liệu là bước đầu tiên trong đường ống tự động hóa (Pipeline). Dữ liệu sau khi thu thập được quản lý theo nguyên tắc:

- **Tách biệt tầng thu thập (Collector Layer) và tầng lưu trữ/chuẩn hóa (Ingestion & Normalization Layer)**.
- **Zero-LLM Cost Ingestion**: Toàn bộ quá trình quét, phân tích cấu trúc DOM và chuẩn hóa ban đầu được thực hiện 100% bằng giải thuật tất định (deterministic parsing & regex matching), không tiêu tốn token AI.
- **Raw Data làm Source of Truth**: Mọi tin tuyển dụng thu thập về đều lưu nguyên bản payload/HTML vào bảng `raw_jobs` trước khi biến đổi sang bảng `jobs`.

```
[ Trang web tuyển dụng ]
        │ (HTTP GET / POST / RSS)
        ▼
[ BaseJobCollector Adapters ] ──> RawJobData (SHA-256 Content Hash)
        │
        ▼
[ JobIngestionPipeline ]
   ├── 1. Kiểm tra Hash SHA-256 (Bỏ qua nếu tin không đổi -> 0 cost)
   ├── 2. Lưu vào database: raw_jobs
   ├── 3. Deterministic Parsing (JobExtractedData)
   ├── 4. Bóc tách Skill Taxonomy & HR Contact (Email/URL)
   ├── 5. Normalization (Title, Company, Salary, Work Mode, Level)
   ├── 6. Deduplication (Exact -> Fuzzy RapidFuzz -> Semantic pgvector)
   ├── 7. Vector Embedding (pgvector)
   └── 8. Lưu vào bảng jobs & liên kết job_skills
```

### Lớp trừu tượng nền tảng: `BaseJobCollector`

Tất cả các adapter thu thập dữ liệu trong dự án đều phải kế thừa từ lớp trừu tượng `BaseJobCollector` tại file:
`backend/app/services/collectors/base.py`

```python
class RawJobData(BaseModel):
    source: str                          # Tên nguồn: 'topcv', 'itviec', 'remotive', ...
    source_url: str                      # URL gốc của tin tuyển dụng
    source_job_id: Optional[str] = None  # Mã ID tin tuyển dụng trên trang nguồn (nếu có)
    raw_payload: Optional[Dict[str, Any]] = None # Dữ liệu cấu trúc bóc tách nhanh từ thẻ card
    raw_html: Optional[str] = None       # Đoạn HTML gốc của card/trang để truy vết
    content_hash: str                    # Mã SHA-256 hash của nội dung thực tế

class BaseJobCollector(abc.ABC):
    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Định danh nguồn."""
        pass

    @abc.abstractmethod
    async def fetch_jobs(self, limit: int = 20) -> List[RawJobData]:
        """Thu thập danh sách tin thô bất đồng bộ."""
        pass

    @abc.abstractmethod
    async def parse_raw(self, raw: RawJobData) -> JobExtractedData:
        """Chuyển đổi dữ liệu thô thành dữ liệu cấu trúc chuẩn."""
        pass

    @staticmethod
    def compute_content_hash(content: Any) -> str:
        """Băm SHA-256 xác định tính toàn vẹn và trùng lặp."""
```

---

## 2. Phân Tích Chuyên Sâu: Cơ Chế Cào Dữ Liệu TopCV (`TopCVJobCollector`)

File hiện thực: `backend/app/services/collectors/topcv_adapter.py`

TopCV là một trong những cổng việc làm lớn nhất tại Việt Nam. Trang web này sử dụng giải pháp hiển thị danh sách dạng Server-Side Rendered (SSR) kết hợp bảo vệ bot cơ bản (WAF, kiểm tra User-Agent và Fingerprint).

### 2.1. Cấu hình Endpoint Mục Tiêu & Phân Trang

Adapter cấu hình chuyên biệt để thu thập việc làm nhóm ngành Công nghệ thông tin / Phần mềm:

- **Base URL**: `https://www.topcv.vn`
- **Search URL**: `https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026`
- **Quy tắc phân trang**:
  - Trang đầu: `https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026`
  - Trang tiếp theo: `https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026?sort=new&page={page}`
  - Sắp xếp: Ưu tiên `sort=new` để luôn đón đầu các tin tuyển dụng mới nhất trong ngày.
- **Giới hạn số trang quét (Pagination Guard)**:
  ```python
  max_pages = min(25, max(1, (limit + 19) // 20))
  ```
  Hệ thống tính toán số trang cần quét dựa trên tham số `limit` (mặc định mỗi trang có khoảng 20-25 tin), tối đa không vượt quá 25 trang để tránh quá tải tài nguyên mạng.

### 2.2. Kỹ Thuật Giả Lập Trình Duyệt (Browser-like Headers) & Chống Rate Limit

Để giảm thiểu việc bị tường lửa WAF chặn hoặc trả về mã lỗi 403 Forbidden, `TopCVJobCollector` thiết lập cấu trúc HTTP Headers tương thích hoàn toàn với trình duyệt Chromium hiện đại:

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Upgrade-Insecure-Requests": "1",
}
```

**Chiến lược điều tiết tần suất (Rate Limiting Delay)**:

- Giữa mỗi chu kỳ tải trang (`page += 1`), adapter thực hiện chờ bất đồng bộ:
  ```python
  await asyncio.sleep(0.35)
  ```
  Độ trễ 350ms vừa đủ để không kích hoạt bộ đếm DoS của máy chủ đích, vừa tối ưu thời gian quét toàn bộ danh sách.

### 2.3. Bóc Tách Cấu Trúc DOM & Bộ Chọn CSS Đa Tầng (Fallback Selectors)

TopCV thường xuyên A/B testing giao diện hoặc thay đổi class CSS. Do đó, adapter áp dụng chiến lược **bộ chọn đa tầng (multi-selector fallback)** để đảm bảo không bị gãy crawler:

#### 1. Khung chứa tin (Job Card Container):

```python
job_cards = soup.select(
    ".job-item-search-result, .job-item-2, .job-item, .job-ta, div[data-job-id]"
)
```

Nếu trang không còn thẻ card nào phù hợp, vòng lặp tự động dừng lại (`break`).

#### 2. Tiêu đề công việc & Đường dẫn chi tiết:

- Bộ chọn:
  ```python
  title_elem = card.select_one("h3 a, .title a, a[href*='/viec-lam/'], span.bold a, a.job-title")
  ```
- Trích xuất linh hoạt:
  ```python
  title = (
      title_elem.get("title")
      or title_elem.get("data-original-title")
      or title_elem.get_text(strip=True)
      or (title_elem.select_one("span") and title_elem.select_one("span").get_text(strip=True))
      or ""
  )
  ```
- Chuẩn hóa URL:
  ```python
  rel_url = title_elem.get("href", "")
  url = rel_url if rel_url.startswith("http") else f"{self.BASE_URL}{rel_url}"
  ```

#### 3. Tên công ty tuyển dụng:

- Bộ chọn:
  ```python
  company_elem = card.select_one("a.company, .company-name, a[href*='/cong-ty/'], .name, span.company-name")
  company = company_elem.get_text(strip=True) if company_elem else "IT Company"
  ```

#### 4. Địa điểm làm việc:

- Bộ chọn:
  ```python
  location_elem = card.select_one(".address, .city, .location")
  location = location_elem.get_text(strip=True) if location_elem else "Vietnam"
  ```

#### 5. Mức lương:

- Bộ chọn:
  ```python
  salary_elem = card.select_one(".salary, .badge-salary")
  salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
  ```

#### 6. Thẻ kỹ năng / Công nghệ (Badges):

- Bộ chọn:
  ```python
  skill_badges = card.select(".tag, .badge, .job-tag")
  skills = [s.get_text(strip=True) for s in skill_badges if s.get_text(strip=True)]
  ```

#### 7. Trích xuất Source Job ID:

- Sử dụng biểu thức chính quy (Regex) bóc tách ID số nguyên từ URL bài đăng:
  ```python
  job_id_match = re.search(r"/(\d+)\.html", url)
  source_job_id = job_id_match.group(1) if job_id_match else None
  ```

### 2.4. Tính Toán SHA-256 Content Hash (Khử Trùng Lặp 0đ)

Trước khi đóng gói, adapter tạo một chuỗi băm đại diện cho trạng thái tin:

```python
content_hash = self.compute_content_hash(f"{title}|{company}|{location}|{url}")
```

Khi đẩy vào Ingestion Pipeline:

- Nếu chuỗi SHA-256 đã tồn tại trong bảng `raw_jobs`, hệ thống chỉ cập nhật timestamp `last_seen_at = now()` và lập tức chuyển sang tin kế tiếp.
- Giúp hệ thống không thực hiện các tác vụ thừa, không gọi mô hình AI và tiết kiệm 100% chi phí xử lý với các tin không có thay đổi nội dung.

### 2.5. Chuyển Đổi Sang Dữ Liệu Chuẩn: `parse_raw()`

Hàm `parse_raw()` nhận đối tượng `RawJobData` và trả về `JobExtractedData`:

1. Làm sạch văn bản HTML mô tả (`raw_html`) bằng `BeautifulSoup(raw.raw_html, "html.parser").get_text()`, loại bỏ khoảng trắng thừa.
2. Gán giá trị mặc định an toàn cho các trường chưa được suy luận:
   - `work_mode`: Mặc định `WorkModeEnum.ONSITE` (sẽ được chuẩn hóa tiếp ở bước Pipeline).
   - `level`: Mặc định `JobLevelEnum.UNKNOWN`.
   - `posted_at`: Mốc thời gian UTC hiện tại.
   - `skills_required`: Danh sách kỹ năng bóc tách từ badges.

---

## 3. Luồng Xử Lý Sau Khi Cào (Post-Ingestion Pipeline)

Toàn bộ các tin trả về từ `TopCVJobCollector` (cũng như các collector khác) đều đi qua quy trình chuẩn hóa và làm sạch trung tâm tại:
`backend/app/services/ingestion_pipeline.py`

Quy trình bao gồm 9 bước nghiêm ngặt:

1. **Hash Verification**: Truy vấn `raw_jobs` theo `content_hash`. Bỏ qua nếu tin không thay đổi.
2. **Raw Job Persistence**: Lưu hoặc cập nhật bản ghi vào `raw_jobs` (fetch_status = `FETCHED`).
3. **Deterministic Parsing**: Gọi `collector.parse_raw(raw_data)`.
4. **Deterministic Skill Scanning**: Gọi `skill_normalizer.extract_skills_from_text(description)` để quét bổ sung các kỹ năng công nghệ chuẩn (canonical taxonomy) xuất hiện trong mô tả mà giao diện web chưa gắn tag.
5. **Contact Extraction**: Trích xuất email HR tuyển dụng và link nộp đơn trực tiếp bằng Regex.
6. **Data Normalization**:
   - `job_normalizer.normalize_title()`: Làm sạch chức danh (loại bỏ ký tự đặc biệt, tag tuyển dụng thừa).
   - `job_normalizer.normalize_company()`: Chuẩn hóa tên doanh nghiệp.
   - `job_normalizer.normalize_location()`: Nhận diện tỉnh thành (Hà Nội, TP.HCM, Đà Nẵng, Remote...).
   - `job_normalizer.normalize_level()`: Suy luận cấp bậc (Intern, Fresher, Junior, Middle, Senior, Lead).
   - `job_normalizer.normalize_salary()`: Chuẩn hóa khoảng lương (Min, Max, Tiền tệ VND/USD).
7. **3-Tier Deduplication (Chống trùng lặp 3 lớp)**:
   - **Tầng 1 (Exact Signature)**: So khớp khóa chữ ký `dedup_signature` (băm từ tên công ty + chức danh + địa điểm).
   - **Tầng 2 (Fuzzy Matching)**: So khớp chuỗi mờ bằng thuật toán RapidFuzz (tỷ lệ tương đồng > 88%).
   - **Tầng 3 (Semantic pgvector)**: So khớp ngữ nghĩa không gian vector cosine distance.
8. **Vector Embedding**: Sinh vector đặc trưng ngữ nghĩa 768 chiều từ `title + company + requirements` và lưu vào PostgreSQL thông qua tiện ích mở rộng `pgvector`.
9. **Final Persistence**: Lưu bản ghi vào bảng `jobs` (trạng thái `ACTIVE`) và tạo quan hệ nhiều-nhiều với bảng `skills` qua bảng trung gian `job_skills`.

---

## 4. Bảng Đối Chiếu 10 Nguồn Thu Thập Dữ Liệu Trong Dự Án

Dự án hiện tích hợp 10 Source Adapters được đặt tại thư mục:
`backend/app/services/collectors/`

| STT | Nguồn (Source ID) | Tệp Adapter               | Giao thức / Phương thức thu thập     | Định dạng dữ liệu | Đặc điểm kỹ thuật nổi bật                                                                             |
| :-- | :---------------- | :------------------------ | :----------------------------------- | :---------------- | :---------------------------------------------------------------------------------------------------- |
| 1   | **TopCV**         | `topcv_adapter.py`        | HTTP GET (HTML Scraping)             | HTML / DOM        | Bóc tách đa trang chuyên mục IT, Multi-class selector fallback, Browser-like headers.                 |
| 2   | **ITViec**        | `itviec_adapter.py`       | HTTP GET (HTML Scraping)             | HTML / DOM        | Thu thập chuyên biệt việc làm IT Việt Nam, bóc tách thẻ kỹ năng `itag`, phân trang query `?page=`.    |
| 3   | **TopDev**        | `topdev_adapter.py`       | HTTP GET (HTML Scraping)             | HTML / DOM        | Quét chuyên mục `it-jobs`, bóc tách tag công nghệ, tự động phân loại Remote/Hybrid qua tiêu đề.       |
| 4   | **VietnamWorks**  | `vietnamworks_adapter.py` | HTTP POST (REST API) + HTML fallback | JSON API          | Gọi trực tiếp search API nội bộ `ms.vietnamworks.com`, bóc tách dải lương số nguyên chuẩn xác.        |
| 5   | **Remotive**      | `remotive_adapter.py`     | HTTP GET (REST API)                  | JSON API          | Public API quốc tế (`remotive.com/api/remote-jobs`), chuyên tin Remote (Software Dev, DevOps).        |
| 6   | **Upwork**        | `upwork_adapter.py`       | HTTP GET (RSS XML)                   | XML / RSS 2.0     | Thu thập tin Freelance/Contract quốc tế qua RSS Feed, chi phí 0đ, không bị Cloudflare chặn.           |
| 7   | **CareerLink**    | `careerlink_adapter.py`   | HTTP GET (HTML Scraping)             | HTML / DOM        | Quét Category 19 (IT - Phần mềm), phân trang đa trang, bóc tách chức danh và mức lương.               |
| 8   | **ITNavi**        | `itnavi_adapter.py`       | HTTP GET (HTML Scraping)             | HTML / DOM        | Thu thập việc làm IT, xử lý thuộc tính `data-id`, bóc tách kỹ năng công nghệ và địa điểm.             |
| 9   | **GrowUpWork**    | `growupwork_adapter.py`   | HTTP GET (HTML Scraping)             | HTML / DOM        | Việc làm IT thị trường Nhật Bản & Việt Nam, bóc tách yêu cầu chứng chỉ tiếng Nhật (N1, N2, N3, BrSE). |
| 10  | **Mock Source**   | `mock_adapter.py`         | Bộ nhớ / Test fixtures               | In-memory Object  | Phục vụ kiểm thử tự động (Unit Test / CI-CD) và chế độ phát triển offline không cần internet.         |

---

## 5. Cơ Chế Điều Phối Vận Hành Tự Động (Batch Runner & Scheduling)

Quá trình cào tin từ TopCV và các nguồn khác được vận hành theo 3 phương thức:

### 5.1. Chu kỳ tự động hàng ngày (Daily Autonomous Batch)

File: `backend/app/services/daily_runner.py`

- Được kích hoạt định kỳ 1 lần/ngày bởi scheduler hoặc background worker.
- Tự động duyệt qua danh sách tất cả các collector đang kích hoạt.
- Tự động lọc và chuyển trạng thái `EXPIRED` cho các tin cũ quá 30 ngày (trừ các tin đã được ứng viên lưu hoặc ứng tuyển).
- Chạy thuật toán chấm điểm phù hợp (Phase 3 Matching Engine) cho hồ sơ ứng viên đối với các tin mới cào được.

### 5.2. Chạy bất đồng bộ qua Background Worker

File: `backend/app/worker.py`

- Lắng nghe sự kiện từ hàng đợi Redis / ARQ task queue.
- Thực thi tác vụ cào dữ liệu chạy ngầm, không gây nghẽn REST API phục vụ người dùng.

### 5.3. Kích hoạt thủ công hoặc qua API

File: `backend/app/api/v1/endpoints/jobs.py`

- Endpoint: `POST /api/v1/jobs/collect` tiếp nhận tham số `source` và `limit` để kích hoạt cào tức thì một nguồn xác định.
- Endpoint: `POST /api/v1/jobs/ingest-manual` cho phép dán trực tiếp một liên kết tuyển dụng hoặc nội dung mô tả công việc thô để nạp vào hệ thống.

---

## 6. Hướng Dẫn Mở Rộng: Xây Dựng Collector Mới

Khi cần tích hợp thêm một trang web tuyển dụng mới vào dự án, cần tuân thủ các nguyên tắc sau:

1. **Kế thừa đúng chuẩn**: Tạo tệp `backend/app/services/collectors/{ten_nguon}_adapter.py` và kế thừa `BaseJobCollector`.
2. **Không code cứng đường dẫn**: Sử dụng cấu hình từ `app.core.config.settings` hoặc các URL tương đối. Tuyệt đối không code cứng đường dẫn tệp tuyệt đối của máy tính cá nhân.
3. **Bảo toàn tính toàn vẹn (Content Hash)**: Luôn tính `compute_content_hash()` từ các trường định danh bất biến (tiêu đề, công ty, địa điểm, URL).
4. **An toàn kết nối**:
   - Thiết lập `timeout` tối đa 10 - 15 giây cho mỗi HTTP client request.
   - Luôn sử dụng khối `try...except` bao quanh vòng lặp thu thập của từng trang để một trang lỗi không làm sập toàn bộ tiến trình.
   - Thêm khoảng nghỉ `asyncio.sleep(0.35)` giữa các trang yêu cầu.
5. **Đăng ký vào hệ thống**: Thêm lớp Collector mới vào danh sách `collectors` trong `backend/app/services/daily_runner.py` và danh mục kiểm thử tại `backend/tests/test_adapters.py`.
