# JWT token storage migration plan (SEC-06)

**Status (2026-11-09): proposed, not implemented.** Tokens still live in browser `localStorage`; documenting this plan does not mitigate script-readable token storage.

## Current implementation

- `frontend/src/api/client.ts` persists `jh_access_token` and `jh_refresh_token`, attaches Bearer headers and coordinates refresh with one shared Promise. Removed `frontend/js` and `frontend/legacy` paths are not active code.
- `backend/app/api/v1/endpoints/auth.py` returns tokens in JSON and accepts refresh/logout tokens in request bodies; no auth-cookie issuance is implemented.
- `backend/app/core/security.py` authenticates Bearer access JWTs; the optional/internal dependency also accepts `?token=` for iframe/download navigation. Resume ownership is checked in `backend/app/api/v1/endpoints/resumes.py` before serving or recompiling PDFs, with explicit privileged exceptions.
- Access TTL defaults to 30 minutes, refresh TTL to 30 days. XSS executing in this origin can read both. CORS does not prevent same-origin XSS theft.

## Proposed rollout gates

1. **Choose deployment topology first.** Pages (`pages.dev`) and Render (`onrender.com`) are cross-site. `SameSite=Lax`/`Strict` cookies are not sent on cross-site fetches. Prefer a same-site custom-domain topology or a same-origin proxy; cross-site cookies require `SameSite=None; Secure` and may still be blocked by third-party-cookie restrictions. Do not promise cookie compatibility before browser verification.
2. **Backend cookie contract.** Issue `HttpOnly; Secure` tokens with narrowly scoped paths and matching deletion attributes. Define expiration, rotation, logout, and header/cookie precedence explicitly. Avoid returning refresh tokens to JavaScript after migration; indefinite dual-mode JSON issuance defeats the confidentiality objective.
3. **CSRF before activation.** Validate allowed origins and use a server-validated CSRF token for cookie-authenticated state changes (`POST`, `PUT`, `PATCH`, `DELETE`, including refresh/logout). Use a session-bound signed double-submit or synchronizer-token design, not an unbound cookie/header equality check alone. Keep exact credentialed CORS origins; never wildcard origins.
4. **Frontend migration.** Update `frontend/src/api/client.ts` and AuthContext to use `credentials: 'include'`, remove persistent token reads/writes, and clear old localStorage values on rollout/logout. Preserve coordinated refresh and bounded read retries; never retry mutations on timeout/network failure.
5. **PDF embeds.** Replace or explicitly retire access JWT query URLs. Test owner-only iframe/download access in the chosen cookie topology; never make resume UUIDs public capabilities. HttpOnly auth does not stop malicious same-origin script making authenticated requests.
6. **Compatibility window.** If Bearer clients remain, define a bounded transition, tests and rollback; only remove header support after non-browser adapters are accounted for. Internal service secrets remain server-side and separate from user identity.

## Acceptance checks (not yet executed)

- Browser reload/login/refresh/logout with concurrent requests and multiple tabs; old storage cleared.
- Cross-origin and cross-site behavior on actual frontend/backend domains, including blocked third-party cookies.
- CSRF rejection for all cookie-authenticated mutations; allowed requests succeed.
- PDF without auth rejected; wrong tenant rejected; owner succeeds, including JIT after artifact loss.
- No refresh credential returned to JavaScript or exposed through query URLs/logs; cookie deletion works with original scope.

This migration reduces direct token extraction, not all XSS impact. Keep output escaping and dependency review independently.
