# Ingestion Hardening Report — Detail Page Enrichment (Phase 2.7)

> **Ngày hoàn thành:** 2026-11-04
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
