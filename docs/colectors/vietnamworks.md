# VietnamWorks Adapter (`VietnamWorksJobCollector`)

- **Tệp nguồn:** `backend/app/services/collectors/vietnamworks_adapter.py`
- **Tên nguồn (`source_name`):** `vietnamworks`
- **Phương thức thu thập:** HTTP POST (Internal REST API) + HTML Fallback

---

## 1. Cơ Chế Thu Thập (REST API Ingestion)

Không dùng web scraping HTML thông thường, VietnamWorks Collector khai thác trực tiếp Search API nội bộ của Navigos Group để lấy dữ liệu cấu trúc; không bảo đảm API luôn khả dụng hoặc dữ liệu hoàn chỉnh:

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
    "hitsPerPage": 50,
    "page": 0
}
```

`limit <= 0`: tối đa 80 trang; positive limit: `ceil(limit/50)` trang. Dừng khi trang rỗng/ngắn, đủ limit hoặc 20 expired records liên tiếp. API lỗi có nhánh HTML fallback; không đồng nghĩa bảo đảm đủ dữ liệu hoặc phân loại mọi access restriction.

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

- Chọn description dài nhất từ payload description (có thể đã enrich), `jobDescription`/detail và raw HTML rồi làm sạch. `expiredDate` epoch-ms map expiry; `approvedOn` map posted date. Tin expired được giữ để pipeline lưu lịch sử.
- Tự động nhận diện `REMOTE` hoặc `HYBRID` nếu xuất hiện trong tiêu đề.
- Chuyển tiếp vào Ingestion Pipeline.
