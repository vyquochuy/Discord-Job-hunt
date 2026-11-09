# Optional Discord adapter

The React Web App is the primary interface. This TypeScript / discord.js adapter retains legacy slash commands and links back to the Web App; it is not a multi-user authentication bridge.

See [deployment and security limitations](../docs/DISCORD_BOT_DEPLOYMENT.md) before enabling privileged commands. From this directory:

```powershell
npm ci
npm run build
npm start
```

For development: `npm run dev`. Direct execution reads `.env` from the current working directory; Compose reads the repository-root `.env`. Configure `DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, optional `DISCORD_GUILD_ID`, `ALLOWED_USER_ID`, `BACKEND_API_URL`, `WEB_APP_URL`, and a strong backend-matching `INTERNAL_API_SECRET`.

The internal secret is privileged service access, not a user's JWT. Optional owner checks are not enforced in every handler; do not deploy the legacy adapter to an untrusted guild assuming `ALLOWED_USER_ID` secures all actions. Actual application submission is unsupported by the backend; use the Web App for candidate workflows.
