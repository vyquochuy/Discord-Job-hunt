# Security remediation plan and source status

**Reviewed: 2026-11-09, current working tree.** This replaces the original pre-publication checklist; checked-in controls are not proof of deployed configuration or a fresh passing test suite. Historical findings retain their IDs in [security/FINDINGS.md](../security/FINDINGS.md).

## Implemented controls and evidence

| Area | Current source behavior | Evidence |
| --- | --- | --- |
| Tenant isolation (SEC-01/02) | Registration creates a clean user-owned candidate and handles duplicate email integrity errors. Resume PDF authentication and ownership checks precede delivery and JIT recompilation; privileged exceptions remain. | `backend/app/api/v1/endpoints/auth.py`, `resumes.py`, `backend/app/repositories/candidate.py`; `backend/tests/test_phase1_authorization_regression.py` |
| Service identity (SEC-03) | Valid internal secret maps to a distinct in-memory privileged service principal, not the first database user. It is not tenant identity or a Discord-user mapping. | `backend/app/core/security.py`; `backend/tests/test_phase2_auth_hardening.py` |
| CORS (SEC-04) | Explicit `ALLOWED_CORS_ORIGINS`; hosting-wide Vercel regex removed. Default dev origins include Vite port 5173. | `backend/app/main.py`, `backend/app/core/config.py`; `backend/tests/test_phase3_cors_xss.py` |
| JWT/passwords | Configured algorithm whitelist (default HS256), required claims/type/UUID checks, Argon2id, refresh rotation/row locking/grace and family revocation. Non-default secrets ≥32 characters required in every non-development environment. Existing access JWTs are not revoked by refresh-family revocation. | `backend/app/core/security.py`, `config.py`, `backend/app/services/auth_service.py` |
| Bootstrap admin | Registration does not promote the first registrant and reserves the bootstrap admin email; startup does not overwrite an existing admin password. | `backend/app/api/v1/endpoints/auth.py`, `backend/app/main.py` |
| Rate limits/errors | SlowAPI decorators protect selected auth/expensive/admin routes; generic unhandled error responses avoid raw exception disclosure. This is not a distributed quota guarantee. | `backend/app/core/limiter.py`, endpoint decorators, `backend/app/main.py` |
| SSRF prechecks | HTTP(S)-only, DNS/IP deny checks and redirect target revalidation. **No transport pinning**; see open SEC-05 below. | `backend/app/services/extraction/url_fetcher.py` |
| LaTeX | `-no-shell-escape`, working-directory separation, timeout and fail-closed compiler (no restrictive subprocess environment configured); readable PDF must have exactly one page. These are hardening controls, not an OS sandbox. | `backend/app/services/tailoring/latex_compiler.py`; `backend/tests/test_latex_compiler_safety.py` |
| Local infrastructure | Postgres/Redis published on loopback. Backend port 8000 remains published, Compose runs backend/workers as root with source mounts and reload; do not present Compose as production isolation. | `docker-compose.yml` |
| Submission | Preparation defaults to simulation; actual transport submission unsupported (501). Manual status updates track external actions. | `backend/app/services/tailoring/application_service.py`; `backend/tests/test_application_submission_safety.py` |

## Remaining work / acceptance gates

- **SEC-05 — DNS transport pinning: OPEN.** `socket.getaddrinfo()` validates a resolution, then ordinary `httpx.AsyncClient.get()` resolves independently. Pin the actual connection to validated addresses while preserving TLS SNI/Host; validate redirects at the connection boundary. Verify locally with deterministic DNS/transport fixtures. No live DNS-rebinding exploitation was run for this documentation pass.
- **SEC-06 — HttpOnly migration: PROPOSED, NOT MITIGATED BY DOCUMENTATION.** Both tokens remain in `frontend/src/api/client.ts` localStorage. See [TOKEN_STORAGE_MIGRATION_PLAN.md](TOKEN_STORAGE_MIGRATION_PLAN.md) for cross-site Pages/Render cookie constraints, CSRF, credentialed CORS and iframe migration gates. CORS is not XSS protection.
- **SEC-07 — global test network isolation: OPEN / needs revalidation.** Test-level mocks exist, but `backend/tests/conftest.py` only globally disables rate limiting; it does not globally deny outbound network or clear LLM credentials. Run tests with explicit dummy environment and network isolation; a passing run without a key is not proof of isolation.
- **Discord:** Legacy commands still use privileged internal credentials; optional owner checks are not universal. Keep deployment trusted/private, do not claim complete command deprecation or tenant mapping. See [DISCORD_BOT_DEPLOYMENT.md](DISCORD_BOT_DEPLOYMENT.md).
- **Public-repository hygiene:** Review current files, Git history, tags, releases and forks for credentials/PII. Rotate exposed secrets. History cleanup is destructive, requires explicit approval/backups and cannot erase already-cloned data; no cleanup is claimed here. Never blindly force-push a shared repository. Candidate seed files are intentional runtime import inputs; use anonymized equivalents if publishing them.
- **Deployment verification:** Confirm exact frontend CORS origins, strong secrets, log/query-token redaction, TLS and resource isolation in the deployed environment. `/health` must stay DB-free, `/health/ready` owns DB readiness, and no client keep-alive polling may defeat Render Free idle policy.

## Validation boundaries

This pass compared source/config and documentation only; it did not execute tests, call providers, rewrite history or deploy. Existing test files above are reproducible evidence targets, not newly verified pass claims. Run isolated checks with dummy credentials before release; frontend build command is `npm --prefix frontend run build`, deployment artifact is `frontend/dist`, runtime configuration is public `window.ENV` in `env.js` (see the [Pages guide](CLOUDFLARE_PAGES_GUIDE.md)).
