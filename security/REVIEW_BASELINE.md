# Security Review Baseline — Job-Hunt Platform

**Date:** 2026-10-06  
**Auditor:** Senior Application Security Engineer & Backend Security Reviewer  
**Status:** Remediated & Verified (Phases 1–3 Complete)  
**Target Codebase:** `c:\Game\Job-Hunt` (Branch: `main`)

---

## 1. Project Overview & System Identity

Job-Hunt is an AI-assisted job hunting intelligence and resume tailoring platform.
- **Frontend:** Modular Vanilla ES6 Single Page Application (`frontend/`) using Simple Blue design system, hash routing (`core/router.js`), reactive state management (`core/store.js`), and centralized HTTP client (`api/client.js`).
- **Backend:** FastAPI REST API (`backend/app/`) running on Python 3.12 with async route handlers.
- **Persistence:** PostgreSQL 16 with `pgvector` extension for vector embeddings, managed via SQLAlchemy 2.0 (asyncpg) and Alembic migrations.
- **Cache & Queue:** Redis 7 for workers and rate-limiting counters.
- **Document & AI Processing:** Gemini REST API (`gemini-3.7-flash` / `gemini-3.6-flash`), local `pdflatex` compilation with sandbox flags, ATS 1-page pure LaTeX templates, claim-level anti-hallucination verification.

---

## 2. Trust Boundaries & Threat Actors

| Actor | Identification Mechanism | Trust Level | Permitted Scope |
| :--- | :--- | :--- | :--- |
| **Guest / Anonymous User** | None (No credentials) | Untrusted | Read-only job exploration (`GET /jobs`, `/jobs/{id}`, `/jobs/taxonomy/skills`), liveness checks (`/health`), registration/login. |
| **Authenticated Candidate** | Bearer JWT (`type: "access"`, 30m TTL) | Semi-Trusted (Tenant) | CRUD on own profile (`/profile`), matching against own profile (`/matches`), saving own jobs (`/jobs/saved`), tailoring resumes (`/resumes/tailor`), tracking own applications (`/applications`). |
| **Superuser / Admin** | Bearer JWT with `user.is_superuser == True` | High Trust | Administrative operations, system maintenance, viewing global application metrics. |
| **Internal Service / Adapter** | `X-Internal-Secret` HTTP Header | High Trust (Service-to-Service) | System operations, trigger batch collections, trigger batch matching. |
| **External Web / JD Sources** | Web scraping & Manual Ingest URLs | Untrusted / Hostile | Parsed for text content only; must never execute code or influence system instructions. |

---

## 3. Resource Ownership Matrix

| Resource Model | Primary Key | Owner Association | Anti-IDOR Enforcement Status | Observed Status in Code |
| :--- | :--- | :--- | :--- | :--- |
| `User` | UUID (`users.id`) | Self | Own record via JWT `sub` claim. | Enforced in `/auth/me`. |
| `Candidate` | UUID (`candidates.id`) | `user_id` (1-1 with `users.id`) | Resolved via `CandidateRepository.get_profile_by_user`. | **Enforced**. Unassigned profile stealing removed; strict 1-1 creation on register. |
| `CandidateSkill / Project` | UUID | Cascaded to `Candidate.id` | Resolved via `Candidate.id`. | Enforced. |
| `Job` | UUID (`jobs.id`) | Global (Public catalog) | Publicly viewable. Mutations restricted to admin/internal. | Enforced. |
| `JobMatch` | UUID (`job_matches.id`) | `candidate_id` | Resolved via `current_user`'s candidate. | Enforced. |
| `TailoredResume` | UUID (`tailored_resumes.id`)| `candidate_id` | Checked via `verify_resume_ownership` in all routes. | **Enforced** in `/resumes/{id}/pdf` via Bearer or Query param token. |
| `SavedJob` | UUID (`saved_jobs.id`) | `user_id` | Enforced by `user_id == current_user.id` in query. | Enforced. |
| `ApplicationLog` | UUID (`application_logs.id`)| `candidate_id` | Enforced by `candidate_id` filter unless superuser. | Enforced. |
| `RefreshToken` | UUID (`refresh_tokens.id`) | `user_id` | Verified by hash and `stored_token.user_id == user_id`. | Enforced. |

---

## 4. Key Security Entry Points & Interfaces

### 4.1 Authentication & Credential Verification
- `POST /api/v1/auth/register`: User creation, candidate profile assignment, Argon2id hashing, dual-token issuance.
- `POST /api/v1/auth/login`: Argon2id verification, transparent rehash on legacy PBKDF2 hashes, token pair issuance.
- `POST /api/v1/auth/refresh`: Atomic row-locking (`with_for_update`), Refresh Token Rotation (RTR), Token Family Revocation (TFR), 15s grace period idempotency.
- `POST /api/v1/auth/logout`: Revocation of refresh token.
- `app/core/security.py`: `get_current_user`, `get_current_user_optional`, `get_authenticated_user_or_internal`, `verify_admin_access`.

### 4.2 Document Generation & File Handling
- `POST /api/v1/resumes/tailor/{job_id}`: AI extraction, prompt generation, JSON schema validation, unit regeneration, LaTeX rendering, `pdflatex` compilation.
- `GET /api/v1/resumes/{id}/pdf`: Publicly accessible PDF delivery with capability UUID, JIT PDF recompilation.
- `POST /api/v1/profile/upload-resume`: Multipart upload (.pdf, .tex, .yaml, .md, .json), streaming chunked memory bounds (10MB limit).
- `app/services/tailoring/latex_compiler.py`: Invocation of `pdflatex` binary with `-no-shell-escape` sandbox parameter and 30s timeout.

### 4.3 Outbound Network Access & Ingestion
- `POST /api/v1/jobs/ingest-manual`: URL and raw text input.
- `app/services/extraction/url_fetcher.py`: `is_safe_public_url` DNS pre-resolution against private/loopback/link-local/cloud metadata IPs, `httpx` async fetch with redirect event hook.
- 10 Collector adapters: Scraping TopCV, ITViec, VietnamWorks, Upwork RSS, etc.

### 4.4 Browser Security & Headers
- CORS middleware in `app/main.py`: Whitelisted domains from `ALLOWED_CORS_ORIGINS` + regex `r"^https://[a-zA-Z0-9_-]+\.vercel\.app$"`.
- Cache-Control middleware: `no-cache, no-store, must-revalidate` on static assets and HTML.
- Client token storage: Tokens stored in browser `localStorage`.

---

## 5. Baseline Test Suite Execution & Observations

A full test run of the existing backend test suite was executed using `.venv\Scripts\python.exe -m pytest backend/tests`:
- **Total Tests:** 167 collected
- **Passed:** 164
- **Failed:** 3
- **Execution Time:** 436.61s (7m 16s)

### Key Test Findings & Failures Observed:
1. **`FAILED backend/tests/test_multi_user_isolation.py::test_multi_user_resume_and_file_sandbox_isolation`**:
   - Specifically failed at line 195: `res_malicious_pdf = await client.get(f"/api/v1/resumes/{resume_a_id}/pdf", headers=headers_b)`
   - Expected status: `404 Not Found`
   - Observed status: `200 OK`
   - **Root Cause Verified:** `GET /api/v1/resumes/{id}/pdf` does not verify user ownership; Bob successfully downloaded Alice's resume PDF.
2. **`FAILED backend/tests/test_daily_batch.py::test_daily_batch_runner_execution` & `test_daily_batch_api_endpoint`**:
   - `daily_runner.py` called `CandidateRepository.get_profile(session)` which assumes a single global candidate exists in database. In an isolated test environment without a pre-seeded candidate, it crashed with `RuntimeError: Candidate profile resolution failed`.
3. **External Network Requests During Testing:**
   - The test suite attempted live HTTP connections to `https://generativelanguage.googleapis.com/...` using `GEMINI_API_KEY` configured in `.env`.
   - Repeated 503 and 429 errors from Google Gemini caused test execution to stall for over 7 minutes. Live network calls must be mocked in test fixtures.
