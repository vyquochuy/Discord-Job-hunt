# Job Hunter Platform — Project Definition

## Vision

A personal AI-powered job hunting intelligence platform that:

- Discovers relevant jobs from permitted sources autonomously
- Evaluates them against the candidate's profile with deterministic scoring
- Generates tailored, Zero-Hallucination application materials (LaTeX PDF + Cover Letter)
- Tracks outcomes and application lifecycle stages
- Serves as a full-featured **Web Application** as primary user interface
- Delivers optional summary notifications via **Discord**

---

## Problem

A candidate currently must manually:

- Search for jobs across multiple platforms
- Read and evaluate each job description
- Assess personal fit for each role
- Customize resume for each application
- Write cover letters
- Answer application questions
- Track application status across multiple spreadsheets/notes
- Follow up on submitted applications

This system automates repetitive aggregation and tailoring while keeping the candidate in complete control of decisions through an accessible, information-dense Web Application.

---

## Target User

Single candidate with User 1–1 CandidateProfile identity mapping.

---

## Core Workflow

```
Job Discovery → Normalize → Deduplicate → Extract Requirements
  → Match Candidate → Rank → Web Dashboard Presentation
  → Tailor Resume (LaTeX + PDF) → Human Review on Web → Prepare Application
  → Track Lifecycle (Saved / Applied / Interview / Offer) → Optional Discord Notification
```

---

## Key Term Definitions

### Job Recommendation
A job that has been collected, normalized, analyzed, scored against the candidate profile, and presented on the Web Dashboard with a match score, signal breakdown, and explanation.

### Good Match
A job where:
- No hard filter blocks the candidate (location, work mode, level, seniority)
- The candidate's skills cover required and preferred skills
- The candidate has relevant project or work experience evidence
- The resulting deterministic score exceeds recommendation thresholds ($\ge 60$ for Good Match, $\ge 80$ for Strong Match)

### Tailored Resume
A resume generated dynamically from verified candidate facts that:
- Selects the most relevant evidence for this specific job
- Prioritizes matching skills and projects
- Rewrites bullet points to align with the role's language without altering factual truth
- **Never invents** experience, metrics, employment, or certifications (Zero-Hallucination guarantee)

### Application Preparation
The process of assembling all materials needed to apply:
- Tailored resume compiled into PDF and LaTeX source
- Authentic Markdown cover letter
- Full fact-checked provenance evidence map

---

## Product Scope

### Web Application (Primary Product Interface)
- **Dashboard**: "What is worth applying today?" (Discoveries count, Strong matches, Top recommendations, Applications summary).
- **Job Explorer**: Search, filter by work mode, level, and location; detailed JD analysis and match reasoning.
- **Recommendations View**: Ranked list of highest-affinity roles.
- **Candidate Profile**: Direct profile management, skills, projects, and baseline context sync.
- **Resume Workspace**: Tailored resume inspection, PDF viewer, LaTeX code, Cover Letter, and Provenance fact-checker.
- **Application Tracking**: Lifecycle management (`SAVED` $\rightarrow$ `PREPARING` $\rightarrow$ `APPLIED` $\rightarrow$ `INTERVIEW` $\rightarrow$ `OFFER`/`REJECTED`).

### Background Automation & Pipeline
- Multi-source job collectors (ITViec, Remotive, CareerLink, TopCV, Mock).
- Ingestion pipeline with SHA-256 caching for 0 LLM cost hit.
- 3-tier deduplication (Exact Hash, RapidFuzz, pgvector Cosine).
- Daily autonomous batch runner.

### Discord Notification Adapter
- Pluggable notification channel for daily digest and high-match alerts.
- Deprecated slash commands providing brief highlights with links back to the Web App.

---

## Out of Scope (MVP)

- Mass automatic spam applications
- CAPTCHA / anti-bot bypass
- Unauthorized scraping
- Fake experience generation
- Autonomous application submission without human review
- Multi-tenant billing / SaaS subscriptions

---

## Application Lifecycle

```
DISCOVERED          → Job found by collector
  ↓
ANALYZED            → JD extracted, match scored
  ↓
RECOMMENDED         → Score above threshold, presented on Web Dashboard
  ↓
SAVED               → User bookmarks on Web App
  ↓
PREPARING           → Tailored resume / cover letter generated
  ↓
READY_FOR_REVIEW    → Materials ready, awaiting user review on Web
  ↓
APPLIED             → Application submitted / sent
  ↓
  ├── OA            → Online assessment received
  ├── INTERVIEW     → Interview scheduled/completed
  ├── OFFER         → Offer received
  ├── REJECTED      → Rejected at any stage
  └── WITHDRAWN     → Candidate withdrew
```

---

## Design Principles

| # | Principle | Description |
|---|-----------|-------------|
| 1 | **Web-First Interface** | Web Application is the primary tool for user interaction |
| 2 | **Human-in-the-loop** | User reviews and approves all application materials |
| 3 | **Evidence-grounded** | AI uses only verified candidate facts (Zero Hallucination) |
| 4 | **Database as Source of Truth** | Runtime state lives in PostgreSQL, not Discord or loose files |
| 5 | **Untrusted external data** | JDs and websites are untrusted inputs, sanitized before use |
| 6 | **Deterministic scoring** | Code computes scores from 7 signals, not unpredictable LLM numbers |
| 7 | **Pluggable Notifications** | Notification services are isolated behind clean provider interfaces |

