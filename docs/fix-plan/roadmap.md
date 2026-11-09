# Roadmap remediation — sequencing, dependency graph & milestones

**Ngày lập:** 2026-11-09 (Asia/Saigon) · **Vai trò:** roadmap/sequencing planner · **Chế độ:** planning only, không sửa source/test/config.
**Đích hợp nhất:** phần cross-cutting roadmap của `docs/FIX_PLAN.MD`. Artifact này không thay thế phần chi tiết theo từng workstream do Lead hợp nhất.
**Nguồn chuẩn (đã đọc):** `docs/OPEN_ISSUES.md` (6 mục) · `docs/SECURITY_REMEDIATION_PLAN.md` · `security/FINDINGS.md` · `docs/ROADMAP.MD` · `tasks/IN_PROGRESS.MD` · `tasks/TODO.MD` · `tasks/DONE.MD` · `docs/DECISIONS.MD` (ADR-006/008/011/014/015) · `docs/TOKEN_STORAGE_MIGRATION_PLAN.md` · `AGENTS.MD` (Critical Invariants, Development Workflow).
**Nguyên tắc bất biến của kế hoạch:** (1) không tin pass-count lịch sử — mọi "fixed" phải có rerun command + output; (2) invariant 19 — không bypass CAPTCHA/WAF/rate-limit/access restriction; (3) không tự chạy ingestion ghi DB, migration production, commit/push, rewrite history khi chưa có quyết định của human owner; (4) ADR-014/015 — thay đổi frontend không được phá performance budget (backdrop-filter 0 trên data surface, đo bằng harness) và không mở lại theme architecture.

## 0. Snapshot precondition (2026-11-09)

Working tree **không sạch**: `git status --porcelain` = **170 entry** = **155 tracked file thay đổi** (70 `M`, 85 `D`) + **15 untracked**; `git diff --stat` = **1.170 insertions / 16.886 deletions**. Trong 15 untracked có các file mà remediation **phụ thuộc trực tiếp**: `backend/app/services/collectors/saramin_adapter.py`, `backend/alembic/versions/009_rename_topdev_saramin.py`, `backend/app/services/job_filters.py`, `backend/tests/test_collectors_regression.py`, `.github/workflows/ci.yml`, `docs/OPEN_ISSUES.md`, `docs/testing/`, `scripts/`. Trong 85 deletion có `backend/app/services/collectors/topdev_adapter.py` và legacy `frontend/js`, `frontend/css`. Hệ quả: bất kỳ lệnh `git stash`/revert/checkout nào cũng có thể **xoá Saramin collector, migration 009 và CI** khỏi working tree — mọi evidence sinh ra trước checkpoint là không tái lập được. Đây là **P0 precondition risk**, không phải chi tiết vận hành.

Baseline tham chiếu (chưa được planner chạy lại; Lead đang giữ baseline verification): **306 passed, 4 warnings, Python 3.12, 46.62s** (`docs/OPEN_ISSUES.md §6`); correctness-only Ruff pass; coverage chưa đo; GitHub-hosted CI chưa xác nhận chạy.

## 1. Bảng workstream tổng hợp

Mức độ: Critical/High/Medium/Low theo impact lên dữ liệu, security, khả năng claim trung thực. Trạng thái xác minh: **OPEN** (chưa có fix/verification), **PARTIAL** (một phần code đã có nhưng gate chưa đạt), **DOC-ONLY** (chỉ có kế hoạch/tài liệu). Effort: S ≤ 1 ngày, M 2–3 ngày, L 4–6 ngày (dev-day, chưa gồm review).

| ID | Workstream | Nguồn docs (file:section) | Mức độ | Trạng thái | Loại | Effort | Phụ thuộc remediation |
|---|---|---|---|---|---|---|---|
| WS-00 | Freeze/branch/commit-or-archive working tree | `OPEN_ISSUES.md §6`; git snapshot mục 0 | Critical | OPEN | ops | S — 0.5–1d | OD-1; **blocks tất cả** |
| WS-01 | TopCV blocked-access handling + partial scan/coverage reporting | `OPEN_ISSUES.md §1`; `AGENTS.MD` invariant 19; `jobs.py:249-252` | High | PARTIAL: BLOCKED→502 có, partial-scan/report chưa có | code + test + docs | M — 2–3d | WS-04 (contract report), OD-6 |
| WS-02 | Saramin metadata-vs-unique-ID + dedup reporting + migration verification | `OPEN_ISSUES.md §2`; `docs/testing/source-recovery.tdd.md`; `ROADMAP.MD` Phase 2.8 | High | PARTIAL: dedup giữ, report chưa đủ, migration 009 mới áp local | code + test + ops | M — 2d | WS-04, OD-2 |
| WS-03 | ITNavi full-scan-with-detail timeout/retry/fallback verification | `OPEN_ISSUES.md §3`; `itnavi_adapter.py` | Medium | OPEN: full-scan timeout 120–300s chưa giải quyết; AJAX không retry | code + test | M — 2d | WS-04 (metrics) |
| WS-04 | Ingestion observability contract (fetched/unique/created/ACTIVE/blocked/partial) | `OPEN_ISSUES.md §2,§4`; `ingestion_pipeline.py:35-47`; `schemas/job.py` | High | OPEN: fields rải rác, không có contract thống nhất | code + test + docs | M — 2–3d | WS-00; **blocks WS-01/02/03/05** |
| WS-05 | Market/historical data integrity + recensus vs deletion policy + write approval gate | `OPEN_ISSUES.md §4`; `analytics/filters.py`; `MARKET_ANALYTICS.md` | High | PARTIAL: whitelist + exclusion có, recensus/chính sách xoá/policy chưa | ops + code + docs | M — 2d (+ write gate riêng) | WS-02, OD-2 |
| WS-06 | SEC-05 SSRF DNS transport pinning | `FINDINGS.md §SEC-05`; `SECURITY_REMEDIATION_PLAN.md "Remaining work"`; `url_fetcher.py` | Medium | OPEN: precheck có, transport chưa pin | code + test | M — 2–3d | WS-00; chặn feature manual ingestion |
| WS-07 | SEC-06 HttpOnly cookie migration (multi-gate) | `FINDINGS.md §SEC-06`; `TOKEN_STORAGE_MIGRATION_PLAN.md`; `SECURITY_REMEDIATION_PLAN.md` | Medium | OPEN (DOC-ONLY plan; code vẫn localStorage) | code + test + ops | L — 4–6d | OD-3, WS-11 (topology) |
| WS-08 | SEC-07 global test network isolation + credential clearing | `FINDINGS.md §SEC-07`; `SECURITY_REMEDIATION_PLAN.md`; `tests/conftest.py` | Low | OPEN: conftest chỉ disable rate limit | test + ops | S — 1d | WS-00; nên đứng trước thay đổi rủi ro cao |
| WS-09 | Quality debt: full style lint, dev npm audit, coverage, GitHub CI, build/browser | `OPEN_ISSUES.md §5,§6`; `IN_PROGRESS.MD "Audit remediation"` (2.207 findings) | Medium | OPEN/PARTIAL: correctness Ruff pass; style debt, coverage, hosted CI chưa | test + ops | M — 2–3d | WS-08 (conftest/CI single owner) |
| WS-10 | Discord legacy privileged commands + repo-public hygiene | `SECURITY_REMEDIATION_PLAN.md "Remaining work"`; `DISCORD_BOT_DEPLOYMENT.md` (owner check không universal; `apply`/`resume` thiếu check) | High | OPEN (Discord PARTIAL: có owner check rời rạc) | code + ops + docs | M — 2–3d | WS-00, OD-4, OD-5 |
| WS-11 | Deployment verification (Render/Supabase/CORS/secrets/log redaction/health) | `SECURITY_REMEDIATION_PLAN.md "Deployment verification"`; `AGENTS.MD` invariants 20–22 | High | OPEN | ops | M — 2d | WS-07 (cookie topology), WS-10 (rotation) |
| WS-12 | Documentation truth: evidence ledger thay pass-claim chưa xác minh | `OPEN_ISSUES.md §6`; `ROADMAP.MD` correction note; `IN_PROGRESS.MD` docs review | Medium | OPEN | docs | M — 1–2d | Toàn bộ WS; chạy cuối |

**Ghi chú trạng thái:** WS-02 và WS-05 đang ở trạng thái nguy hiểm nhất về mặt "truth": migration 009 đã chạy local nhưng **chưa xác nhận production**, và DB local từng có synthetic rows chưa kiểm đếm lại (`OPEN_ISSUES.md §2, §4`). WS-09 có con số 2.207 style findings **chỉ là claim lịch sử** — phải đo lại và ghi command trước khi dùng làm gate.

## 2. Dependency graph

### 2.1 Gate P0 — bắt buộc trước mọi workstream

```
[WS-00 FREEZE GATE: branch remediation/2026-11-09 + checkpoint commit(s) + tag/archive]
   │  (không có gate này: 15 untracked file trọng yếu + 85 deletion có thể biến mất)
   ├─► WS-08 SEC-07 (network-deny conftest + dummy env + CI commit)
   │        └─► WS-09 baseline (style-lint count, coverage, hosted CI)
   └─► toàn bộ WS-01 … WS-12
```

### 2.2 Chuỗi blocking chính

```
WS-04 INGESTION OBSERVABILITY CONTRACT  (P1, contract + schema + API report)
   ├─► WS-01 TopCV partial scan/coverage report   (P1)
   ├─► WS-02 Saramin fetched/unique/created/ACTIVE + dedup report (P1)
   ├─► WS-03 ITNavi timeout/retry metrics + fallback proof (P1)
   └─► WS-05 Market recensus report (fetched ≠ unique ≠ ACTIVE) (P1, read-only)

WS-02 migration 009 verification (local → staging/prod evidence)
   └─► WS-05 write/recensus decision (P1 report → P2 write only nếu OD-2 approve)

WS-06 SEC-05 (url_fetcher transport pinning)  ──► chặn mọi feature mới dùng URLFetcher (manual ingestion)
WS-07 SEC-06 (cookie) phụ thuộc: OD-3 topology ──► CSRF design ──► credentialed CORS ──► iframe PDF auth
WS-10b repo hygiene: rotation (làm trước) ──► secrets history scan ──► OD-4 rewrite decision
WS-10a Discord scoping ──► WS-11 deployment verification (secret scope + CORS)
WS-11 deployment verification ──► WS-12 docs truth (deployment claims cần evidence)

WS-09 quality/CI gate  ──► phải đứng TRƯỚC các thay đổi rủi ro cao (SEC-05/06, migration, ingestion writes)
WS-12 evidence ledger ──► chạy CUỐI, sau khi mọi lane đóng; không lane nào được sửa docs truth song song
```

### 2.3 Song song được / phải serialize

- **Song song an toàn (file ownership rời nhau):** WS-01 `collectors/topcv_adapter.py` ↔ WS-02 `collectors/saramin_adapter.py` + migration ↔ WS-03 `collectors/itnavi_adapter.py` ↔ WS-06 `extraction/url_fetcher.py` ↔ WS-07 `frontend/src/api/client.ts` + `auth.py` ↔ WS-10a `discord-bot/src/` (sau khi WS-04 contract chốt).
- **Phải serialize:** WS-04 (owner duy nhất của `ingestion_pipeline.py`, `schemas/job.py`, `api/v1/endpoints/jobs.py`, `job_filters.py`, `daily_runner.py`) trước các báo cáo của WS-01/02/03/05; `backend/tests/conftest.py` + `.github/workflows/ci.yml` (owner duy nhất: WS-08/09); `backend/app/main.py` (CORS/security: owner duy nhất WS-07/WS-11); `backend/tests/test_collectors_regression.py` (hiện là file dùng chung của TopCV/CareerLink/Saramin/GrowUpWork — giao một owner, các lane khác thêm file test mới); git commit/history rewrite/DB migration execution (Lead/ops exclusive); `docs/**` final truth pass (WS-12 exclusive).

**Quy tắc:** dirty-tree gate là P0; mọi milestone sau chỉ bắt đầu khi exit gate trước đã đạt bằng evidence, không bằng "đã xong".

## 3. Milestones P0–P3

Tổng effort ước tính: **~24–33 dev-day**; với phân rã lane ở mục 4 còn khoảng **9–13 ngày lịch** (chưa gồm thời gian chờ human approval OD-1…OD-8).

### P0 — Freeze, checkpoint & evidence baseline (1–2 ngày)

- **Mục tiêu:** biến working tree 170-entry thành baseline bất biến, tái lập được; dựng test isolation + CI gate tối thiểu.
- **Workstreams:** WS-00 (bắt buộc), WS-08, một phần WS-09 (CI workflow, baseline style/audit/coverage).
- **Entry gate:** Lead hoàn tất baseline verification đầu tiên (pytest + build + lint); human trả lời OD-1 (branch/commit strategy).
- **Exit gate / acceptance evidence:** (a) nhánh `remediation/2026-11-09` + checkpoint commit đã tạo (hoặc archive tag theo OD-1); (b) `git status --porcelain` sạch ngoài ignored; (c) `backend/tests/conftest.py` có fixture deny outbound network toàn cục + clear `GEMINI_API_KEY`/provider keys; (d) `.github/workflows/ci.yml` được track với dummy env; (e) file baseline `docs/testing/BASELINE_2026-11-09.md` ghi command + output (pass count, Python/Node version, date); (f) style-lint baseline count và `npm audit --omit=dev` output được ghi; (g) coverage: đo được thì ghi %, không đo được thì ghi rõ "chưa đo + lý do".
- **Cannot claim done without:** `git status --porcelain` rỗng (trừ ignored), `pytest` dummy-env pass count bằng/khác baseline có giải thích, `ruff` correctness, `git diff --check`, `npm --prefix frontend run build`, `npm audit --omit=dev`, và commit hash của checkpoint.
- **Effort:** 1–2 ngày. **Blocker:** OD-1.

### P1 — Ingestion correctness & observability (4–6 ngày)

- **Mục tiêu:** contract báo cáo ingestion thống nhất; TopCV/Saramin/ITNavi có hành vi và bằng chứng đúng; recensus market **read-only**.
- **Workstreams:** WS-04 (mở màn, owner duy nhất), rồi WS-01, WS-02, WS-03, WS-05 (read-only report).
- **Entry gate:** P0 exit + OD-2 tối thiểu ở mức "approve read-only probe/report, chưa approve DB write".
- **Exit gate / acceptance evidence:** (a) contract định nghĩa tường minh `fetched / unique / created / active / unchanged / duplicates / blocked / partial / errors` + schema test; (b) `POST /api/v1/jobs/collect` trả report có `blocked`/`partial` thay vì 502 im lặng mất dữ liệu đã fetch; TopCV trả `BLOCKED` có cấu trúc (giữ listing đã lấy, không retry 403/429); (c) Saramin report tách fetched 319-metadata vs 96 unique, dedup không đổi; (d) ITNavi full-scan-with-detail có deadline tổng hữu hạn, retry AJAX policy tường minh, `fallback /job-detail/{id}` được chứng minh không redirect về homepage bằng test; (e) market recensus report (trước/sau, synthetic `growupwork-curated-*`, alias `topdev`) **không ghi DB**; (f) mọi claim P1 có evidence row theo mục 6.
- **Cannot claim done without:** `pytest tests/test_collectors_regression.py tests/test_saramin_fields.py tests/test_jobs_filters_pagination.py` (và file test mới của từng lane) ghi RED→GREEN; full pytest dummy-env; `ruff` correctness; `git diff --check`; `python scripts/check_collectors.py` chỉ khi được phép (read-only, ghi nhận "chưa chạy" nếu bị chặn); xác nhận không có migration/write nào ngoài checkpoint.
- **Effort:** 4–6 ngày. **Blocker:** WS-04 phải merge trước khi bất kỳ lane nào chốt report.

### P2 — Security & exposure gates (4–6 ngày)

- **Mục tiêu:** đóng các open security gate (SEC-05/06/07 đã đóng ở P0 cho SEC-07), Discord scoping, repo hygiene, deployment verification đầu tiên.
- **Workstreams:** WS-06, WS-07 (quyết định topology trước), WS-10, một phần WS-11.
- **Entry gate:** P1 exit (log/redaction fields phục vụ verification) + OD-3/OD-4/OD-5 được trả lời.
- **Exit gate / acceptance evidence:** (a) SEC-05: test deterministic DNS/transport cho thấy connection được pin theo IP đã validate, giữ TLS SNI/Host, redirect validate ở connection boundary; fail-before/pass-after được ghi; (b) SEC-06: ADR topology được accept, cookie contract (HttpOnly/Secure/path/rotation/logout) + CSRF test cho mọi mutation + credentialed CORS exact origins + iframe PDF owner-auth test + rollback plan; (c) SEC-07: chứng minh suite không outbound khi thiếu key (mock transport fail nếu có call) và credentials bị clear; (d) Discord: privileged commands được scope owner-only hoặc deprecate sau flag, `apply`/`resume` không còn thiếu owner check, doc không claim "deprecated hoàn toàn" nếu chưa; (e) repo hygiene: rotation ledger (secret nào, khi nào, bởi ai), history scan report, quyết định rewrite theo OD-4; (f) deployment verification: `/health` DB-free, `/health/ready` là nơi duy nhất query DB, CORS exact origins, log/query-token redaction, no keep-alive polling.
- **Cannot claim done without:** file test mới `test_ssrf_transport_pinning.py` RED→GREEN; auth/CSRF/CORS tests; `npm --prefix frontend run build` + `npx tsc -b`; deployment evidence có timestamp + environment (không chứa secret trong output); `git diff --check`.
- **Effort:** 4–6 ngày. **Blocker:** OD-3 quyết định trước khi viết code SEC-06; OD-4 trước khi đụng git history.

### P3 — Verification closure & documentation truth (2–3 ngày)

- **Mục tiêu:** đóng quality debt ở mức gate (không mass-autofix), chạy hosted CI, đo coverage, thay toàn bộ pass-claim bằng evidence ledger.
- **Workstreams:** WS-09 (hoàn tất), WS-11 (final), WS-12.
- **Entry gate:** code freeze sau P2; mọi PR/commit của P1/P2 đã merge vào nhánh remediation.
- **Exit gate / acceptance evidence:** (a) GitHub-hosted CI run xanh với link/run-id; (b) coverage % được đo trên tree freeze + command; (c) style-lint delta so baseline ≤ 0 finding mới; (d) `npm audit --omit=dev` zero + dev findings được triage (không silently upgrade); (e) build/browser verification rerun (Compose frontend-build + serving check + browser QA nếu OD-7 cho phép); (f) `docs/FIX_PLAN.MD` + `OPEN_ISSUES.md` + `ROADMAP.MD` + `SECURITY_REMEDIATION_PLAN.md` được cập nhật trạng thái thật, mỗi claim trỏ command + output; (g) không còn câu "pass/verified/complete" không dẫn được bằng chứng.
- **Cannot claim done without:** full command set ở §6.4 chạy lại và ghi kết quả; `git diff --check`; evidence ledger đầy đủ row cho mỗi workstream; cross-check toàn bộ số pass-count trong docs mới.
- **Effort:** 2–3 ngày. **Blocker:** mọi lane khác phải đóng.

## 4. Parallelization matrix

Mỗi lane một owner; file/dir ghi dưới đây là **write scope** đề xuất (advisory, nhưng phải tách rời thực tế).

| Lane | Workstream | Write scope chính (owner duy nhất) | Song song an toàn với | Phải serialize với |
|---|---|---|---|---|
| A | WS-04 ingestion contract | `backend/app/services/ingestion_pipeline.py`, `backend/app/schemas/job.py`, `backend/app/api/v1/endpoints/jobs.py`, `backend/app/services/job_filters.py`, `backend/app/services/daily_runner.py`, `backend/tests/test_ingestion_pipeline.py` | B, C, D, F (chỉ đọc contract) | Mọi lane chốt report (B/C/D/E) — contract phải merge trước |
| B | WS-01 TopCV | `backend/app/services/collectors/topcv_adapter.py`, `backend/tests/test_topcv_blocked_reporting.py` (mới), `docs/colectors/0_topcv.md` | C, D, F, G | A (contract report); `test_collectors_regression.py` (owner khác) |
| C | WS-02 Saramin | `backend/app/services/collectors/saramin_adapter.py`, `backend/alembic/versions/009_rename_topdev_saramin.py`, `backend/tests/test_saramin_fields.py`, `docs/colectors/topdev.md` | B, D, F, H | A; DB migration execution phải qua Lead/ops |
| D | WS-03 ITNavi | `backend/app/services/collectors/itnavi_adapter.py`, `backend/tests/test_itnavi_full_scan.py` (mới) | B, C, F, H | A (metrics); `test_collectors_regression.py` (owner khác) |
| E | WS-05 market recensus | `backend/app/services/analytics/**`, `backend/tests/test_market_analytics.py`, `docs/MARKET_ANALYTICS.md` (chỉ phần evidence) | F, G, I (đọc DB read-only) | A, C (số liệu report); DB write phải chờ OD-2 |
| F | WS-06 SEC-05 | `backend/app/services/extraction/url_fetcher.py`, `backend/tests/test_ssrf_transport_pinning.py` (mới) | A, B, C, D, G, I | `detail_fetcher.py`/manual ingestion owner (chỉ đọc API); không sửa `main.py` |
| G | WS-07 SEC-06 | `frontend/src/api/client.ts`, `frontend/src/api/auth.api.ts`, `frontend/src/context/AuthContext.tsx`, `backend/app/api/v1/endpoints/auth.py`, `backend/app/core/security.py`, `backend/app/core/config.py`, `backend/app/main.py` (CORS owner), `backend/tests/test_jwt_and_secrets_security.py` | B, C, D, F | WS-11 topology; `main.py` không ai khác sửa |
| H | WS-08/WS-09 quality & CI | `backend/tests/conftest.py`, `.github/workflows/ci.yml`, `frontend/package.json`/`package-lock.json` (audit/coverage only, không upgrade khi chưa duyệt), `docs/testing/**` | B, C, D, E, I | G (nếu cần fixture auth); mọi lane (coverage đo sau freeze) |
| I | WS-10a Discord + WS-10b hygiene | `discord-bot/src/**`, `docs/DISCORD_BOT_DEPLOYMENT.md`; hygiene: git history/rotation (ops, không file) | A, B, C, D, E, F | WS-00 commit; OD-4 trước rewrite/history; `docker-compose.yml` không đổi nếu chưa duyệt |
| J | WS-11 deployment verification | Ops-only (Render/Supabase dashboard), `docs/testing/deployment-evidence.md` (evidence) | chạy sau G/H landing | G (cookie/CORS), I (rotation) |
| K | WS-12 docs truth | `docs/FIX_PLAN.MD`, `docs/OPEN_ISSUES.md`, `docs/ROADMAP.MD`, `docs/SECURITY_REMEDIATION_PLAN.md`, `tasks/**` | — (luôn cuối) | Tất cả; cấm lane khác sửa các file này song song |

**Xung đột phải chú ý:** `backend/tests/test_collectors_regression.py` hiện là file chung (đã có test cho TopCV/CareerLink/Saramin/GrowUpWork) — giao một owner duy nhất (đề xuất Lead hoặc lane C); các lane B/D thêm file test mới thay vì sửa file này. `backend/app/services/extraction/detail_fetcher.py` chỉ đọc, không lane nào được sửa khi F đang mở. `docker compose run frontend-build` + `restart backend` là thao tác dùng chung — chạy tuần tự, không chạy song song với DB migration.

## 5. Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Abort / rollback |
|---|---|---|---|---|---|
| R1 | Dirty working tree 155 tracked + 15 untracked bị trộn vào remediation; untracked Saramin/migration 009/CI biến mất | Gần chắc chắn | High | WS-00 gate: branch + checkpoint commit + tag/archive trước P1 | Không bắt đầu P1; giữ checkpoint tag; `git stash` chỉ sau khi đã commit/archive |
| R2 | Migration 009 production không chắc đúng (local-only evidence); recensus có thể đổi lịch sử | Medium | High | Dry-run trên bản sao staging/Supabase snapshot; đếm before/after; approval OD-2; migration forward-only (refuses unsafe downgrade) | Restore snapshot; không downgrade; nếu lệch số liệu, dừng và báo, không "sửa bằng tay" |
| R3 | Live-site access restrictions (TopCV 403/Cloudflare, ITNavi timeout) — invariant 19 | High | Medium | Không retry 403/429; ghi BLOCKED là dữ liệu; manual JD path; timeout budget hữu hạn | Dừng probe; ghi "blocked/chưa xác minh"; tuyệt đối không bypass |
| R4 | Cookie cross-site Pages/Render bị chặn third-party cookie | High | Medium | OD-3 chọn topology trước; same-site custom domain ưu tiên; test browser thật | Không half-migrate; revert về Bearer + risk acceptance ADR ghi rõ |
| R5 | Lint debt 2.207 findings gây scope creep / mass autofix phá diff | High | Medium | Baseline count có command; gate delta ≤ 0 finding mới; cấm mass autofix | Revert commit lint-only (không behavior change); giữ baseline file |
| R6 | Coverage measurement tốn thời gian/không cài pytest-cov | Medium | Low | Timebox 1 ngày, đo trên tree freeze; ghi "chưa đo + lý do" nếu thiếu tool | Không claim %, không nâng gate coverage khi chưa có số |
| R7 | Unverified historical evidence (306 passed, 2.207, 3 audit findings, deployment claims) | High | High | Rerun ở P0/P3 với dummy env; evidence ledger mỗi claim một row | Claim thiếu command+output bị downgrade thành "unverified" trong docs |
| R8 | Hệ quả từ 85 deletion (legacy frontend, topdev_adapter) làm gãy import hoặc test không lộ | Medium | High | Checkpoint làm deletion tường minh; `rg topdev_adapter`, `rg "frontend/js"`; chạy full pytest | Restore từ tag nếu có consumer chưa khai báo; không hồi sinh legacy frontend |
| R9 | SEC-06 dual-mode issuance (vừa cookie vừa JSON refresh) làm mất mục tiêu confidentiality | Medium | High | Gate ordering: cookie contract → CSRF → CORS → mới bỏ JSON refresh; test không còn token trong JS | Rollback về Bearer-only + risk acceptance; không để trạng thái nửa vời |
| R10 | Secrets/PII đã nằm trong git history; rotation chưa làm | Medium | High | Rotate trước (độc lập history rewrite), rồi scan; OD-4 quyết rewrite có backup | Nếu phát hiện lộ: rotate ngay, coi là incident dù không rewrite được; không force-push shared repo |
| R11 | Dev dependency upgrade từ npm audit làm gãy build/CI | Medium | Medium | Tách PR riêng, `npm ci` reproducible, không bundle upgrade vào fix | Revert `package-lock.json`; giữ 3 dev findings ở trạng thái triaged/deferred |
| R12 | Ingestion write/recensus làm hỏng lịch sử hoặc xoá synthetic rows | Medium | High | Read-only report trước; write chỉ sau OD-2 + backup; không xoá history mặc định | Restore snapshot; giữ synthetic rows và exclusion thay vì xoá |
| R13 | Parallel agents sửa trùng file làm mất thay đổi (FS_STALE hoặc overwrite) | Medium | High | Lane ownership ở §4; mỗi lane chỉ thêm file test mới; Lead review final diff | Rebase từ checkpoint; không silent overwrite; `git diff` review trước khi merge |

## 6. Evidence & reporting discipline

### 6.1 Definition of Done — checklist template (mỗi workstream/PR)

```
[ ] Diff đúng scope: liệt kê file đã đổi; không lẫn file ngoài lane.
[ ] RED trước GREEN: với bug fix, ghi lại test fail (command + output) trước khi sửa.
[ ] Rerun command + output: ngày, environment (OS/Python/Node), pass count.
[ ] Correctness lint: ruff --isolated --select E9,F63,F7,F82 (bắt buộc).
[ ] Style-lint delta: count mới so baseline, không tăng finding.
[ ] Full pytest dummy-env: pass count >= baseline; warning/failure mới phải giải thích.
[ ] Frontend: npx tsc -b + npm run build nếu có đổi frontend.
[ ] git diff --check pass.
[ ] Docs claim ↔ command mapping: mỗi câu "fixed/verified" có evidence row.
[ ] Không secret/PII trong output/log/evidence file.
[ ] Reviewer đối chiếu output thật, không chỉ đọc claim.
```

### 6.2 Evidence ledger — format bắt buộc

Mọi "done/fixed" trong `docs/FIX_PLAN.MD` phải có một row:

| ID | Claim | Command (đầy đủ) | Ngày + environment | Output quan sát (pass count / số liệu) | Verified by |
|---|---|---|---|---|---|
| EV-XXX | … | `…` | 2026-11-.. · Python 3.12 | `306 passed, 4 warnings` | Lead/reviewer |

**Quy tắc:** (a) không có row = trạng thái "unverified", không được viết "fixed"; (b) pass count lịch sử trong `ROADMAP.MD`/`IN_PROGRESS.MD`/`DONE.MD` không được dùng làm evidence hiện tại; (c) mọi số liệu live (fetched/unique) phải ghi rõ là quan sát tại thời điểm nào, không phải coverage guarantee; (d) nếu command không chạy được (ví dụ live probe bị chặn), ghi rõ "không chạy được + lý do", không suy diễn.

### 6.3 Quy tắc báo cáo

- "Đã sửa" chỉ dùng khi có diff + RED→GREEN + rerun output; "đã hoàn thành" chỉ dùng khi exit gate của milestone có evidence.
- Mọi so sánh số liệu phải nêu mốc tham chiếu (baseline commit/checkpoint hash).
- Docs truth (WS-12) chỉ được cập nhật sau khi các lane đóng; khi chưa chắc, viết "chưa xác minh" thay vì "pass".
- Không commit evidence chứa token thật, query token, hay PII ứng viên.

### 6.4 Command set chuẩn để rerun (từ `docs/OPEN_ISSUES.md §6` và repo)

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
npm --prefix frontend run build
cd frontend; npx tsc -b; cd ..
python scripts/check_frontend_serving.py            # sau docker compose run --rm frontend-build
npm --prefix frontend audit --omit=dev
```

Style-lint baseline (phải ghi rõ rule set + count, chưa được coi là gate cho đến khi đo lại):

```powershell
.\.venv\Scripts\ruff.exe check --isolated --output-format=json backend/app backend/tests scripts > lint-baseline.json
```

## 7. Open decisions cần human owner

| ID | Quyết định | Lựa chọn / recommendation | Cần trước |
|---|---|---|---|
| OD-1 | Xử lý working tree 155 file + 15 untracked | (a) commit checkpoint lên nhánh `remediation/2026-11-09` rồi tag (**recommended**); (b) tạo tag archive rồi mở nhánh mới; (c) stash-only (không recommended vì mất untracked risk) | P0 exit |
| OD-2 | Cho phép DB recensus/ingestion write + cách verify migration 009 trên production + chính sách xoá synthetic `growupwork-curated-*`/Upwork legacy | Read-only trước; write chỉ sau backup/snapshot; **không xoá history** mặc định (giữ exclusion); migration forward-only | P1 (read-only report) / P2 (write) |
| OD-3 | Cookie topology cho SEC-06 | Same-site custom domain hoặc same-origin proxy (**recommended**); cross-site `SameSite=None` chỉ sau browser test; hoặc chấp nhận localStorage risk có ADR | P2 SEC-06 |
| OD-4 | Có rewrite git history để purge secret/PII không | Rotate secrets trước; rewrite chỉ khi cần, có backup + xác nhận force-push; seed PII dùng bản anonymized nếu publish | P2 hygiene |
| OD-5 | Discord legacy: deprecate privileged commands hay giữ trusted/private | Ưu tiên owner-check toàn bộ + deprecate sau env flag; không claim deprecated khi code còn | P2 Discord |
| OD-6 | TopCV: bỏ source khỏi full-scan schedule hay giữ blocked-reporting | Giữ source + báo BLOCKED/partial + manual JD (**recommended**); chỉ bỏ khỏi `daily_runner.FULL_SCAN_SOURCES` nếu 403 lặp lại dài ngày | P1 TopCV |
| OD-7 | Mức verification cuối: có chạy GitHub-hosted CI thật + browser QA (CDP/Playwright) không, ai cấp evidence | Chạy hosted CI + browser QA tối thiểu 1 lần trên tree freeze (**recommended**) | P3 |
| OD-8 | Ai được truy cập Render/Supabase để làm deployment verification; evidence nào admissible | Chỉ owner/ops; evidence là output command + screenshot không chứa secret | P2/P3 |

**Chưa có OD nào ở trên được trả lời tại thời điểm lập roadmap này.** Mọi milestone liệt kê OD tương ứng là **blocked chờ quyết định**, không được tự chọn thay owner.

---

**Mapping nhanh milestone → workstream:** P0 = WS-00, WS-08, phần WS-09 · P1 = WS-04 → WS-01/02/03/05(read-only) · P2 = WS-06, WS-07, WS-10, phần WS-11 · P3 = WS-09(final), WS-11(final), WS-12.
**Liên kết:** chi tiết từng finding xem `security/FINDINGS.md`; limitation gốc xem `docs/OPEN_ISSUES.md`; gate security xem `docs/SECURITY_REMEDIATION_PLAN.md`; token migration xem `docs/TOKEN_STORAGE_MIGRATION_PLAN.md`.
