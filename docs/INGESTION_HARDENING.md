# Ingestion Hardening Report — Detail Enrichment & Full Unexpired Scanning (Phase 2.7 & 2.8)

> **Ngày hoàn thành:** 2026-11-04 (Phase 2.7) · 2026-11-04 (Phase 2.8)
> **Phạm vi:** Backend job ingestion pipeline — nâng cấp chất lượng JD thu thập từ các nguồn tuyển dụng Việt Nam.
> **Nguồn tham khảo kỹ thuật:** `SonPhatTranDeveloper/vietnam-it-job-trends` (pipeline nghiên cứu 7-step crawl → dedupe → fetch-details → filter → consolidate → LLM-extract → classify).

---

## 1. Vấn đề tồn tại trước đây

Pipeline ingest cũ của Job-Hunt chỉ thu thập **listing-level data** (thẻ card trang danh sách) rồi dùng chính HTML card đó làm description:

```text
Collector.fetch_jobs() → card HTML → parse_raw() → description  ← SAI LECH CHAT LUONG
```

Hệ quả:

| Triệu chứng | Ảnh hưởng |
| --- | --- |
| Description chỉ gồm vài dòng card (title/company/1-2 tags) | 7-signal scoring thiếu bằng chứng → điểm match không chính xác |
| Không có ngày đăng thật (`posted_at = now()`) | Stale detection / retention policy hoạt động sai |
| HTML card dính junk class CSS dễ vỡ khi platform đổi layout | Parser âm thầm đổ rác vào `jobs.description` |
| Không Có cơ chế phát hiện trang bị chặn (Cloudflare WAF, login gate) | Lỗi/403/readme page bị coi là JD hợp lệ |

---

## 2. Giải pháp triển khai — Detail Page Enrichment

### 2.1 Pipelinenew sau thay đổi

```text
Collector.fetch_jobs()             (listing: URL, title, company, location, salary, tags)
  → BƯỚC 2.5: detail_fetcher.fetch_detail()        (ENRICHMENT — mới)
       JSON-LD JobPosting (schema.org)
       → site-specific DOM selectors
       → generic largest-block heuristic
       → clean_text của URLFetcher
  → Quality Validation (challenge / login / insufficient content)
  → Richer-record merge vào raw_payload
  → BƯỚC 3: parse_raw() (adapter ưu tiên payload["description"])
  →Normalization → Dedup → Embedding → PostgreSQL
```

### 2.2 Thành phần mới: `backend/app/services/extraction/detail_fetcher.py`

| Hàm thành phần | Trách nhiệm |
| --- | --- |
| `JobDetailResult` | DTO kết quả (status OK/BLOCKED/INCOMPLETE/FAILED, description, posted_at, employment_type, experience_months, skills, method, attempts) |
| `JobDetailFetcher.fetch_detail()` | Điều phối retry (max 2, backoff 1.5s/3s), không retry HTTP terminal 401/403/407/429 |
| `_extract_description()` | JSON-LD → site DOM → largest-block → page_text (4 tầng dự phòng) |
| `_extract_jsonld_meta()` | Trích `datePosted`, `employmentType`, `monthsOfExperience`, `skills` từ schema.org JobPosting |
| `is_challenge_page()` | Detect Cloudflare/status-page markers → **BLOCKED, KHÔNG BYPASS** (Invariant 19) |
| `is_login_gate()` | Detect trang yêu cầu đăng nhập (title marker HOẶC body ngắn + marker → tránh false-positive) |
| `merge_detail_into_payload()` | Richer-record merge: description dài hơn thắng, skills UNION không mất dữ liệu, `posted_iso` tin cậy cao hơn |
| `note_detail_failure()` | Bookkeeping trạng thái failure vào `payload["detail_meta"]` (không phá listing data) |
| `parse_posted_datetime()` | Đa định dạng: ISO 8601 / epoch giây–mili-giây / relative VN-EN ("3 days ago", "5 ngày trước", "hôm qua") |
| `clean_html_to_text()` / `normalize_description()` | HTML→text sạch, gộp dòng trống |

### 2.3 Nguồn được enrichment (`SUPPORTED_SOURCES`)

```text
itviec ↦ JSON-LD JobPosting + .job-detail__content
topcv ↦ JSON-LD + .job-description + boilerplate filter (largest-block)
topdev ↦ JSON-LD + JD card (div.rounded-xl.border.p-4, marker "Mô tả/Yêu cầu")
vietnamworks ↦ JSON-LD + generic (API fetch jobId đã có sẵn trong URLFetcher)
careerlink ↦ generic selectors (article/main/[class*='job-description'])
```

Nguồn **không** được enrich (đã có JD đầy đủ hoặc không hữu ích): `remotive` (API trả full description), `upwork`, `itnavi`, `growupwork`, `mock`.

### 2.4 Cấu hình Settings mới (`backend/app/core/config.py`)

```python
DETAIL_FETCH_ENABLED: bool = True     # Tắt hoàn toàn enrichment nếu cần
DETAIL_FETCH_TIMEOUT: float = 10.0    # Per-detail fetch timeout
DETAIL_FETCH_MAX_ATTEMPTS: int = 2    # Retry lần, backoff 1.5s/3s
DETAIL_FETCH_MAX_PER_RUN: int = 20    # Trần (budget) mỗi nguồn / mỗi lần chạy
```

Tiêu chí skip 0-cost: listing description `>= 800` ký tự (VD: VietnamWorks Search API trả JD đầy đủ) → **không fetch detail** để tiết kiệm băng thông.

### 2.5 Thay đổi trong `ingestion_pipeline.py`

- `IngestionStats` bổ sung metrics: `details_enriched`, `details_failed`, `details_skipped` (tự động hiển thị trong `POST /api/v1/jobs/collect` report).
- Tham số mới `fetch_details: Optional[bool] = None` (None → đọc từ settings).
- BƯỚC 2.5 chèn ngay sau khi `RawJob` DB record flush, TRƯỚC `parse_raw()`:
  - Detail **thành công** → `raw_data.raw_payload` được merge, đồng bộ lại vào ORM record.
  - Detail **thất bại** → note failure vào `detail_meta`, pipeline tiếp tục với listing data (graceful degradation, không gián đoạn).
- `content_hash` listing-level giữ nguyên ý nghĩa (cache-hit chi phí 0 như cũ), hash chi tiết JD lưu tại `payload["detail_meta"]["description_hash"]`.
- Retry detail bị BLOCKED/FAIL được lên kế hoạch ở **chu kỳ cào tiếp theo** khi listing hash thay đổi — tránh spam retry cùng nguồn (Invariant 22: không auto-retry mutation).

### 2.6 Adapters cập nhật `parse_raw()`

| Adapter | Hành vi mới |
| --- | --- |
| `itviec_adapter` | Ưu tiên `payload["description"]`; capture `posted_at_text` từ card (`time`, `.small-text`) + có `posted_iso`;hapus content_hash cập nhật theo text này |
| `topcv_adapter` | Ưu tiên `payload["description"]` (via `clean_html_to_text`); fallback card; `posted_iso` |
| `topdev_adapter` | Như TopCV + giữ logic WorkModeEnum từ title |
| `vietnamworks_adapter` | Richer-record merge giữa payload description / detail / raw_html (`max(candidates, key=len)`) |

### 2.7 An ninh & tuân thủ Invariants

| Invariant | Trạng thái |
| --- | --- |
| 12 — External job data là untrusted | Detail chỉ là READ-ONLY GET; challenge/login KHÔNG bị bypass, đánh dấu Blocked và đề xuất fallback nhập tay |
| 19 — Không automation trái phép | Không webdriver/anti-detect/captcha-solver; chỉ httpx + SSRF-safe URLFetcher; terminal HTTP 401/403/429 phải KHÔNG retry |
| 22 — Idempotent mutation safety | Read-only detail fetch; retry giới hạn có backoff; không retry mạng chung mutation |
| 18 — No secrets in source | Không key mới nào được thêm |
| 14 — Scoring deterministic | Enrichment chỉ làm giàu evidence cho scoring; không thay đổi thuật toán chấm điểm |

---

## 3. Kết quả kiểm thử

```text
27/27 tests mới PASSED     (backend/tests/test_detail_enrichment.py)
39/39 tests liên quan PASSED (detail + ingestion_pipeline + adapters)
198/202 whole suite PASSED (4 failures TIỀN TỒN TẠI, đã được cách ly bằng git stash
                            xác nhận xảy ra cả ở base — không phải hệ quả thay đổi mới)
```

Phạm vi test chi tiết:

1. **PostedDateParser** (7 test): ISO / Z-suffix / epoch millis / "Posted 3 days ago" / "5 ngày trước" / "hôm qua" / invalid None.
2. **SecurityDetection** (4 test): Cloudflare challenge → detect; JD hợp lệ → không quét sạch; login gate → detect; JD dài có "sign in" → không false-positive.
3. **MergeHelpers** (5 test): dài thắng, không đi xuống grade, skills union no-dup, `posted_iso` không bị ghi đè, note failure sống cùng listing.
4. **DetailFetcher** (5 test): JSON-LD method; HTTP 403 terminal → BLOCKED 1 lần (không retry); TIMEOUT → retry thành công; content ngắn → INCOMPLETE; WAF → BLOCKED.
5. **AdapterParseRaw** (2 test): ITViec ưu tiên payload description; TopCV fallback card.
6. **PipelineIntegration** (4 test): enrichment persist full JD; BLOCKED → degrade; unsupported source → skip; budget limit SKIPPED chính xác.

---

## 4. Files thay đổi

```text
backend/app/services/extraction/detail_fetcher.py     [MỚI]      Core service (~500 dòng)
backend/app/services/ingestion_pipeline.py            [MODIFIED] BƯỚC 2.5 + IngestionStats 3 metrics mới
backend/app/core/config.py                            [MODIFIED] 4 settings DETAIL_FETCH_*
backend/app/services/collectors/itviec_adapter.py     [MODIFIED] parse_raw ưu tiên detail + posted capture
backend/app/services/collectors/topcv_adapter.py      [MODIFIED] parse_raw ưu tiên detail
backend/app/services/collectors/topdev_adapter.py     [MODIFIED] parse_raw ưu tiên detail
backend/app/services/collectors/vietnamworks_adapter.py [MODIFIED] richer-record merge
backend/tests/test_detail_enrichment.py               [MỚI]      27 test cases
```

Không có migration DB nào cần thiết (chỉ mở rộng `raw_jobs.raw_payload` JSONB — schema-agnostic).

---

## 5. Hướng phát triển tiếp (backlog)

- [ ] Trích xuất `salary range` từ JSON-LD `baseSalary` → `normalize_salary` deterministic.
- [ ] Extend `JobExtractedData` với `employment_type` (mapping FULL_TIME/PART_TIME/CONTRACT về taxonomy).
- [ ] Viết lại detail fetch bằng batch concurrent (asyncio.gather, max 5 concurrency) để rút ngắn daily batch.
- [ ] TAXONOMY 4 chiều (title/seniority/location/work_model category) từ repo tham khảo cho UI filter — Phase 2.8 candidate.
- [ ] Browser-render fallback (Playwright) chỉ cho JS-only SPA hợp lệ — giữ nguyên Invariant 19.

---

# Phase 2.8 — Full Unexpired Scanning & Expiry Detection

> **Ngày hoàn thành:** 2026-11-04
> **Phạm vi:** 5 nền tảng Việt Nam (ITViec, TopCV, TopDev, VietnamWorks, CareerLink). Các nguồn remote nước ngoài (Remotive, Upwork, ITNavi, GrowUpWork) **chưa** nâng cấp — vẫn chạy incremental như cũ.

## 6. Vấn đề tồn tại trước đây

| Triệu chứng | Nguyên nhân gốc |
| --- | --- |
| Chỉ quét được ~2 trang/nguồn dù gọi `limit=50` | `max_pages = min(25, max(1, (limit + 19) // 20))` |
| Dù có tăng `limit` vẫn không quét quá 500 tin | Trần cứng `min(25, ...)` bất kể tham số |
| Tin đã hết hạn vẫn hiện như đang tuyển | Không lưu `expires_at`, không có trạng thái EXPIRED |
| Job hết hạn bị cào lại mỗi chu kỳ | Không có cờ đánh dấu, không có bước bảo trì |
| Không có tín hiệu hạn nộp từ JSON-LD | `_extract_jsonld_meta()` bỏ qua `validThrough` |

## 7. Giải pháp triển khai

### 7.1 Quét toàn bộ (`full_scan`)

`ingestion_pipeline.run(..., full_scan: bool = False)`:

```text
full_scan=True → limit = 0            (collector hiểu 0 = KHÔNG GIỚI HẠN)
                → MAX_CONSECUTIVE_UNCHANGED = 0  (tắt dừng sớm theo unchanged streak)
full_scan=False → giữ nguyên hành vi incremental (limit thật, streak = 30)
```

Mỗi adapter VN:

```python
unlimited = limit <= 0
max_pages = 80 if unlimited else max(1, (limit + 19) // 20)
```

- Bỏ hoàn toàn trần cứng `min(25, ...)`.
- Trần an toàn `80` trang chỉ để chống vòng lặp vô hạn khi site phân trang tuần hoàn.

### 7.2 Smart Stop Condition (dừng khi gặp chuỗi tin hết hạn)

Vì các nguồn sắp xếp tin mới nhất trước (`sort=new`, `sort=date`, `ordering=latest_jobs`), khi gặp liên tiếp nhiều tin hết hạn thì các trang sau chắc chắn cũ hơn:

```text
MAX_CONSECUTIVE_EXPIRED = 15 (20 với VietnamWorks)
consecutive_expired >= ngưỡng → break toàn bộ pagination
```

### 7.3 Phát hiện hết hạn — 3 nguồn tín hiệu độc lập

| Tín hiệu | Nguồn | Xử lý |
| --- | --- | --- |
| `validThrough` / `expires` | JSON-LD `JobPosting` | `parse_posted_datetime()` → `expires_at` |
| `Hạn nộp hồ sơ: dd/mm/yyyy` | DOM (`.job-detail__info--deadline`, `[class*='deadline']`, regex toàn văn) | `extract_deadline_from_dom()` |
| Marker text | `"tin tuyển dụng đã hết hạn"`, `"no longer available"`, `"this position has been closed"`, … | `check_is_job_expired()` |
| `expiredDate` (epoch-ms) | VietnamWorks Search API | `datetime.fromtimestamp(ms/1000, tz=utc)` |

`JobDetailResult` bổ sung `expires_at: Optional[datetime]` và `is_expired: bool`. `merge_detail_into_payload()` ghi `raw_payload["expires_iso"]` + `raw_payload["is_expired"]`.

### 7.4 Trạng thái Job: EXPIRED (không xóa dữ liệu)

Trong `ingestion_pipeline.run()` BƯỚC 8:

```python
is_job_expired = payload["is_expired"] or (expires_at and expires_at < now_utc)
job_status = EXPIRED if is_job_expired else ACTIVE
```

- **Insert mới**: lưu với `status=EXPIRED`, `expires_at` set, tăng `stats.expired_marked`.
- **Update**: chỉ nâng cấp ACTIVE → EXPIRED; không hồi sinh tin đã hết hạn trừ khi nguồn trả về hạn mới còn hiệu lực.
- **Không xóa**: giữ lịch sử + tránh cào lại vô ích ở chu kỳ sau.

### 7.5 Bảo trì định kỳ `expire_outdated_jobs(db)`

```sql
UPDATE jobs SET status = 'EXPIRED'
WHERE status = 'ACTIVE' AND expires_at IS NOT NULL AND expires_at < now()
```

Gọi ở 2 nơi:
- `POST /api/v1/jobs/collect` (sau khi ingest) → trả `report.expired_total`.
- `daily_runner` BƯỚC 3.5 → chạy mỗi chu kỳ batch.

## 8. API & Runner

```text
POST /api/v1/jobs/collect?source=itviec&full_scan=true
  → report: { total_fetched, created, unchanged, duplicates_detected, errors,
              details_enriched, details_failed, details_skipped,
              expired_marked, expired_total, full_scan }
```

`daily_runner`:

```python
FULL_SCAN_SOURCES = frozenset({"itviec", "topcv", "topdev", "vietnamworks", "careerlink"})
full_scan = col.source_name in FULL_SCAN_SOURCES
```

Chỉ 5 nguồn VN được quét toàn bộ; nguồn nước ngoài giữ incremental.

## 9. Files thay đổi

```text
backend/app/services/extraction/detail_fetcher.py         [MODIFIED] expires_at/is_expired, validThrough,
                                                                     extract_deadline_from_dom, check_is_job_expired
backend/app/services/collectors/itviec_adapter.py          [MODIFIED] unlimited + smart stop + expires_at
backend/app/services/collectors/topcv_adapter.py           [MODIFIED] unlimited + deadline_text + expires_at
backend/app/services/collectors/topdev_adapter.py          [MODIFIED] unlimited + smart stop (card + fallback link)
backend/app/services/collectors/vietnamworks_adapter.py    [MODIFIED] expiredDate/approvedOn epoch-ms, hits_per_page=50
backend/app/services/collectors/careerlink_adapter.py      [MODIFIED] unlimited + smart stop + parse_raw detail-first
backend/app/services/ingestion_pipeline.py                 [MODIFIED] full_scan, job_status EXPIRED/ACTIVE,
                                                                     IngestionStats.expired_marked, expire_outdated_jobs
backend/app/api/v1/endpoints/jobs.py                       [MODIFIED] query param full_scan + report mở rộng
backend/app/services/daily_runner.py                       [MODIFIED] FULL_SCAN_SOURCES + BƯỚC 3.5 expiry maintenance
backend/tests/test_expiry_and_full_scan.py                 [MỚI]      18 test cases
```

Không có migration DB: `jobs.expires_at` và `JobStatusEnum.EXPIRED` đã tồn tại từ trước.

## 10. Kiểm chứng

```text
pytest tests/test_expiry_and_full_scan.py          → 18 passed
pytest tests/test_detail_enrichment.py
       tests/test_ingestion_pipeline.py
       tests/test_adapters.py
       tests/test_manual_ingestion.py
       tests/test_expiry_and_full_scan.py          → 66 passed
pytest (toàn bộ backend)                           → 216 passed, 4 failed (4 failure tiền tồn tại,
                                                      không liên quan Phase 2.8)
```

Nhóm test bao phủ:

1. **Deadline/expiry detection** (6): regex tiếng Việt, class TopCV, không deadline, marker VN/EN, tin còn hạn không bị flag.
2. **JSON-LD `validThrough`** (2): tương lai → `expires_at` + `is_expired=False`; quá khứ → `is_expired=True`.
3. **Merge helper** (2): ghi `expires_iso`/`detail_meta`; gắn cờ `is_expired` vào payload.
4. **VietnamWorks API** (1): `expiredDate` epoch-ms → `expires_iso`, `approvedOn` → `posted_iso`, tin quá hạn bị flag, `parse_raw` map `expires_at`.
5. **Pipeline** (4): quá hạn → EXPIRED; còn hạn → ACTIVE; cờ payload override; `expire_outdated_jobs` chỉ đổi đúng bản ghi.
6. **Full scan** (3): `full_scan=True` truyền `limit=0`; incremental giữ `limit`; full scan không dừng ở unchanged streak 30.

## 11. Backlog Phase 2.8+

- [ ] UI filter loại bỏ job `EXPIRED` khỏi danh sách mặc định (thêm toggle "Hiện tin đã hết hạn").
- [ ] Dashboard widget "tin sắp hết hạn trong 3 ngày" để ưu tiên ứng tuyển.
- [ ] Áp dụng `full_scan` cho Remotive/Upwork khi có nhu cầu (hiện chưa cần).
- [ ] Metric Prometheus `jobs_expired_total{source}` để theo dõi tỷ lệ tin hết hạn theo nguồn.
