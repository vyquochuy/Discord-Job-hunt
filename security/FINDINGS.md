# Security Findings & Vulnerability Assessment — Job-Hunt Platform

**Date:** 2026-10-06  
**Auditor:** Senior Application Security Engineer & Backend Security Reviewer  
**Status:** Historical assessment (2026-10-06); source-status reconciliation 2026-11-09, not a fresh exploitation/test run
**Repository:** `c:\Game\Job-Hunt` (Branch: `main`)

---

## Current source reconciliation (2026-11-09)

SEC-01–04 fixes remain present. Historical severity/impact narratives below describe the original assessment, not newly reproduced vulnerabilities. SEC-05 remains an unpinned-DNS design risk: prechecks and redirect checks do not bind the actual httpx connection. SEC-06 is **open architectural exposure**, not mitigated by writing a migration plan: React `frontend/src/api/client.ts` still persists both tokens. SEC-07 has no global network-denial fixture (`backend/tests/conftest.py` only disables rate limiting); individual mocks do not prove suite-wide isolation. No live LLM calls or credential leakage were reproduced in this documentation review.

PDF access requires an access JWT (Bearer or supported `?token=`) and ownership validation before serving/JIT. Explicit superuser/internal-service privileges remain; a UUID is not a public capability. Query JWT URLs can leak through logs/history and must be treated as credentials. The internal principal is distinct from database users but is still privileged, not a universally tenant-bound identity.

Evidence: `backend/app/core/security.py`, `backend/app/api/v1/endpoints/auth.py`, `resumes.py`, `backend/app/main.py`, `backend/app/services/extraction/url_fetcher.py`, `frontend/src/api/client.ts`, `backend/tests/conftest.py`. Regression files listed below exist; their historical pass claims were not rerun here.

## 1. Summary of Findings

| ID | Title | Severity | Classification | Status | Target Component |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **SEC-01** | BOLA / IDOR in Resume PDF Download Endpoint | **High** | Confirmed Vulnerability | **Resolved (Phase 1)** | `resumes.py::download_resume_pdf` |
| **SEC-02** | Candidate Profile Hijacking During User Registration | **High** | Confirmed Vulnerability | **Resolved (Phase 1)** | `auth.py::register_user` |
| **SEC-03** | Service Authentication Masquerades as First Database User | **High** | Confirmed Vulnerability | **Resolved (Phase 2)** | `security.py::get_current_user_optional` |
| **SEC-04** | Overly Permissive CORS Origin Regex for Vercel Subdomains | **Medium** | Confirmed Vulnerability | **Resolved (Phase 3)** | `main.py::CORSMiddleware` |
| **SEC-05** | TOCTOU DNS Rebinding Window in Outbound URL Ingestion | **Medium** | Plausible Risk | Open | `url_fetcher.py::is_safe_public_url` |
| **SEC-06** | Browser `localStorage` Token Storage Exposing Refresh Tokens | **Low** | Plausible Risk / Architecture | **Open / migration proposed** | `frontend/src/api/client.ts::setTokens` & `docs/TOKEN_STORAGE_MIGRATION_PLAN.md` |
| **SEC-07** | Live External LLM Network Calls in Test Suite | **Low** | Confirmed Hygiene / Leak | Open | `backend/tests/` |
| **SEC-08** | LaTeX Compilation Process Escape (`\write18`) | N/A | False Positive | Mitigated | `latex_compiler.py` (`-no-shell-escape`) |
| **SEC-09** | JWT Algorithm Confusion / `alg: none` | N/A | False Positive | Mitigated | `security.py::decode_token` |
| **SEC-10** | Unbounded Memory Exhaustion via Resume Upload | N/A | False Positive | Mitigated | `profile.py::upload_resume` |

---

## 2. Detailed Findings

---

### SEC-01: BOLA / IDOR in Resume PDF Download Endpoint

- **File Path:** [`backend/app/api/v1/endpoints/resumes.py`](file:///c:/Game/Job-Hunt/backend/app/api/v1/endpoints/resumes.py#L164-L215)
- **Symbol:** `download_resume_pdf`
- **Relevant Code Behavior:**
  Endpoint previously allowed unauthenticated access to any resume PDF via UUID.
- **Exploit Preconditions:**
  An attacker obtains or guesses the UUID of another candidate's tailored resume.
- **Impact:**
  **High**. Exposure of Personally Identifiable Information (PII) including full name, home address, personal phone number, email address, GPA, academic history, employment records, and projects of any user. Complete violation of tenant isolation.
- **Confidence:** **CONFIRMED**  
- **Resolution:** **RESOLVED (Phase 1)**.
  - Endpoint now depends on `get_authenticated_user_or_internal`.
  - Verifies resume ownership via `verify_resume_ownership(resume, cand, _user)`.
  - Supports Bearer access JWT and `?token=` query param authentication (credential-bearing URL; not inherently leak-proof) for inline browser preview (`<iframe>` / `<embed>`).
- **Regression Test:** `backend/tests/test_phase1_authorization_regression.py::test_resume_pdf_download_bola_and_query_token_auth`

---

### SEC-02: Candidate Profile Hijacking and Race Condition in User Registration

- **File Path:** [`backend/app/api/v1/endpoints/auth.py`](file:///c:/Game/Job-Hunt/backend/app/api/v1/endpoints/auth.py#L80-L97), [`backend/app/repositories/candidate.py`](file:///c:/Game/Job-Hunt/backend/app/repositories/candidate.py#L64-L85)
- **Symbol:** `register_user`, `CandidateRepository.get_or_create_for_user`
- **Relevant Code Behavior:**
  Previously queried and claimed unassigned `Candidate` records (`user_id.is_(None)`), leading to profile hijacking and concurrent registration race conditions.
- **Exploit Preconditions:**
  The database contains any pre-seeded or unlinked `Candidate` record with `user_id = None`. Any actor registers via `/api/v1/auth/register`.
- **Impact:**
  **High**. Stolen candidate profiles, skills, projects, and unhandled `UniqueViolation` 500 error on concurrent registration collisions.
- **Confidence:** **CONFIRMED**.
- **Resolution:** **RESOLVED (Phase 1)**.
  - Removed unassigned candidate theft entirely. Each newly registered user is assigned a clean, isolated `Candidate` record.
  - Wrapped registration in explicit `try/except IntegrityError` handling returning HTTP 400 with a clean message.
- **Regression Test:** `backend/tests/test_phase1_authorization_regression.py::test_candidate_profile_unassigned_stealing_regression` & `test_concurrent_registration_email_collision_handling`

---

### SEC-03: Service Authentication Masquerades as Arbitrary First Database User

- **File Path:** [`backend/app/core/security.py`](file:///c:/Game/Job-Hunt/backend/app/core/security.py#L297-L313)
- **Symbol:** `get_current_user_optional` & `get_authenticated_user_or_internal`
- **Relevant Code Behavior:**
  When `X-Internal-Secret` was supplied, it executed a database query to select `User 1` (Admin) and masqueraded as that user.
- **Exploit Preconditions:**
  An internal service made requests to user-scoped endpoints with `X-Internal-Secret`.
- **Impact:**
  **High**. Conflated service-to-service authentication with user identity. Silently mutated User 1's profile and data.
- **Confidence:** **CONFIRMED**.
- **Resolution:** **RESOLVED (Phase 2)**.
  - Eliminated implicit database User fallback.
  - Returns an explicit, distinct in-memory system service principal (`00000000-0000-0000-0000-000000000001`, `system@jobhunter.internal`).
  - The service principal is distinct but has `is_superuser=True`; this fix removes implicit first-user identity, not all privileged access. Do not infer universal tenant scoping for internal-secret requests.
- **Regression Test:** `backend/tests/test_phase2_auth_hardening.py::test_internal_service_masquerade`

---

### SEC-04: Overly Permissive CORS Origin Regex for Vercel Subdomains

- **File Path:** [`backend/app/main.py`](file:///c:/Game/Job-Hunt/backend/app/main.py#L162-L172)
- **Symbol:** `app.add_middleware(CORSMiddleware)`
- **Relevant Code Behavior:**
  Included `allow_origin_regex=r"^https://[a-zA-Z0-9_-]+\.vercel\.app$"`, allowing cross-origin credentialed requests from any third-party app hosted on Vercel.
- **Exploit Preconditions:**
  Attacker registers a free Vercel domain and tricks a user into visiting it while logged in.
- **Impact:**
  **Medium**. Cross-origin reads/writes permitted from untrusted sibling Vercel tenants.
- **Confidence:** **CONFIRMED**.
- **Resolution:** **RESOLVED (Phase 3)**.
  - Removed `allow_origin_regex` wildcard pattern.
  - Whitelist strictly enforces configured deployment domains via `cors_origins`.
- **Regression Test:** `backend/tests/test_phase3_cors_xss.py::test_cors_rejects_untrusted_origins`

---

### SEC-05: TOCTOU DNS Rebinding Window in Outbound Manual URL Ingestion

- **File Path:** [`backend/app/services/extraction/url_fetcher.py`](file:///c:/Game/Job-Hunt/backend/app/services/extraction/url_fetcher.py#L15-L49)
- **Symbol:** `is_safe_public_url` & `URLFetcher.fetch`
- **Relevant Code Behavior:**
  `is_safe_public_url` resolves the hostname via `socket.getaddrinfo(hostname, None)` and validates that IP is not in private/reserved ranges. Afterwards, `httpx.AsyncClient` executes `await client.get(url)`, triggering a second, independent DNS resolution.
- **Exploit Preconditions:**
  An attacker sets up a dual-response DNS record with TTL 0 (returning a public IP on DNS query #1, and `127.0.0.1` or `169.254.169.254` on DNS query #2) and submits the URL to `POST /api/v1/jobs/ingest-manual`.
- **Impact:**
  **Medium**. Bypasses SSRF filtering to interact with internal services on `localhost` or cloud metadata services.
- **Confidence:** **PLAUSIBLE** (Classic Time-Of-Check to Time-Of-Use design flaw).
- **Current source evidence (2026-11-09):** Standard `httpx.AsyncClient` has no custom transport binding to the checked IP. Redirect targets are also prechecked, but connections remain unpinned. A bounded deterministic transport/DNS regression is still needed; no exploit was run here.

---

### SEC-06: Browser `localStorage` Token Storage Exposing Refresh Tokens

- **File Path:** [`frontend/src/api/client.ts`](../frontend/src/api/client.ts)
- **Symbol:** `ApiClient.setTokens`
- **Relevant Code Behavior:**
  Access Token (30m) and Refresh Token (30d) are stored in `window.localStorage.getItem('jh_access_token')` and `'jh_refresh_token'`.
- **Exploit Preconditions:**
  Any Cross-Site Scripting (XSS) vulnerability in the Single Page Application or imported dependencies.
- **Impact:**
  **Low-Medium**. An attacker executing script in the origin can exfiltrate the 30-day refresh token, achieving persistent account access.
- **Confidence:** **PLAUSIBLE / ARCHITECTURAL TRADE-OFF**.
- **Evidence limit:** This review did not establish a reachable XSS entry point or prove its absence. Both tokens remain script-readable; the HttpOnly plan is unimplemented and must account for cross-site Pages/Render cookies and CSRF.

---

### SEC-07: Live External LLM Network Calls and Credential Usage During Tests

- **File Path:** [`backend/tests/test_architectural_anti_hallucination.py`](file:///c:/Game/Job-Hunt/backend/tests/test_architectural_anti_hallucination.py), [`backend/tests/test_jd_agnostic_tailoring.py`](file:///c:/Game/Job-Hunt/backend/tests/test_jd_agnostic_tailoring.py)
- **Symbol:** `unit_regeneration_orchestrator.validate_and_regenerate`
- **Relevant Code Behavior:**
  Tests execute real HTTP requests to `https://generativelanguage.googleapis.com` if `GEMINI_API_KEY` is present in `.env`.
- **Exploit Preconditions:**
  Running `pytest` in an environment configured with live credentials.
- **Impact:**
  **Low**. Causes test suite stalls (over 7 minutes due to 429/503 retries), leaks keys in test logs/network traces, and causes unexpected API billing.
- **Confidence:** **CONFIRMED** (Directly observed during Phase 0 baseline test execution).
- **Current evidence limit (2026-11-09):** The original observation is historical. Suite-wide network isolation is still absent in conftest, but live calls, billing and key leakage were not reproduced in this documentation pass.

---

## 3. Mitigated Controls & False Positives Verified

- **SEC-08 (LaTeX Command Injection):**  
  `latex_compiler.py` uses `subprocess.run` with array arguments (no shell interpolation) and explicitly specifies `-no-shell-escape`, neutralizing `\write18` execution. **Mitigated.**
- **SEC-09 (JWT Algorithm Confusion):**  
  `security.py` strictly decodes with `algorithms=["HS256"]` and validates all required claims. **Mitigated.**
- **SEC-10 (Unbounded Uploads / Memory Exhaustion):**  
  `profile.py::upload_resume` checks Content-Length, file size, extension whitelist, and reads chunks up to 10MB limit. **Mitigated.**
