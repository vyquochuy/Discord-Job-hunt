# Market analytics

Eight tabs remain inside the existing Market route; Dashboard, ingestion and personal matching are unchanged.

## Data and API

Public, read-only endpoints under `/api/v1/market`: `filters`, `overview`, `hiring-trends`, `salaries`, `skills`, `roles`, `geography`, `employers`, `insights`. `/analytics` remains compatible.

All modules read existing `jobs`, `raw_jobs`, `job_skills` and `skills`. SQL source scope is ITViec, TopCV, Saramin, VietnamWorks, CareerLink, ITNavi and GrowUpWork, plus legacy `topdev` rows for migration compatibility (`MARKET_SOURCES` in `services/analytics/filters.py`). Saramin replaces the historical TopDev collector; migration `009_rename_topdev_saramin` handles source data. Remotive, Upwork, manual and mock are excluded, as are historical synthetic `growupwork-curated-*` source IDs. Jobs discovery remains multi-source and is not the Market dataset. Default scope is ACTIVE; `include_expired=true` also includes EXPIRED; MERGED is always excluded. No separate data store, LLM numbers, forecast or polling loop.

Shared query parameters: `date_from`, `date_to` (inclusive UTC posting dates), `category`, `level`, `location`, `region`, `source`, `work_mode`, `skill`, `company`, `include_expired`. Categories and coarse regions are lexical derivations, not employer-declared classifications. Unknown titles remain Other. Seniority/work mode retain ingestion's inference limitations.

Each response includes `meta`: generation timestamp, applied filters, total jobs, usable sample, coverage, status and caveats. Empty results are not network failures. Low coverage/sample is explicitly insufficient. Counts describe collected listings, not unique vacancies or all Vietnam hiring.

## Interpretation limits

- Posting timestamps may reflect fallback/backfill. Spike detection marks *possible* bulk imports; it cannot establish cause. Zero bars mean no observed listings in that bucket, not zero market demand. ACTIVE-only historical charts have survivorship bias.
- Salary uses advertised range midpoint, or the available bound for one-sided ranges. The source schema does **not** preserve monthly/yearly/hourly cadence, gross/net or bonuses. Do not label these as monthly wages or comparable compensation. Native currencies remain visible; USD conversion uses `MARKET_USD_TO_VND` (default 26000, configurable, not a live quote) and is estimated. Invalid/non-finite/non-positive/reversed ranges are excluded.
- Skill shares use jobs with linked skills as denominator; co-occurrence is association, not causation. Two-half comparisons describe sample composition and can be distorted by backfill.
- Company identity uses existing normalized names, not a verified company registry. Earliest observation in a filtered window cannot establish a genuinely new employer.
- AI Market Insights is explicitly deterministic rules, not generative AI or prediction.

## Verification

`cd backend` then `python -m pytest tests/test_market_analytics.py tests/test_health.py tests/test_job_models.py -q`.

`python scripts/check_market_analytics.py` performs read-only smoke requests against the configured database, without printing credentials. Run only against a database you intend to query.

`cd frontend` then `npm run build`.

Current implementation loads compact facts and aggregates in Python (no descriptions/embeddings). At substantially larger datasets, move aggregations into SQL/materialized aggregates after profiling; no speculative cache infrastructure or schema migration is required without assuming a fixed current row count.

### Test evidence

Salary-invalidity regressions were executed before fixing the helper: 5 failed (NaN, infinity, negative, reversed, zero ranges). The same target passed after validation was added. Endpoint tests cover empty/populated datasets, ACTIVE/EXPIRED/MERGED scopes, currency conversion, filter validation, inclusive dates and legacy compatibility. No claim of full-suite coverage or browser QA is made by these checks.
