# Source recovery and discovery verification — 2026-11-09

Scope derived from the approved conversation plan; no checkpoint commits created because the working tree already contains uncommitted audit remediation. This is a **historical implementation/probe record**, not a current test rerun, upstream availability promise, or full-source coverage guarantee. Documentation audit on 2026-11-09 read local source only; no live requests.

| Behavior checked at implementation time | Check | Historical evidence |
|---|---|---|
| Market excludes international/manual/mock and historical synthetic GrowUpWork records, including legacy aggregate queries | `pytest tests/test_market_analytics.py -q` | New exclusions RED, 21 GREEN |
| Public ACTIVE-only filter catalog, UNKNOWN filtering, stable pagination | `pytest tests/test_jobs_filters_pagination.py -q` | 4 RED, 4 GREEN initially |
| TopCV access restriction is a safe 502, unrelated errors are not masked | Same Jobs tests | 1 RED, final 7 GREEN |
| Direct Market deep links serve built React | `python scripts/check_frontend_serving.py` | Missing route assertion RED; added route GREEN |
| Saramin pagination/URL validation, nonpositive full-scan limits, repeat-page stop, current CareerLink markup and blocked-source reporting | `pytest tests/test_collectors_regression.py tests/test_saramin_fields.py tests/test_growupwork_public_data.py -q` | RED observed during implementation; final full suite 306 GREEN, including these regressions |
| Jobs renders 12/page, next page changes IDs, source filter resets page | Local Chrome CDP, desktop 1440x900 and mobile 375x812 | PASS against live local API; 12 cards on pages 1/2, 5 after GrowUpWork filter |
| Market tabs, default collapsed filters | Same CDP run, 8 tabs x 2 sizes | PASS; mobile donut clipping reproduced then CSS fix verified: legend clientWidth=scrollWidth=305 at375px, no document/card overflow |

Build: Docker `frontend-build` (`npm ci && npm run build`) passed, 1700 modules. Ruff correctness (`E9,F63,F7,F82`) and `git diff --check` passed during integration. Final full suite after collector edits stopped: **306 passed, 4 warnings** (33.86s); preceding transient runs during parallel edits are superseded.

Local Alembic head: `009_rename_topdev_saramin`. Migration retains historical URLs/payloads, rejects conflicting IDs without merging/deleting, and deliberately refuses unsafe downgrade (cannot distinguish newly ingested Saramin records from renamed history).

Read-only live probe (`python scripts/check_collectors.py`) does not ingest database records. First run: CareerLink415, GrowUpWork800, Saramin96, ITNavi timeout240s (unresolved), TopCV blocked. Final Saramin adapter uses page_size20; independent inspection of all16 advertised API pages also found96 unique IDs despite metadata total319: pages1–4 added20 each, page5 added16, pages6–16 added none. Duplicate-stop is retained; upstream completeness is not claimed. Counts are observations, not completeness guarantees. Existing local curated records are not deleted. No production deployment, hosted CI execution, coverage percentage or visual-baseline comparison verified.

## Current source constraints (not live-verified)

- Saramin uses IT-category public API, page_size20, cap200 pages and stops at last_page, empty data or no new valid IDs. Migration renames legacy source labels, not historical payloads/URLs into newly fetched API records.
- ITNavi `limit <= 0` caps at **50 pages**; positive limits use `min(25, ceil(limit/10))`. Listings are sequential; per-page card AJAX uses `asyncio.gather` without a semaphore. Listing timeout10s/connect5s retries timeout once; AJAX timeout5s. There is no 240s collector-wide deadline or completion guarantee.
- GrowUpWork full scan caps at80 pages, positive scan at `min(25, ceil(limit/20))`; embedded JSON is preferred over DOM. It no longer manufactures synthetic jobs. Historical curated rows remain stored but excluded from Market; Upwork still has a separate pre-existing synthetic fallback outside Vietnam Market scope.
- TopCV recognized listing restrictions raise BLOCKED and get API502. CareerLink also raises on recognized restrictions but has no dedicated API502 mapping. Detail enrichment BLOCKED is different: it records failure metadata and retains listing data. Other collectors can return partial/empty data after logging errors; tests do not establish uniform blocked reporting for every source.
- Pipeline full_scan disables the unchanged streak and passes limit0; it does not remove adapter page caps, timeouts, expired-streak heuristics or upstream access restrictions. Fetch count is not deduplicated ingestion/ACTIVE count.

Historical security dependency check: `npm audit --omit=dev` zero findings; full audit reports 3 existing dev-tool findings (1 moderate,2 high). No dependency upgrades bundled into this task.
