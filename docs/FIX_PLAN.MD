# Kế hoạch khắc phục các hạn chế đã ghi nhận

Ngày lập: 2026-11-09. Phạm vi: lập kế hoạch, chưa triển khai bản vá, migration, ingestion hoặc deploy.
Nguồn vấn đề: [OPEN_ISSUES](OPEN_ISSUES.md), [security remediation](SECURITY_REMEDIATION_PLAN.md), [findings](../security/FINDINGS.md).
Không dùng [architecture audit](ARCHITECTURE_AUDIT.md) lịch sử làm checklist tính năng còn thiếu.

## 1. Hiện trạng và giới hạn bằng chứng

- Backend đã chạy trong phiên này: **306 passed, 4 warnings, 30.29s**, với ENVIRONMENT=test và JWT/internal secrets giả. Đây không phải chứng minh test hoàn toàn offline: chưa có guard toàn cục chặn network.
- Không đo lại coverage, full Ruff, npm audit, build/browser hoặc production. Các số 2.207 lint findings và 3 dev vulnerabilities chỉ là số lịch sử, phải đo lại.
- Working tree có nhiều thay đổi từ trước; kiểm tra hiện tại báo 155 modified và 16 untracked. Không tự reset, stash, commit hoặc coi toàn bộ diff là sản phẩm phiên này.
- Probe TopCV/Saramin/ITNavi và số record lịch sử trong docs chưa được chạy lại. Không suy ra nguyên nhân WAF, cooldown, độ đầy đủ hay số ACTIVE từ chúng.
- Workflow fan-out trước bị giới hạn concurrency; lần tiếp theo trả 12 kết quả null. Không có review hợp lệ từ hai lượt đó. Review/team chỉ được ghi nhận khi thực sự trả nội dung.

## 2. Thứ tự thực hiện

| Mốc | Công việc | Phụ thuộc | Ước lượng* | Điều kiện ra mốc |
| --- | --- | --- | --- | --- |
| P0 | Chốt baseline diff; SEC-07 cô lập test; đo lint/audit/coverage | Không | 1–2 ngày | Test unmocked không ra network; suite và mock transports vẫn chạy |
| P1-A | SEC-05 transport pinning | P0 | 2–3 ngày | Kết nối thực đến IP đã kiểm tra, TLS/redirect/IPv6 được test |
| P1-B | Contract scan + TopCV + Saramin | P0 | 2–3 ngày | BLOCKED/partial không bị báo success; counters có nghĩa rõ ràng |
| P2-A | ITNavi budget/detail + kiểm kê Market | P1-B | 2–3 ngày | Timeout/duplicate/cap có stop_reason; không bịa full coverage |
| P2-B | SEC-06 auth migration theo topology | P0; quyết định deployment | 3–5 ngày | CSRF, rotation, PDF ownership và browser cookie gates qua |
| P3 | Lint/dependencies, Discord, release/deployment checks | Các thay đổi liên quan xong | 2–4 ngày | CI thực, build/browser và checklist release có bằng chứng |

*Ngày công dự kiến, không phải cam kết; tổng khoảng 12–20 ngày cho một người, tùy scope auth và quyền truy cập deployment. P1-A/P1-B có thể chạy song song. Không gộp tất cả thành một PR.

## 3. P0 — Môi trường kiểm thử và baseline

### SEC-07: chặn network, không chỉ bỏ API key

Bằng chứng: [conftest](../backend/tests/conftest.py#L1-L14) hiện chỉ tắt rate limiter; import app xảy ra trước fixture.

- Thiết lập dummy environment và vô hiệu credentials provider **trước khi import settings/app**; kiểm tra cả settings đã cache, không chỉ os.environ.
- Dùng guard ở tầng kết nối socket cho test unit/integration mặc định. Không chặn toàn bộ httpx request vì ASGITransport/MockTransport là đường test hợp lệ.
- Test cần network thật phải là nhóm integration opt-in riêng, mặc định bị loại trong CI; không mở một marker cho phép mọi host tùy ý. DB integration dùng DB test được chỉ định, không dùng URL production lấy từ .env.
- Test mới dự kiến: `backend/tests/test_network_isolation.py`; assert request không mock bị chặn trước connect, fake provider key không kích hoạt LLM, MockTransport và ASGI app vẫn hoạt động. Một subprocess pytest nhỏ chứng minh guard bắt được request từ test khác.
- Chạy lại suite với dummy secrets, không log khóa. **Done:** test chứng minh guard fail-closed, suite pass; không chỉ dựa vào thời gian chạy ngắn.

### Baseline chất lượng

Đo full Ruff, nhóm theo rule/file; đo coverage với pytest-cov đã cài và audit dev dependencies. Lưu output CI/artifact hoặc ghi ngắn trong task hiện có; chưa cần xây hệ thống evidence ledger mới. Kiểm tra diff theo từng workstream, không mass auto-fix trên working tree hiện tại.

## 4. P1-A — SEC-05 DNS transport pinning

Bằng chứng: [URL precheck](../backend/app/services/extraction/url_fetcher.py#L15-L48) resolve DNS, nhưng [request](../backend/app/services/extraction/url_fetcher.py#L145-L160) dùng AsyncClient thường và resolve độc lập.

- Resolve một lần tại ranh giới mở kết nối, kiểm tra tất cả địa chỉ và chỉ connect IP đã chấp nhận; từ chối non-global addresses, mapped IPv6 private và hostname/userinfo/port không hợp lệ theo policy rõ ràng.
- Giữ URL hostname gốc cho Host, TLS SNI và certificate verification; không đổi đơn giản URL sang IP rồi tắt verify TLS.
- Thử implementation nhỏ nhất dùng transport/httpcore backend hiện có. Trước khi chọn custom backend/private hook, xác minh API/version và viết một proof test. Không chốt một extension chưa kiểm chứng là đã hoạt động.
- Tắt proxy từ môi trường cho đường fetch này (`trust_env=False`); redirects giới hạn số hop và mỗi target đi qua cùng transport policy. Không tái dùng connection vượt policy/host.
- Áp dụng cho mọi nhánh URLFetcher, kể cả [VietnamWorks API helper](../backend/app/services/extraction/url_fetcher.py#L352-L408); rà soát đường detail enrichment do URL không tin cậy có thể đi qua.
- Test dự kiến `backend/tests/test_url_fetcher_transport.py`: DNS lần đầu public/lần sau loopback; mixed public/private records; IPv6/mapped IPv6; redirect private; DNS failure; proxy env; SNI/Host/certificate hostname; timeout và cleanup.
- **Done:** fake network backend ghi nhận connect chỉ nhận validated IP; hostname TLS vẫn đúng; không resolve hostname lần hai ở tầng connect. Không gọi đây là OS sandbox hoặc chống mọi SSRF trên toàn hệ thống.
- Rollback: nếu transport mới không đạt gate, vô hiệu URL ingestion fail-closed và giữ raw-text import; không quay lại đường fetch không pin như thể đã khắc phục.

## 5. P1-B — Scan contract trước, sửa collector sau

### Contract chung, additive và không phá clients

Bằng chứng: [collector interface](../backend/app/services/collectors/base.py), [pipeline](../backend/app/services/ingestion_pipeline.py#L35-L80), [API](../backend/app/api/v1/endpoints/jobs.py#L245-L274). Adapter hiện trả list; pipeline chỉ nhận dữ liệu sau khi fetch hoàn tất.

- Thêm kết quả scan nhỏ trong module collector hiện có: items, stop_reason, pages_fetched, upstream_total (nullable), completion (`complete`/`partial`/`unknown`), failure_kind (`blocked`/`timeout`/`error`/null).
- Giữ `fetch_jobs()` list cho consumer cũ; thêm entry point kết quả có metadata với wrapper mặc định cho adapter chưa chuyển. Không gán `complete` cho adapter cũ khi không biết lý do dừng.
- Phân biệt `rows_received`, `unique_items`, `processed`, `created`, `updated`, `unchanged`, `duplicates_detected`, `errors`, `expired_marked`. `created` hiện tăng cả nhánh update tại [pipeline](../backend/app/services/ingestion_pipeline.py#L246-L327); cần test/fix ý nghĩa trước khi public thêm thống kê.
- Giữ field legacy trong giai đoạn chuyển đổi và ghi rõ semantics cũ; thêm field mới, không âm thầm đổi nghĩa gây hỏng consumer. ACTIVE inventory là truy vấn DB riêng có timestamp, không cộng từ fetched/created.
- `upstream_total` không phải mẫu số đáng tin cho coverage; tỷ lệ coverage để null khi không chứng minh được. Dừng ở cap/timeout/repeated page không phải full scan hoàn tất.
- Không đổi ngay 502 thành 200 với `status=success`. Giữ response lỗi tương thích cho blocked; bổ sung payload report có cấu trúc và kiểm tra frontend error parsing. API version/contract mới chỉ đổi status sau khi consumers cùng cập nhật.
- Daily runner ghi trạng thái từng nguồn và tổng hợp partial/error thay vì chỉ tăng một số lỗi; source bị chặn không làm mất report của nguồn khác.
- Test fixtures: complete, empty hợp lệ, blocked trang đầu, blocked trang 2, timeout, invalid payload, page cap, unchanged early stop. Test API + daily runner, không chỉ adapter.

### TopCV

Bằng chứng: [URL và block detection](../backend/app/services/collectors/topcv_adapter.py#L26-L71); [API mapping](../backend/app/api/v1/endpoints/jobs.py#L248-L254).

- Giữ dữ liệu trang đã nhận trong scan result khi gặp restriction; dừng ngay và ghi blocked/partial. Không retry 401/403/407/429, không đổi IP/client/cookie để vượt WAF.
- Chỉ xử lý listing đã nhận trước block theo policy rõ; không tiếp tục fetch detail từ nguồn vừa bị chặn. Trang đầu bị block phải có zero records + blocked, không phải empty success.
- Giữ category URL hiện tại cho đến khi có bằng chứng phạm vi ngành tương đương từ nguồn được phép truy cập; canonical URL một response không đủ để đổi scope.
- **Done:** fixture trang 1 có N items + trang 2 403 giữ N items/report, số request dừng ở 2, không gọi detail; manual JD luôn là phương án thay thế. Không hứa sẽ khôi phục truy cập TopCV.

### Saramin

Bằng chứng: [adapter](../backend/app/services/collectors/saramin_adapter.py#L25-L96) **đã có dedup ID và dừng khi trang không có ID mới**. Không viết lại tính năng này.

- Bổ sung stop_reason `no_new_ids`, raw row/unique counts, upstream metadata và cap; giữ validation URL/schema hiện có. Không suy ra lỗi API từ một probe cũ.
- Fixture nhiều trang lặp ID phải dừng, trả mỗi ID một lần và completion chưa chắc đầy đủ. Fixture metadata sai/missing phải báo lỗi có cấu trúc, không fake total.
- Xem migration `009_rename_topdev_saramin.py` bằng code và read-only Alembic current/history trên môi trường được chỉ định; local head không chứng minh production head. Backup + collision check trước thao tác ghi được giao riêng.
- **Done:** báo rõ unique khác upstream_total; không dùng 319/96 như hằng số; migration production vẫn OPEN cho đến khi có bằng chứng môi trường đó.

## 6. P2-A — ITNavi và dữ liệu Market

### ITNavi

- Đo request count/concurrency bằng fake client trước khi tối ưu; listing-only không chứng minh full scan có detail hoàn tất.
- Bounded detail concurrency và whole-run deadline; retry tối đa một lần cho timeout/transient phù hợp, trong budget còn lại; không retry restriction status. Không tăng concurrency để né rate limit.
- Nếu AJAX canonical/detail thất bại, đánh dấu URL unverified; không coi `/job-detail/{id}` là canonical đã xác minh. Nếu kiểm tra detail thực tế, xác nhận final URL/identity marker đúng job, không homepage/login/challenge.
- Fixture: AJAX timeout rồi thành công, 403 không retry, homepage redirect, malformed JSON, budget cạn giữa trang, cancellation không để task chạy nền. Report phải giữ listing đã nhận và ghi partial/detail failure.
- **Done:** deterministic full fixture hoàn tất trong deadline; incomplete detail được thể hiện rõ. Live bounded probe (nếu được phép riêng) chỉ chứng minh lần chạy đó, không chứng minh thu toàn bộ site.

### Market/history

- Giữ whitelist VN + alias legacy theo [OPEN_ISSUES §4](OPEN_ISSUES.md#4-market-và-dữ-liệu-lịch-sử); giữ exclusion `growupwork-curated-*` và không tự xóa lịch sử.
- Test SQL/source filter cho VN, topdev alias, Remotive/Upwork/manual/mock và synthetic IDs; test ACTIVE/EXPIRED/MERGED theo contract Market hiện có.
- Read-only inventory theo source/status, số synthetic candidates, DB migration revision và thời gian snapshot. Không xuất PII/secrets vào report; không chạy ingestion mới trong công việc lập kế hoạch này.
- Nếu cần sửa dữ liệu: đề xuất riêng theo tập ID, backup và transaction/rollback; không dùng delete lịch sử để làm chart đẹp.
- **Done:** fetched/unique/DB ACTIVE tách biệt; derived/estimated/insufficient labels và source exclusions có regression test.

## 7. P2-B — SEC-06 auth migration theo cổng quyết định

Bằng chứng: [API client](../frontend/src/api/client.ts#L100-L188) lưu access/refresh và refresh qua JSON; [migration draft](TOKEN_STORAGE_MIGRATION_PLAN.md) vẫn là kế hoạch.

1. Chốt topology trước: ưu tiên frontend/API cùng site qua custom domains hoặc same-origin proxy phù hợp nền tảng. Pages và Render khác site có thể bị browser chặn third-party cookies dù `SameSite=None; Secure`; CORS không giải quyết việc đó.
2. Chọn bước tối thiểu: refresh token HttpOnly cookie, access token chỉ trong memory và Bearer header. Không tiếp tục trả refresh token trong JSON/localStorage sau migration. Nếu dùng cả access cookie, mọi cookie-auth mutation phải có CSRF gate.
3. CORS exact origins + credentials; frontend credentials include ở endpoint cần cookie. Kiểm tra Origin và CSRF token cho refresh/logout/login và mọi cookie-auth mutation; không dựa vào SameSite=None như biện pháp CSRF. Cookie host-only, path/lifetime/expiry/delete nhất quán.
4. Giữ rotation/family revocation và refresh mutex. Không replay mutation sau timeout/network error; phân biệt 401 auth retry với retry mù khi chưa biết server đã xử lý hay chưa.
5. PDF: ưu tiên fetch với Bearer rồi blob URL cho iframe; revoke blob khi đổi/unmount. Nếu giữ query JWT trong chuyển tiếp, ownership/auth không đổi, hạn chế logging/referrer. Không biến UUID hoặc URL ký đơn thuần thành quyền truy cập công khai.
6. Rollout backend/frontend phối hợp, xóa hai localStorage token cũ sau cutover. Rollback không âm thầm ghi refresh token lại vào localStorage; nếu lỗi cookie thì yêu cầu login lại hoặc tắt flow an toàn.

**Tests/Done:** register/login/refresh/logout, concurrent refresh, replay/revocation, cross-origin CSRF bị từ chối, origin allowlist, cookie flags/deletion, reload session, Safari/Firefox/Chrome privacy modes trên topology thật; PDF owner/non-owner/guest và JIT vẫn đúng. Chưa vượt browser gate thì SEC-06 vẫn OPEN, không đánh dấu fixed vì đã thêm Set-Cookie.

## 8. P3 — Debt, Discord và release

- **Lint/dependency:** đo baseline hiện tại; sửa từng nhóm/file chạm tới, giữ correctness gate và không tăng style debt. Audit production/dev riêng; chỉ cập nhật dependency có đường fix đã kiểm chứng lockfile/build, không `audit fix --force` mù. Không thêm framework chỉ để theo dõi debt.
- **Coverage/CI:** đo tổng + module vừa sửa; ưu tiên branch của security/error paths hơn ép số phần trăm toàn repo thiếu baseline. [CI](../.github/workflows/ci.yml) đã có pytest, correctness Ruff, typecheck/build/serving; thêm isolation/coverage artifacts phù hợp. CI config tồn tại không đồng nghĩa GitHub-hosted run đã pass.
- **Discord:** kiểm tra từng privileged command trước khi đổi principal. Trước mắt giữ trusted/private + allowlist bắt buộc cho lệnh nhạy cảm hoặc deprecate sang Web links; không xây capability framework nếu chỉ cần bỏ privileged handlers. Test người ngoài allowlist không tạo mutation và notification vẫn độc lập domain.
- **Repo hygiene:** chỉ scan read-only và report đã redact; rotate secret nếu thực sự lộ. Không tự rewrite Git history/force-push, không xuất PII context. Publishing seed dùng ví dụ ẩn danh; không đổi runtime source of truth.
- **Deployment:** kiểm tra exact CORS origins, strong secrets, TLS, log redaction query token; `/health` zero DB và `/health/ready` 503 an toàn khi DB lỗi; no keep-alive polling, read-only bounded retry; Compose development root/reload/mount không phải production sandbox.
- **Release:** frontend build/serving + browser guest/auth, cold start, PDF, mobile và Market states. Không gọi production certification từ local tests. Không restore legacy frontend hay texlive-latex-extra.

## 9. Quy trình agent team cho từng PR

- Lead chốt contract/acceptance trước; implementer chỉ sửa write scope của task; reviewer đọc diff độc lập và phản biện tests. Một task chưa complete không được coi là xong vì agent đang inactive.
- Scopes song song: SEC05 extraction transport; ingestion base/pipeline/API; auth backend+frontend. Serialize khi cùng sửa conftest, CI hoặc API client; P0 owner hoàn thành trước khi nhánh khác dựa vào guard.
- Mỗi PR: RED test tái hiện → sửa tối thiểu → GREEN targeted tests → suite phù hợp → diff check → cập nhật đúng mục task/doc. Không gom refactor/lint toàn dự án vào bugfix.
- Workflow chỉ fan-out nhỏ có giới hạn; kết quả null/failed phải ghi chưa review, không tính là PASS. Không tự lặp hàng chục agent khi không có bằng chứng tiến triển.

## 10. Lệnh và điều kiện hoàn tất

Từ repo root (PowerShell), sau khi đã có network isolation:

```powershell
$env:ENVIRONMENT='test'
$env:JWT_SECRET_KEY='ci-only-jwt-secret-not-for-deployment-0123456789'
$env:INTERNAL_API_SECRET='ci-only-internal-secret-not-for-deployment-0123456789'
# Chạy pytest từ backend/ để giữ cùng import/config như baseline:
Push-Location backend
try { ..\.venv\Scripts\python.exe -m pytest -q -o log_cli=false } finally { Pop-Location }
.\.venv\Scripts\ruff.exe check --isolated --select E9,F63,F7,F82 backend/app backend/tests scripts
git diff --check
# Nếu sửa frontend:
npm --prefix frontend run build
```

Đo coverage riêng với `--cov=app --cov-branch --cov-report=term-missing` khi pytest-cov khả dụng; không giả định nó đã được cấu hình. UI local Compose dùng build/restart theo AGENTS, không tự deploy.

Checklist Done cho từng hạng mục: phạm vi diff rõ; test tái hiện và acceptance qua; không vi phạm invariant; output/date/environment ghi trong task; rollback mô tả được; reviewer có kết quả thực; remaining live/deploy gates ghi OPEN. Lập kế hoạch xong không có nghĩa các lỗi đã sửa.

## 11. Bước kế tiếp đề xuất

Bắt đầu **P0 SEC-07**, rồi tách hai PR song song **SEC-05** và **scan contract**. Chưa đổi category TopCV, chưa thu thập ghi DB, chưa migration production, chưa cookie cutover, chưa commit/push/deploy trong phiên lập kế hoạch.

Tự đánh giá bản kế hoạch: Accuracy 4/5 (source trọng yếu có dẫn chứng; live/prod chưa kiểm tra), Completeness 4/5 (bao phủ các nhóm docs; runtime integration còn gate), Clarity 4/5 (mốc và Done rõ; nhiều workstream), Actionability 4/5 (files/tests/rollout có hướng cụ thể; transport cần proof test), Conciseness 4/5 (một tài liệu trung tâm, không tách thêm bộ governance). Tổng 4.0/5; ưu tiên xác minh transport API và topology cookie khi triển khai.
.