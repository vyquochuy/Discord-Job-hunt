# Discord adapter deployment

Source-checked 2026-11-09. The Web Application is the primary interface; Discord is optional. Legacy slash commands remain registered and some still call protected APIs; they are not a supported multi-user authentication bridge.

## Discord setup

Create an application in Discord Developer Portal; obtain its bot token and Application ID. Invite it with `bot` and `applications.commands` scopes and only the permissions needed (send messages, embed links, attach files for retained file flows). Current gateway intents in `discord-bot/src/index.ts` are Guilds, GuildMessages and DirectMessages: Message Content and Server Members privileged intents are not required by this implementation.

## Configuration

For direct Node execution, `dotenv.config()` reads `.env` in the **current working directory**. When running inside `discord-bot/`, configure `discord-bot/.env` (ignored), or supply process environment variables. Compose explicitly reads the root `.env`.

```dotenv
DISCORD_TOKEN=replace_with_bot_token
DISCORD_CLIENT_ID=replace_with_application_id
DISCORD_GUILD_ID=replace_with_server_id
ALLOWED_USER_ID=replace_with_owner_discord_user_id
BACKEND_API_URL=http://localhost:8000
WEB_APP_URL=http://localhost:8000
INTERNAL_API_SECRET=replace_with_strong_random_secret_matching_backend
```

Use an HTTPS backend and public Web App origin outside local development. `BACKEND_API_URL` is the backend origin (the HTTP client adds `/api/v1`); `WEB_APP_URL` is the frontend origin for links. `DISCORD_GUILD_ID` is optional: absent means global command registration, present means guild registration. Ten commands are registered at startup, not just by `npm run dev`.

`INTERNAL_API_SECRET` grants privileged service access, not the Discord member's candidate identity. Never expose it to browsers or untrusted guilds. `ALLOWED_USER_ID` is checked in several handlers, but is optional and **not a universal guard** (`apply` and `resume` lack that check). Setting it is not proof all interactions are owner-only. Keep this legacy adapter in a trusted/private deployment until handler authorization and tenant mapping are reviewed. Protected candidate calls may fail or lack a candidate context; the service principal must not be described as an authenticated personal user.

## Local execution

From the repository root:

```powershell
cd discord-bot
npm ci
npm run dev
```

Or build and run in that directory:

```powershell
npm run build
npm start
```

For Compose, from the repository root:

```powershell
docker compose up -d discord-bot
docker compose logs -f discord-bot
```

Compose overrides the backend origin with `http://backend:8000`. The bind mount `./discord-bot:/app` masks the image's built `dist`; ensure a local `discord-bot/dist` exists (`npm run build`) before starting. Backend startup also depends on the frontend builder. After frontend changes: `docker compose run --rm frontend-build`, then `docker compose restart backend`.

## Behavior and hosting limits

Commands currently registered: `/ping`, `/profile`, `/jobs`, `/job`, `/match`, `/recommend`, `/collect`, `/resume`, `/apply`, `/import`. Inspect `discord-bot/src/commands/` for current options; legacy collector choices and links can lag behind backend support. Profile seed files are `context/candidate-profile.yaml` and `context/master-resume.tex`, not `candidate_profile.md`.

Application preparation defaults to simulation in the backend; actual submission is unsupported (501). The legacy `/apply` command still defaults `simulate_only` to false, so do not interpret it as a working mail transport or a Web UI approval flow. Use the Web App for candidate workflows.

Use a host supporting a long-running Node process and outbound Discord Gateway connections. No provider's free tier is guaranteed 24/7/always-on here; check current provider terms, sleep behavior and cost. Render Free backend cold starts remain possible. Do not add keep-alive polling to defeat its idle policy. Never commit tokens or print credentials in deployment logs.

Evidence: `discord-bot/src/config.ts`, `src/index.ts`, `src/services/api-client.ts`, `src/commands/apply.ts`, `src/commands/resume.ts`, `package.json`, `Dockerfile`, root `docker-compose.yml`, `backend/app/core/security.py`.
