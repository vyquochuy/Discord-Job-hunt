# Cloudflare Pages — React SPA deployment

Source-checked 2026-11-09; dashboard labels and provider quotas are not verified here.

## Build and publish

The live app is React 18 / TypeScript / Vite, not the removed Vanilla JS frontend. In Pages Git integration use repository root as the build root:

- Framework preset: Vite (or None with the explicit command below).
- Build command: `npm --prefix frontend ci && npm --prefix frontend run build`
- Output directory: `frontend/dist`
- Use Node 22 (matching the Compose frontend builder).

`frontend/dist` is generated and ignored. Never publish `frontend/` source as the website. Vite does not currently copy root `frontend/env.js` or `frontend/_redirects` automatically (no `publicDir` override). Append this to the Linux Pages build command:

```sh
cp frontend/env.js frontend/_redirects frontend/dist/
```

The deployed `_redirects` must contain `/* /index.html 200` so direct SPA routes work.

For a local PowerShell build from the repository root:

```powershell
npm --prefix frontend ci
npm --prefix frontend run build
Copy-Item frontend/env.js,frontend/_redirects frontend/dist/
```

Deploy **that output directory**, not source, using an installed Wrangler CLI:

```powershell
wrangler login
wrangler pages deploy frontend/dist --project-name=job-hunter
```

## Runtime API configuration

`frontend/index.html` loads `/env.js` before the app. Set the public backend address in `frontend/env.js` before copying it to dist:

```javascript
window.ENV = {
  API_URL: 'https://job-hunt-backend-0hrl.onrender.com/api/v1',
  ENVIRONMENT: 'production',
};
```

This file is public browser configuration: never put JWT signing keys, internal service secrets, database credentials or Discord tokens here. Pages environment variables alone do not become `window.ENV`; generate/copy the file explicitly if using build variables.

Actual precedence in `frontend/src/config/env.ts`:

1. Browser `localStorage['jh_api_base']` override (System page).
2. Local-host detection (port 8000 uses `/api/v1`; other local ports target backend port 8000).
3. `window.ENV.API_URL`, then compatibility runtime globals.
4. `<meta name="api-base" content="https://your-backend.example/api/v1">`.
5. Relative `/api/v1` fallback.

Clear a stale System-page override before diagnosing `env.js`. Only use a backend you trust: authenticated requests carry bearer credentials to the configured API.

## Backend security and verification

Set backend `ALLOWED_CORS_ORIGINS` to exact trusted frontend origins, e.g. `https://job-hunter.pages.dev` plus your custom domain. The code uses an explicit allowlist, **not** `*`, `*.pages.dev` or a Vercel-wide regex. Add approved preview origins individually; do not trust every tenant of a hosting provider.

Check deployed `/env.js`, `/_redirects` in the uploaded artifact, assets, and a direct `/jobs` navigation. A JSON/HTML mismatch usually means the API address points at the SPA rather than FastAPI.

PDF URLs from `frontend/src/api/resumes.ts` carry an access JWT as `?token=` for iframe navigation. The backend validates authentication and candidate ownership (privileged admins/internal services retain their explicit bypass); a UUID alone is not access. Treat query-token URLs as credentials and avoid logging/sharing them. Missing ephemeral PDFs are recompiled from PostgreSQL only after authorization.

Render liveness is `/health` (no database queries), readiness is `/health/ready` (database check). Cold starts are handled by bounded read retries and feedback; do not add keep-alive polling. Network failures/timeouts on mutations must not trigger automatic retries.

Evidence: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/config/env.ts`, `frontend/src/api/client.ts`, `backend/app/main.py`, `backend/app/api/v1/endpoints/resumes.py`.
