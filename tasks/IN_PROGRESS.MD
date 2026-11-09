# In Progress

## Source recovery, Vietnam market and discovery pagination (2026-11-09)

- Approved scope: replace TopDev with Saramin public IT API + source migration; recover CareerLink markup and ITNavi/GrowUpWork full scans. No WAF/CAPTCHA bypass; TopCV blocked access must surface as a failure, not a successful empty scan.
- Market scope includes ITViec, TopCV, Saramin, VietnamWorks, CareerLink, ITNavi and GrowUpWork (legacy TopDev retained until migration); excludes international/manual/mock sources. Charts precede tables with independent CSS columns; filters collapsed by default.
- Discovery uses an ACTIVE-only backend filter catalog, stable server pagination and 12 jobs per page. `scripts/check_collectors.py` is a read-only live probe (no database writes); fetched count is not the deduplicated ACTIVE count.
- Market tests: 21 passed; Jobs filter/pagination/blocked-source API: 7 passed (RED→GREEN recorded during implementation). Docker frontend build passed (1700 modules); local backend migration head is `009_rename_topdev_saramin`. Fixed direct `/market` SPA route (serving check RED→GREEN).
- Historical `growupwork-curated-*` synthetic fallback rows are excluded from Market without deleting history; collector no longer manufactures fallback jobs. Upwork's pre-existing synthetic fallback remains outside Market scope.
- `npm audit --omit=dev`: zero findings; full audit still reports 3 dev-tool findings (1 moderate, 2 high), deferred rather than silently upgrading build dependencies.
- Read-only live probe: CareerLink 415 unique records, GrowUpWork 800, Saramin 96 (coverage mismatch being investigated), ITNavi timed out at 240s, TopCV blocked. These are fetched records, not DB ingested/ACTIVE totals; no rescan written to the DB yet.
- Browser: Jobs 12/page + next + source-filter reset verified desktop/mobile; all 8 Market tabs loaded, no console/network failures. Mobile donut legend clipping fixed and rechecked with cache-disabled navigation: 305px client/scroll width, no card/document overflow.
- Verification snapshot (2026-11-09, previous execution): **306 passed, 4 warnings**; correctness-only Ruff passed. Saramin uses page_size=20: inspection of all 16 advertised pages yielded 96 unique IDs (later pages repeated); metadata total 319 is not a collection guarantee. ITNavi full-scan timeout remains unresolved despite page-level concurrency; listing-only counts do not prove successful detail collection. No commit or production deployment performed.
- Documentation review (2026-11-09): current blockers and evidence limits are in `docs/OPEN_ISSUES.md`. TopCV 200/403 observations do not establish a specific blocking cause or cooldown; robots.txt is not authorization to bypass restrictions. Backend suite rerun during this documentation review: **306 passed, 4 warnings in 46.62s** (Python 3.12). Correctness-only Ruff and Markdown relative-link checks passed. No new deployment/build/browser verification; coverage not measured.

## Compose frontend build (2026-11-09)

- `frontend-build` uses Node 22 and `npm ci && npm run build` before backend starts (`service_completed_successfully`). Linux node_modules stays in a named volume, separate from host dependencies; generated dist remains ignored.
- Verified regression RED→GREEN and real `docker compose up -d backend`: builder exit 0; localhost:8000 root serves React HTML, JS asset and /health all return 200.
- After UI changes, rebuild and reload backend with `docker compose run --rm frontend-build` then `docker compose restart backend`; `restart` alone does not rebuild dependencies.

## Audit remediation (2026-11-09)

- Compiler fails closed for absent binary/nonzero exit, removes invalid output, and requires a readable exactly-one-page PDF via existing `pypdf`. Regression RED: 5 failures; final compiler checks: 8 pass. Real local `pdflatex` smoke passed.
- CF IP precedes XFF; strong secrets required outside development; registration never elevates the first account and reserves the bootstrap admin email.
- Application preparation defaults to simulation (`READY`); actual submission is unsupported (501) until a transport exists. Explicit manual status updates track external submissions.
- Daily ingestion succeeds without a candidate, explicitly skipping matching/tailoring. Corrected stale authorization/test fixtures without weakening tenant checks.
- PR CI: pytest, correctness-only Ruff (`E9,F63,F7,F82`), `tsc -b`, Vite build and dist-serving check. Full style lint remains debt (2,207 existing findings); no mass auto-fix.
- Final local verification in test environment with strong CI-like secrets: **275 passed, 4 warnings**; frontend build/typecheck, correctness lint and `git diff --check` pass. GitHub-hosted CI and coverage percentage not yet verified.

## Legacy frontend cleanup (2026-11-09)

- Removed legacy `frontend/js`, `frontend/css`, `frontend/legacy`, generated dist/cache/tsbuildinfo outputs and the duplicate extracted-design ZIP; retained `frontendv2/Redesign` source and dependencies.
- FastAPI serves only built React `frontend/dist`, never Vite source/legacy files; missing build leaves API-only behavior. PDF ownership/auth unchanged.
- Checks: `python scripts/check_frontend_serving.py` and `npm run build` passed; regenerated outputs removed again after verification.

## Goal
Tiếp tục hoàn thiện các chốt chặn bảo mật nâng cao còn lại (SSRF DNS transport pinning `SEC-05`, cô lập test LLM `SEC-07`, lộ trình di chuyển Token sang HttpOnly Cookie `SEC-06`) và tiếp tục triển khai Phase 8 (Cloud Production Hardening: Supabase PostgreSQL pgvector, Upstash Redis Serverless, & Render Zero-Cost Deployment).

## Context
Các giai đoạn trọng yếu của hệ thống đã hoàn thành xuất sắc và được kiểm chứng toàn diện:
- **Phase 1 (Candidate Profile)**: Hồ sơ ứng viên chuẩn hóa, đồng bộ ngữ cảnh 2 chiều.
- **Phase 2 & 2.5 (Job Collection & Ad-hoc Ingestion)**: Thu thập đa nguồn tự động & nhập liệu thủ công URL/Text tức thì, deduplication 3 tầng, chuẩn hóa taxonomy.
- **Phase 3 (Job Intelligence)**: Hard filters 3 trạng thái, thuật toán tính điểm deterministic 7 tín hiệu, giải thích minh bạch.
- **Phase 4 & 4.5 & 6.2 (Evidence-Grounded Resume Tailoring Engine & Anti-Hallucination Refactor)**: Fact Graph & Evidence Registry, Canonical Technology Alias Registry, Gemini Semantic Writer (`gemini-3.6-flash`), ClaimLevelValidator (6-stage validation + Architectural Scope Shift protection), Deterministic Composer Fallback, Pure LaTeX Renderer.
- **Phase 5 & 6 (API Boundaries & Web Application Workspace)**: Kiến trúc Web-First (Simple Blue UI), phân quyền User 1-1 Candidate, Saved Jobs, Notification Service, tích hợp đầy đủ quy trình từ Job Discovery đến Dispatch.
- **Phase 8.1 & 8.2 (Cloudflare Pages Frontend & Render Backend Cloud-Ready)**: SPA routing `_redirects`, multi-tier dynamic `API_BASE` resolution, JIT PDF recompilation cho ephemeral storage của cloud container, idempotent retry safe.
- **Security Remediation (Phases 1, 2, 3 Hoàn thành & Xác thực 100%)**:
  - *Phase 1 (Tenant Isolation & Authorization)*: Đã vá hoàn toàn lỗ hổng BOLA/IDOR tại `/resumes/{id}/pdf` (`SEC-01`, hỗ trợ Bearer & Query token cho iframe), xóa bỏ lỗi chiếm đoạt candidate profile và xung đột email registration (`SEC-02`).
  - *Phase 2 (Authentication Hardening & Identity Boundaries)*: Loại bỏ cơ chế implicit masquerading `User 1` khi dùng `X-Internal-Secret` (`SEC-03`), định danh Service Principal tường minh, kiểm thử chặt chẽ vòng đời JWT (expired token, signature tampering).
  - *Phase 3 (Frontend Security & CORS)*: Gỡ bỏ wildcard regex `*.vercel.app` (`SEC-04`), whitelist nghiêm ngặt domain chỉ định; áp dụng `escapeHtml()` trong template string frontend chống DOM XSS; lập tài liệu kỹ thuật di chuyển token storage sang `HttpOnly` Cookie (`SEC-06`).
  - *Regression Test Suite*: 8/8 test bảo mật chuyên biệt pass (`test_phase1_authorization_regression.py`, `test_phase2_auth_hardening.py`, `test_phase3_cors_xss.py`).
- **Phase 9.1 (HOÀN THÀNH — 2026-11-06): Khôi phục 3 Design Theme từ Figma Make (`frontendv2/Redesign`)**:
  - **A. Modern Enterprise** (mặc định, light, phẳng, sidebar trắng, card 14px), **B. Liquid Glass** (light, `backdrop-filter: blur(26px) saturate(1.5)`, sidebar 24px, card 19px, ambient gradient), **C. AI Intelligence** (dark, `#080d1c`, card 12px gradient, glow, grid overlay 30px).
  - **Một component tree duy nhất, ba bộ token**: theme chỉ là CSS custom properties gắn qua `data-theme` trên `<html>`; không nhân bản component, không fork layout/content/business logic.
  - **Semantic migration (không phải CSS shim)**: thay toàn bộ `bg-white` / `bg-slate-*` / `text-slate-*` / tint trạng thái bằng token ngữ nghĩa (`bg-surface`, `border-border`, `text-text-muted`, `bg-success-50`…) trên ~28 file; Tailwind map `rgb(var(--*-rgb) / <alpha-value>)`.
  - **Chuyển theme runtime + không nháy**: `localStorage['jh_theme']`, script inline pre-hydration trong `index.html` set `data-theme` + `color-scheme` trước first paint; switcher A/B/C ở Topbar và mục "Giao diện" trong SystemPage.
  - **Typography bất biến**: DM Sans (body) / Manrope (display) giống hệt Figma ở cả 3 theme.
  - **Accessibility**: 4 giá trị Figma không đạt WCAG AA được nudge tối thiểu (A `--text-muted` `#697386`→`#677184`; B `--text-muted` `#607983`→`#586f79`, `--primary` `#087fba`→`#0772a7`), ghi chú inline trong `themes.css`; 28/28 cặp màu audit đạt ≥ 4.5:1.
  - **Bug thật đã vá trong quá trình verify**: overlay theme B bị tile do `background-size` hardcode (→ token `--page-overlay-size`); `Button` thiếu `whitespace-nowrap`; `Input`/`Select` wrapper thiếu `min-w-0`; `DialogHeader` thiếu `pr-14` (nút X đè badge); sidebar 244px làm nhãn "Hệ thống & Dữ liệu" + badge `Admin` tràn 1px (→ 252px); iframe PDF kế thừa `color-scheme: dark` (→ `.app-pdf-frame`); thanh accent `::after` ở nav item không có trong Figma và bị cắt thành nửa viên thuốc ở mép sidebar (→ gỡ bỏ); nhãn stat card Dashboard bị `truncate` 1 dòng (→ `line-clamp-2`); `ResumePage` nhận response không phải JSON (API base cấu hình sai) và render iframe với `undefined` trong URL (→ guard shape + toast lỗi rõ ràng).
  - **Ma trận xác minh**: 8 route × 3 theme + job-detail modal + mobile drawer, chuyển theme không reload, reload không nháy, 0 layout drift, 0 tràn ngang, 0 console error. `npm run build` xanh (1697 modules).
  - **Đã bị thay thế bởi Phase 9.3**: sản phẩm rút về một bản sắc Liquid Glass với 2 chế độ sáng/tối; theme A (Modern Enterprise) và C (AI Intelligence) đã bị xoá khỏi code. Phần còn giá trị là cơ chế: một component tree, token ngữ nghĩa, `themes.css` làm nguồn duy nhất, script pre-hydration chống nháy.
- **Phase 9.2 (HOÀN THÀNH — 2026-11-06): Tối ưu hiệu năng Liquid Glass (giữ nguyên bản sắc thiết kế)** — chi tiết tại `docs/DECISIONS.MD` ADR-014:
  - **Đo trước khi sửa**: harness CDP (`perf.mjs`, 4 route × 3 theme, fixture 60 job, 1440×900). Theme Glass `/jobs` đạt **113.2 ms/frame avg, p95 176.4 ms, 81 frame rơi** (≈8 fps) trong khi Enterprise/AI chỉ 16–18 ms → nguyên nhân quy về `backdrop-filter`, không phải DOM/data.
  - **Xác định mô hình chi phí**: quét biến thể blur trên `/jobs` cho thấy bán kính blur gần như miễn phí, chi phí nằm ở **mỗi surface phải đọc lại backdrop (~20 ms/frame)**: hiện tại 37.3 ms → giảm nửa bán kính 34.4 ms → bỏ hẳn backdrop 16.6 ms.
  - **Cắt blur trên bề mặt dữ liệu**: `--card-blur: none` cho Glass (62 element backdrop-filter trên `/jobs` → 0), giữ cảm giác kính bằng gradient chuyển sắc `rgba(255,255,255,.82→.62)` + viền sáng + inset highlight.
  - **Cắt blur trên navigation**: sidebar/topbar/hero nằm trên nền gradient tĩnh vốn đã mịn → blur gần như vô hình nhưng tốn ~20 ms/frame; giữ độ trong suốt (`rgba(240,250,252,.66)` / `rgba(238,249,251,.55)`) + viền sáng. Enterprise/AI cũng bỏ `--topbar-blur` (~95% đục) và thêm `--hero-blur: none`.
  - **Blur chỉ còn ở overlay thật**: dialog/sheet scrim giữ `backdrop-blur-[2px]` — nơi nội dung thực sự trôi phía sau và bán kính nhỏ rất rẻ.
  - **Ambient blob**: bỏ `filter: blur(90px)` trên 2 layer lớn (bị re-blur mỗi lần repaint) → `radial-gradient(... transparent 78%)`, kích thước 760/640px, chi phí filter = 0.
  - **Transition theo thuộc tính + cô lập paint**: `.app-card` chỉ transition `border-color`/`background-color` (bỏ `box-shadow`/`border-radius`/`transform` gây re-raster toàn bộ card khi hover và khi đổi theme) + `contain: paint`; gỡ `transition-all` ở `JobCard`, `Card` hoverable, row Dashboard/Resume/Recommendations, Toast, Sidebar, Tabs, thanh tiến trình JobDetailModal.
  - **Chặn transition ở first paint**: `html:not(.theme-transitions) * { transition: none !important }` + `ThemeContext` thêm class trong `requestAnimationFrame` → hết hiện tượng fade nền 350 ms mỗi lần load (reload AI giờ settle ngay `rgb(8,13,28)` ở 400 ms).
  - **React**: `JobCard` bọc `React.memo` (+ `displayName`); handler `onOpenJobDetail` đã là `useCallback` ổn định nên memo có hiệu lực; bỏ `text-rendering: optimizeLegibility`.
  - **Suy giảm mềm**: `prefers-reduced-motion` ẩn ambient layer; `prefers-reduced-transparency` ép surface đặc; dưới 1024px bỏ toàn bộ backdrop-filter (GPU mobile trả giá cao nhất).
  - **Kết quả đo lại** (5 pass stability, median): Glass `/jobs` **16.6 ms** (min 16.54 / max 17.65), p95 176.4 → 18–23 ms, frame rơi 81 → 0–2; Glass dashboard 95.0 → 15.1 ms; applications 27.6 → 9.75 ms; cả 3 theme (bấy giờ) đều 15–17 ms (60 fps). Số element có backdrop-filter: 62 → 0.
  - **Không hồi quy thị giác**: ảnh matrix trước/sau gần như trùng khớp (sidebar tint cyan, ambient glow, card kính trong); contrast 9/9 cặp văn bản/bề mặt mới ≥ 4.5:1 (worst-case trên stop tối nhất của canvas). `npm run build` xanh.
- **Phase 9.3 (HOÀN THÀNH — 2026-11-07): Rút gọn Appearance về 2 chế độ Liquid Glass (Sáng mặc định + Tối đầy đủ)** — chi tiết tại `docs/DECISIONS.MD` ADR-015:
  - **Xoá theme A & C**: `ThemeId = 'light' | 'dark'`; `data-theme` chỉ còn `glass` (`:root`, mặc định) và `glass-dark`. Toàn bộ token của Modern Enterprise và AI Intelligence bị xoá khỏi `themes.css`, không chỉ ẩn.
  - **Dark là đảo token của cùng một bản sắc**: giữ nguyên cặp accent azure/cyan + violet, radius card 19px / sidebar 24px, cùng thang elevation và các class treatment; không component nào rẽ nhánh theo mode.
  - **Giữ nguyên ngân sách blur ADR-014**: `--card-blur` / `--sidebar-blur` / `--topbar-blur` / `--hero-blur` vẫn `none` ở **cả hai** mode; chất kính đến từ gradient trong suốt + viền sáng 1px + inset highlight (dark dùng hairline trắng 14%).
  - **Surface tối gần đặc ở nơi cần đọc**: `--surface` = `rgb(18 32 46 / 0.9)` để dialog/sheet/toast/bảng/form luôn đọc được; card vẫn giữ gradient trong suốt vì nằm trên canvas.
  - **Token `--scrim` mới** (`light rgba(15,23,42,.38)` / `dark rgba(2,8,16,.72)`) thay `bg-overlay/40` cho overlay dialog/sheet — scrim 40% gần đen gần như không làm tối trang dark.
  - **Scale màu ngữ nghĩa đảo ở dark** (`*-50` = nền tint đậm nhất, `*-600/700` = chữ sáng) để giữ nguyên vocabulary `bg-primary-50 text-primary-700`.
  - **Lưu trữ + theo OS + không nháy**: `localStorage['jh_theme']` (`light`|`dark`) thắng; nếu chưa có thì theo `prefers-color-scheme` và chỉ cập nhật live khi người dùng chưa chọn. Giá trị cũ migrate im lặng: `glass`/`enterprise` → `light`, `ai` → `dark`. Script pre-paint trong `index.html` áp `data-theme` + `color-scheme` trước first paint.
  - **Một toggle icon-only**: button `role="switch"` 58×34, icon Sun/Moon, thumb trượt `translateX(24px)` ở dark, transition transform 200 ms, tắt dưới `prefers-reduced-motion`; không tên theme, không mô tả trong header. SystemPage hiển thị trạng thái "Liquid Glass Sáng/Tối" + toggle.
  - **Kết quả xác minh**: 8 route × 2 mode, 0 layout drift, 0 tràn ngang, 0 console error; toggle runtime đổi `glass` ⇄ `glass-dark`, persist `light`/`dark`, `textContent: ''`, 2 icon / 1 button; reload không nháy tại 400 ms = `glass-dark` / `rgb(8, 18, 30)`; mobile 390×844 toggle hiển thị 58×34 tại x=265, topbar 62px, không tràn.
  - **Hiệu năng**: light 16.65 / 16.47 / 12.80 ms, dark 16.58 / 15.64 / 16.45 ms (`/jobs`, `/`, `/applications`), backdrop-filter **0**, frame rơi 0; đổi theme 43.6 ms → dark và 58.4 ms → light (2–3 frame).
  - **Contrast**: 28/28 cặp trong phạm vi ≥ 4.5:1 (dark card muted 5.80, sidebar muted 6.03, dialog muted 6.16, nav active 6.97, chips 8.69–10.94). Ghi nhận ngoài phạm vi: chữ trắng trên gradient nút primary = 3.54:1 — gradient Figma có sẵn, giống nhau ở cả 2 mode, không tự ý đổi.
  - **CSS giảm 53.4 → 49.2 kB** dù thêm dark mode, nhờ xoá 2 bộ token. `npm run build` xanh (1697 modules, CSS 49.23 kB / JS 397.67 kB).

## Phase 9.4 — Vietnam IT Labor Market Analytics Platform (IN PROGRESS)

**Goal:** mở rộng module Market Intelligence thành 8 tab phân tích thị trường IT Việt Nam trên dữ liệu aggregate thật từ PostgreSQL, không tạo nguồn dữ liệu song song và không bịa số liệu.

**Backend**
- `backend/app/services/analytics/` tách thành lõi dùng chung: `MarketFilters` + `JobFact` loader, taxonomy suy ra (category/region/role family), percentile/FX/coverage, time buckets.
- Module mới: `overview`, `hiring_trends`, `salary_intelligence`, `skills_intelligence`, `role_intelligence`, `geography_intelligence`, `employer_intelligence`, `insight_engine`, `catalog`.
- Endpoints `/api/v1/market`: `filters`, `overview`, `hiring-trends`, `salaries`, `skills`, `roles`, `geography`, `employers`, `insights`; giữ `/analytics` tương thích.
- Mọi response có `meta` (`sample_size`, `total_jobs`, `coverage`, `status`, `notes`) để phân biệt `ok` / `insufficient` / `empty` / `unavailable`.
- Loại `MERGED`; mặc định `ACTIVE`, tùy chọn gồm `EXPIRED`. Hoãn index/migration cho đến khi profiling trên dữ liệu lớn chứng minh cần thiết (~1.500 tin hiện tại).

**Frontend**
- `MarketPage.tsx` thành shell: PageHeader + filter bar dùng chung + 8 tab + nội dung tab.
- `frontend/src/pages/market/` chứa 8 tab module; `frontend/src/components/market/` chứa chart SVG thuần (line/area, bar, histogram, donut, sparkline, heatmap), status/coverage notice, stat card.
- Hook `useMarketQuery` có abort + cache state; tab không active unmount; filter/drill-down dùng chung.
- Thứ tự triển khai: Hiring Trends → Salary → Skills → Overview → Roles → Geography → Employers → Insights.

**Verification so far (2026-11-07)**
- Backend isolated market + health + job-model + normalizer checks: 24 passed; no external AI calls.
- Frontend: all 8 tabs implemented in existing Market route; `npm run build` passed (1700 modules), `node scripts/check-market.mjs` passed (API encoding/abort options + eight empty-state panels).
- No new dependencies, migrations or polling. Cache deferred; requests are abortable and stale-response guarded. Browser visual/interaction QA remains a release follow-up.
- Read-only configured PostgreSQL smoke: 9 new endpoints returned 200 over 1,505 active records; salaries correctly `insufficient`.
- Invalid salary regression RED: 5 failures (NaN/infinity/negative/reversed/zero) → GREEN after validation.
- Methodology and reproducible checks: `docs/MARKET_ANALYTICS.md`.
- Full-suite coverage and visual browser verification are not yet claimed.

**Market UI refinement (2026-11-07)**
- Dark mode: Dracula-inspired charcoal/slate with cyan/violet accents; light mode and zero-blur performance budget preserved.
- Shared filters condensed to dates/category/location; advanced filters remain accessible and active filters removable. Tab names localized.
- KPI hierarchy and concise expandable methodology updated; line chart with axes/peak, salary histogram and source donut supplement ranking bars. `npm run build` and `node scripts/check-market.mjs` passed (empty/populated charts, zero bins, true donut proportions). Browser visual QA still pending.

**Data honesty rules**
- Lương chỉ thống kê trên tin có `salary_currency` VND/USD; USD quy đổi VND theo `MARKET_USD_TO_VND` và gắn nhãn `estimated`.
- Category/vùng là suy ra từ `normalized_title` / `normalized_location`, gắn nhãn derived.
- Phát hiện spike `posted_at` (bulk backfill) và hiển thị caveat, không làm mượt.
- Insights là quan sát tất định, không phải dự báo; không dùng LLM sinh số.

## Relevant Files
- `backend/app/api/v1/endpoints/resumes.py` (Vá BOLA PDF & Query Token Auth)
- `backend/app/api/v1/endpoints/auth.py` & `backend/app/repositories/candidate.py` (Vá Candidate Stealing & Race Condition)
- `backend/app/core/security.py` (Service Principal cách ly & Token Verification)
- `backend/app/main.py` (CORS domain whitelist)
- `frontend/src/` (React/TypeScript UI; legacy vanilla JS removed)
- `security/REVIEW_BASELINE.md` & `security/FINDINGS.md` (Hồ sơ kiểm toán & trạng thái lỗ hổng)
- `backend/tests/test_phase1_authorization_regression.py`
- `backend/tests/test_phase2_auth_hardening.py`
- `backend/tests/test_phase3_cors_xss.py`
- `docs/AUTHENTICATION_AND_JWT.md` & `MIGRATION_PLAN.md`
- `frontend/src/styles/themes.css` (Nguồn chân lý duy nhất cho 2 bộ token Liquid Glass Light/Dark + treatment classes)
- `frontend/tailwind.config.js` (Map token ngữ nghĩa → CSS vars, `scrim`, DM Sans/Manrope)
- `frontend/src/theme/` (`tokens.ts` mode model + legacy migration, `ThemeContext.tsx` persistence/OS-follow, `ThemeSwitcher.tsx` Sun/Moon switch)
- `frontend/index.html` (script pre-paint chống nháy theme, `data-theme="glass"` mặc định)
- `frontend/src/components/layout/` (`AppShell.tsx`, `Sidebar.tsx`, `Topbar.tsx`)
- `frontend/src/pages/SystemPage.tsx` (SECTION 0 "Giao diện" hiển thị mode + toggle)
- `frontend/src/theme/ThemeContext.tsx` (gate `.theme-transitions` chống fade ở first paint)
- `frontend/src/components/ui/dialog.tsx` & `sheet.tsx` (overlay dùng `bg-scrim`)
- `frontend/src/components/jobs/JobCard.tsx` (`React.memo` + bỏ `transition-all`)
- `frontend/src/components/ui/card.tsx`, `tabs.tsx`, `context/ToastContext.tsx`, `components/layout/Sidebar.tsx` (transition theo thuộc tính)

## Next Steps
1. **SEC-05 SSRF Defense Hardening**: Bổ sung transport IP pinning cho `URLFetcher` để triệt tiêu cửa sổ Time-Of-Check to Time-Of-Use (TOCTOU) DNS rebinding.
2. **SEC-07 Test Suite Hygiene**: Mock hoàn toàn các network call tới Gemini API trong test suite để tránh timeout 429 và leak credential.
3. **Triển khai di chuyển Token sang HttpOnly Cookie** theo lộ trình đã lập tại `MIGRATION_PLAN.md`.
4. Tiếp tục hoàn thiện Phase 8.2 / 8.4 trên môi trường Cloud Production.
5. **Phase 2.7 (HOÀN THÀNH — 2026-11-04)**: Detail Page Enrichment cho Ingestion Pipeline (JSON-LD + DOM + richer-record merge, 27 tests pass) — chi tiết tại `docs/INGESTION_HARDENING.md`.
6. **Phase 2.8 (HOÀN THÀNH — 2026-11-04)**: Full Unexpired Scanning & Expiry Detection cho 5 nền tảng VN (ITViec, TopCV, TopDev, VietnamWorks, CareerLink) — `full_scan`, smart stop, `EXPIRED` status, `expire_outdated_jobs`, 18 tests pass.
7. **Phase 2.9 candidate — Expiry UX**: Ẩn job `EXPIRED` khỏi danh sách mặc định (toggle "Hiện tin đã hết hạn"), widget "tin sắp hết hạn trong 3 ngày" trên Dashboard.
8. Phase 2.9 candidate: Taxonomy 4 chiều (title/seniority/location/work-model) cho UI filter & scoring.
9. **Phase 9.1 (HOÀN THÀNH — 2026-11-06, ĐÃ BỊ THAY THẾ bởi Phase 9.3)**: Khôi phục 3 theme thiết kế Figma Make (A Modern Enterprise / B Liquid Glass / C AI Intelligence) — chi tiết tại `docs/DECISIONS.MD` ADR-013. Theme A & C đã bị xoá khỏi code.
10. **Phase 9.2 (HOÀN THÀNH — 2026-11-06)**: Tối ưu hiệu năng Liquid Glass — Glass `/jobs` 113.2 ms → 16.6 ms/frame (frame rơi 81 → 0), backdrop-filter 62 → 0 element, giữ nguyên bản sắc thị giác; chi tiết tại `docs/DECISIONS.MD` ADR-014.
11. **Phase 9.3 (HOÀN THÀNH — 2026-11-07)**: Rút gọn appearance về 2 chế độ Liquid Glass (Sáng mặc định + Tối), toggle Sun/Moon icon-only, theo OS khi chưa chọn, migrate giá trị `jh_theme` cũ, không nháy khi reload; chi tiết tại `docs/DECISIONS.MD` ADR-015.
12. **Phase 9.3 follow-up (tùy chọn)**: Commit toàn bộ thay đổi appearance + tối ưu hiệu năng (đang uncommitted trong `frontend/`), thêm script benchmark `perf.mjs` vào `frontend/scripts/` để chặn hồi quy blur trong CI.
