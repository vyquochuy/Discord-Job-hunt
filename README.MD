# AI Job Hunter Agent

Personal AI-powered job hunting assistant operated through Discord.

> **Status:** Early foundation — directory structure and documentation only. No runnable code yet.

---

## Architecture

```
Discord Bot (TypeScript) → FastAPI Backend (Python) → PostgreSQL
                                     ↓
                              Workers (Python) ← Redis Queue
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.MD) for full architecture.

---

## Prerequisites

- Node.js 18+ (Discord bot)
- Python 3.11+ (backend, workers)
- PostgreSQL 15+ with pgvector
- Redis
- Docker & Docker Compose (recommended)

---

## Setup

```bash
# Not yet runnable — setup instructions will be added in Phase 0
cp .env.example .env    # Configure environment variables
docker compose up -d    # Start all services
```

### Environment Variables

```bash
# .env.example does not exist yet — will be created in Phase 0
DISCORD_TOKEN=
OPENAI_API_KEY=
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

---

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Discord Bot
cd discord-bot
npm install
npm run dev

# Tests (not yet configured)
# pytest                    # Backend tests
# npm test                  # Bot tests
```

---

## Documentation

| File | Purpose |
|------|---------|
| [`AGENTS.md`](AGENTS.MD) | **Start here** — AI agent rules and context |
| [`docs/PROJECT.md`](docs/PROJECT.MD) | Product definition and workflow |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.MD) | System architecture and data model |
| [`docs/AI_SYSTEM.md`](docs/AI_SYSTEM.MD) | AI pipeline specification |
| [`docs/ROADMAP.md`](docs/ROADMAP.MD) | Development phases |
| [`docs/SECURITY.md`](docs/SECURITY.MD) | Security policy |
| [`docs/DECISIONS.md`](docs/DECISIONS.MD) | Architecture Decision Records |
