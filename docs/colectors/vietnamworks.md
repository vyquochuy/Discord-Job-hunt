# VietnamWorks Adapter (`VietnamWorksJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/vietnamworks_adapter.py`
- **Tên nguồn (`source_name`):** `vietnamworks`
- **Phương thức thu thập:** HTTP POST (Internal REST API) + HTML Fallback

---

## 1. Cơ Chế Thu Thập (REST API Ingestion)

Không dùng web scraping HTML thông thường, VietnamWorks Collector khai thác trực tiếp Search API nội bộ của Navigos Group để đạt hiệu năng cao và độ chính xác tuyệt đối:

- **API Search URL:** `https://ms.vietnamworks.com/job-search/v1.0/search`
- **Base Web URL:** `https://www.vietnamworks.com`
- **HTTP Method:** `POST`
- **HTTP Headers:**
  ```json
  {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*",
      "Content-Type": "application/json"
  }
  ```

### JSON Request Payload
```json
{
    "userId": 0,
    "query": "IT Software",
    "filter": [],
    "ranges": [],
    "order": [],
    "hitsPerPage": 25,
    "page": 0
}
```

## 2. Bóc Tách Dữ Liệu Từ JSON Response

Dữ liệu được trích xuất trực tiếp từ các trường JSON trả về trong mảng `data`:
- **Tiêu đề (`jobTitle`):** Lấy trực tiếp từ field `jobTitle`.
- **Đường dẫn (`jobUrl`):** Chuẩn hóa thành `https://www.vietnamworks.com{jobUrl}`.
- **Tên công ty (`companyName`):** Trích xuất từ field `companyName`.
- **Địa điểm (`workingLocations`):** Duyệt mảng `workingLocations`, trích xuất `cityNameVI` hoặc `cityName`.
- **Dải lương (`salaryMin`, `salaryMax`, `salaryCurrency`):**
  - Nếu có giá trị số: Định dạng dạng `{salaryMin:,} - {salaryMax:,} {salaryCurrency}`.
  - Nếu không: Dùng trường hiển thị sẵn `prettySalary`.
- **Kỹ năng (`skills`):** Mảng đối tượng `[{skillName: "Java"}, ...]`.
- **Mô tả (`jobDescription`):** Bóc tách nội dung HTML gốc gửi kèm trong payload.
- **Source Job ID:** Bóc tách từ trường `jobId`.

## 3. Chuyển Đổi Trong `parse_raw()`

- Làm sạch văn bản HTML của trường `jobDescription` bằng `BeautifulSoup`.
- Tự động nhận diện `REMOTE` hoặc `HYBRID` nếu xuất hiện trong tiêu đề.
- Chuyển tiếp vào Ingestion Pipeline.
