# Open issues — handoff cho AI/kỹ sư mới

Đối chiếu source ngày 2026-11-09. Đây là trạng thái kỹ thuật, không phải chứng nhận production. Đọc `AGENTS.md`, `docs/ROADMAP.MD` và `tasks/IN_PROGRESS.MD` trước khi thay đổi. Các thống kê live bên dưới là quan sát trong phiên trước, không bảo đảm kết quả hiện tại.

## 1. TopCV: truy cập bị chặn không ổn định, nguyên nhân chưa xác định

**Bằng chứng:** Có lần collector lấy 20 bản ghi trong 4.6s; nhiều request khác trả 403 với trang `Attention Required! | Cloudflare`. Kết quả còn khác nhau giữa HTTP client và các lần chạy. Chưa đủ bằng chứng kết luận do rate-limit, bot-score, IP hay URL. Không có bằng chứng cho thời gian cooldown 30–60 phút.

- `backend/app/services/collectors/topcv_adapter.py` vẫn dùng `tim-viec-lam-it-phan-mem-c10026`. Một response đã khai báo canonical `tim-viec-lam-software-engineering-cr257cb258`; cần kiểm tra phạm vi ngành trước khi thay URL, không mặc định hai danh mục tương đương.
- HTTP 401/403/407/429 hoặc marker challenge làm collector raise `TopCV BLOCKED`. `backend/app/api/v1/endpoints/jobs.py` ánh xạ lỗi này thành 502. Nếu bị chặn sau trang đầu, danh sách đã fetch chưa được trả về cho pipeline.
- Partial scan + báo cáo mức độ hoàn thành là **đề xuất**, chưa triển khai; phải kiểm tra contract pipeline/API trước khi đổi.
- `robots.txt` và sitemap từng trả 200, sau đó cũng có lần 403. Không có `Disallow` không đồng nghĩa được cấp quyền crawl hoặc vượt WAF. Sitemap chỉ giúp khám phá URL; không đảm bảo quyền truy cập JD, trạng thái ACTIVE hay tính đầy đủ.
- Tuân thủ invariant 19: dừng khi gặp hạn chế; không bypass CAPTCHA/WAF/rate-limit. Không retry 403/429 để tìm đường vượt chặn. Phương án hiện có: dán JD thủ công; phương án khác: feed/API được TopCV cấp quyền.

## 2. Saramin: tổng metadata không khớp số ID duy nhất

`backend/app/services/collectors/saramin_adapter.py` thay TopDev, dùng public IT-category API với `page_size=20`. Probe trước ghi nhận metadata 319 nhưng chỉ 96 ID duy nhất qua 16 trang; các trang sau lặp dữ liệu. Đây là số quan sát, không phải trần cố định hoặc bằng chứng tất cả tin còn hạn.

Giữ dedup; báo riêng fetched/unique/created/duplicates/unchanged/ACTIVE. Migration `009_rename_topdev_saramin.py` đổi tên nguồn và kiểm tra collision. Phiên trước đã áp dụng lên DB local; chưa xác nhận DB production.

## 3. ITNavi: chưa xác minh hoàn tất full scan có detail

`backend/app/services/collectors/itnavi_adapter.py`:

- 10 tin/trang; incremental page budget tính theo 10, cap 25 trang; full scan cap 50 trang.
- `asyncio.gather` parse card trong một trang, gọi AJAX lấy canonical slug/description.
- Listing timeout retry một lần; lỗi AJAX được log rồi fallback, **không có retry AJAX tương ứng**.
- Fallback `/job-detail/{id}` từng redirect về trang chủ: không được coi là URL chi tiết đã xác minh.
- Probe listing-only từng tìm 483 ID duy nhất, nhưng full collector có detail đã timeout ở các budget 120–300s. Incremental 50 từng hoàn tất. Không kết luận full-scan timeout đã giải quyết.

## 4. Market và dữ liệu lịch sử

- Whitelist trong `backend/app/services/analytics/filters.py`: 7 nguồn VN + alias cũ `topdev`; excludes Remotive/Upwork/manual/mock.
- `market_source_predicate()` loại record có `RawJob.source_job_id` bắt đầu `growupwork-curated-`, không dùng cờ JSON `is_fallback`.
- GrowUpWork đã bỏ curated fallback. Probe từng thu 800 bản ghi; có cap pagination, không chứng minh đây là toàn bộ tin còn hạn.
- DB local từng có 5 GrowUpWork synthetic và 5 Upwork cũ; chưa kiểm đếm lại. Không tự xóa lịch sử.
- Live fetched counts không phải số job dedup ACTIVE trong DB. Chưa được duyệt chạy ingestion mới vào DB; không tự chạy hoặc commit/push.

## 5. Security và chất lượng còn cần theo dõi

Đọc `docs/SECURITY_REMEDIATION_PLAN.md`, `security/FINDINGS.md` và code trước khi đánh dấu hoàn tất:

- SEC-05: URL validation hiện tại không đủ để khẳng định chống DNS rebinding bằng transport pinning; kiểm tra `backend/app/services/extraction/url_fetcher.py`.
- SEC-06: access/refresh token còn trong localStorage; cookie migration là kế hoạch (`docs/TOKEN_STORAGE_MIGRATION_PLAN.md`), không phải tính năng đã có. Không đợi production mới cân nhắc rủi ro này.
- SEC-07: cần xác minh test không gọi LLM/network thật, không suy từ test pass rằng CI hoàn toàn offline.
- Full style lint còn nợ; correctness-only Ruff pass không có nghĩa mọi rule pass. Audit dependency dev và coverage cần kiểm tra lại bằng lệnh thực tế.
- PDF yêu cầu auth + ownership kể cả query token cho embed; UUID không phải public capability. Compiler fail-closed, kiểm tra PDF đúng 1 trang. Không khôi phục mô tả public PDF cũ.

## 6. Bằng chứng kiểm thử và cách chạy lại

Chạy lại trong lần review docs ngày 2026-11-09: **306 passed, 4 warnings**, Python 3.12, 46.62s. Correctness-only Ruff chạy lại và pass. Compose frontend build/browser checks là bằng chứng phiên trước (chưa chạy lại build/browser ở lần này), không phải xác nhận production. Coverage phần trăm chưa đo.

Từ `backend/` (PowerShell):

```powershell
$env:ENVIRONMENT='test'
$env:JWT_SECRET_KEY='ci-only-jwt-secret-not-for-deployment-0123456789'
$env:INTERNAL_API_SECRET='ci-only-internal-secret-not-for-deployment-0123456789'
..\.venv\Scripts\python.exe -m pytest -q -o log_cli=false
```

Từ repo root:

```powershell
.\.venv\Scripts\ruff.exe check --isolated --select E9,F63,F7,F82 backend/app backend/tests scripts
git diff --check
```

Build UI container: `docker compose run --rm frontend-build`, sau đó `docker compose restart backend`. React source ở `frontend/src`; `frontend/dist` là output sinh ra, không commit. Git working tree có nhiều thay đổi từ trước; dùng `git status`/`git diff` để phân biệt, không coi tất cả là thay đổi của phiên docs này.
