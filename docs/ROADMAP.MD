# Roadmap

---

## Phase 0 — Foundation

**Status:** IN PROGRESS

**Goal:** Repository structure, documentation, development environment, infrastructure.

**Scope:**
- Repository initialization and directory structure
- Documentation system (AGENTS.md, docs/, context/, tasks/)
- Docker Compose (PostgreSQL, Redis, backend, discord-bot, workers)
- Discord bot skeleton (package.json, tsconfig, bot startup)
- FastAPI backend skeleton (requirements.txt, main.py, health endpoint)
- Database migration tooling setup
- `.env.example` with all required variables
- Basic CI (linting, type checking)

**Dependencies:** None.

**Acceptance Criteria:**
- [ ] Docker Compose starts all services
- [ ] Discord bot connects and responds to a health command
- [ ] FastAPI health endpoint returns 200
- [ ] Database is accessible and migrations run
- [ ] CI passes on clean checkout

---

## Phase 1 — Candidate Profile

**Status:** NOT STARTED

**Goal:** Store and manage candidate data so the system can use it for matching and generation.

**Scope:**
- Candidate profile database model
- Import `candidate-profile.yaml` into database
- Profile CRUD API endpoints
- Discord commands: `/profile`, `/profile update`
- Validation of profile data

**Dependencies:** Phase 0.

**Acceptance Criteria:**
- [ ] Candidate profile stored in PostgreSQL
- [ ] Profile viewable via `/profile` Discord command
- [ ] Profile editable via Discord modal
- [ ] Master resume accessible to backend services

---

## Phase 2 — Job Collection

**Status:** NOT STARTED

**Goal:** Automatically discover and store normalized job postings from at least one source.

**Scope:**
- Job and Company database models
- JobCollector abstract interface
- First source implementation (TBD — likely an official API)
- Job normalization to common schema
- Deduplication logic (layers 1–3)
- Scheduled collection via worker
- Collection health tracking

**Dependencies:** Phase 0.

**Acceptance Criteria:**
- [ ] Jobs collected automatically on schedule
- [ ] Jobs normalized to common format
- [ ] Duplicate jobs detected and merged
- [ ] Jobs stored in PostgreSQL
- [ ] Collection failures logged and recoverable

---

## Phase 3 — Job Intelligence

**Status:** NOT STARTED

**Goal:** Analyze job descriptions and produce candidate-job matches with deterministic scores.

**Scope:**
- JD requirement extraction (AI operation)
- JobRequirements structured output
- Hard filter implementation
- Match signal extraction
- Deterministic scoring with configurable weights
- Match explanation generation
- Job ranking
- Discord commands: `/jobs`, `/job <id>`, `/match <id>`

**Dependencies:** Phase 1, Phase 2.

**Acceptance Criteria:**
- [ ] JD parsed into structured requirements
- [ ] Hard filters disqualify incompatible jobs
- [ ] Deterministic match score computed for each job
- [ ] Explanation generated for each match
- [ ] Jobs viewable and ranked via Discord

---

## Phase 4 — Resume Intelligence

**Status:** NOT STARTED

**Goal:** Generate job-specific tailored resumes grounded in candidate evidence.

**Scope:**
- Resume planning (AI operation)
- Resume generation (AI operation)
- Evidence validation
- DOCX/PDF output
- Evidence provenance tracking
- Discord command: `/resume <job_id>`

**Dependencies:** Phase 1, Phase 3.

**Acceptance Criteria:**
- [ ] Tailored resume generated per job
- [ ] All claims traceable to master resume
- [ ] Output downloadable as DOCX/PDF
- [ ] User can review before use

---

## Phase 5 — Application Management

**Status:** NOT STARTED

**Goal:** Track application lifecycle from discovery through outcome.

**Scope:**
- Application and ApplicationEvent database models
- Application state machine
- Status tracking (lifecycle states)
- Discord commands: `/applications`, `/application <id>`
- Cover letter generation
- Application question assistance
- Application preparation workflow

**Dependencies:** Phase 3, Phase 4.

**Acceptance Criteria:**
- [ ] Applications tracked with lifecycle status
- [ ] Status transitions follow state machine rules
- [ ] All transitions logged as events
- [ ] Cover letter generated per job
- [ ] Application questions answered with evidence

---

## Phase 6 — Automation

**Status:** NOT STARTED

**Goal:** Daily digest, human approval flow, and submission assistance.

**Scope:**
- Daily digest generation and delivery via Discord DM
- Application approval flow (review → approve → submit assistance)
- Human confirmation gate enforcement
- Notification system (digest, status updates, errors)

**Dependencies:** Phase 5.

**Acceptance Criteria:**
- [ ] Daily digest sent via Discord DM
- [ ] User can approve/reject applications via Discord buttons
- [ ] No submission without explicit user confirmation
- [ ] Error notifications delivered to user

---

## Phase 7 — Personalization

**Status:** NOT STARTED

**Goal:** Learn from application outcomes to improve matching accuracy.

**Scope:**
- Application outcome tracking (interview, rejection, offer)
- Feedback loop to refine match scoring weights
- Preference learning from user actions (save, skip, apply patterns)
- Score weight tuning based on historical data

**Dependencies:** Phase 6 (sufficient application history needed).

**Acceptance Criteria:**
- [ ] Outcomes recorded and linked to jobs and matches
- [ ] Scoring weights adjustable based on outcome data
- [ ] Matching accuracy improves over time
