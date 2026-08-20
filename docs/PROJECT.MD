# Job Hunter Agent — Project Definition

## Vision

A personal AI-powered job hunting assistant that:

- Discovers relevant jobs from permitted sources
- Evaluates them against the candidate's profile
- Generates tailored application materials
- Assists with application preparation
- Tracks outcomes and reports via Discord

Discord is the primary interface.

---

## Problem

A candidate currently must manually:

- Search for jobs across multiple platforms
- Read and evaluate each job description
- Assess personal fit for each role
- Customize resume for each application
- Write cover letters
- Answer application questions
- Track application status
- Follow up on submitted applications

This system automates the repetitive parts while keeping the candidate in control of final decisions.

---

## Target User

Single candidate. MVP is not multi-tenant.

Multi-tenancy is not planned for the initial release.

---

## Core Workflow

```
Job Discovery → Normalize → Deduplicate → Extract Requirements
  → Match Candidate → Rank → Tailor Resume → Prepare Application
  → Human Approval → Submit → Track → Daily Report
```

---

## Key Term Definitions

### Job Recommendation

A job that has been collected, normalized, analyzed, scored against the candidate profile, and presented to the user with a match score and explanation. The system recommends jobs above a configurable score threshold.

### Good Match

A job where:

- No hard filter disqualifies the candidate (location, work authorization, seniority)
- The candidate's skills cover a significant portion of required skills
- The candidate has relevant project or work experience
- The resulting deterministic score exceeds the recommendation threshold

### Tailored Resume

A resume generated from the master resume (`context/master-resume.md`) that:

- Selects the most relevant evidence for this specific job
- Reorders and emphasizes skills matching the JD requirements
- Rewrites bullet points to align with the role's language
- Omits irrelevant content
- **Never invents** experience, metrics, employment, or certifications

### Application Preparation

The process of assembling all materials needed to apply:

- Tailored resume (DOCX/PDF)
- Cover letter (if required)
- Answers to application-specific questions
- All grounded in verified candidate evidence
- Presented to the user for review before submission

---

## MVP Scope

- Discord bot as primary interface
- Job collection from at least one permitted source
- Job normalization and deduplication
- JD requirement extraction (AI)
- Candidate matching and deterministic scoring
- Job ranking and recommendation via Discord
- Candidate profile management
- Resume tailoring per job
- Application tracking with status lifecycle
- Daily digest via Discord

---

## Out of Scope (MVP)

- Mass automatic applications
- CAPTCHA / anti-bot bypass
- Unauthorized scraping
- Fake experience generation
- Automatic application submission (without human approval)
- Multi-user SaaS
- Billing
- Mobile application
- Web UI

---

## Application Lifecycle

```
DISCOVERED          → Job found by collector
  ↓
ANALYZED            → JD extracted, match scored
  ↓
RECOMMENDED         → Score above threshold, presented to user
  ↓
SAVED               → User bookmarks for later
  ↓
PREPARING           → Resume/cover letter being generated
  ↓
READY_FOR_REVIEW    → Materials ready, awaiting user review
  ↓
APPROVED            → User approves submission
  ↓
SUBMITTED           → Application submitted
  ↓
  ├── OA            → Online assessment received
  ├── INTERVIEW     → Interview scheduled/completed
  ├── OFFER         → Offer received
  ├── REJECTED      → Rejected at any stage
  └── WITHDRAWN     → Candidate withdrew
```

### Transition Rules

| Transition                    | Triggered By             | Requires User Confirmation |
| ----------------------------- | ------------------------ | -------------------------- |
| DISCOVERED → ANALYZED         | System (automatic)       | No                         |
| ANALYZED → RECOMMENDED        | System (score threshold) | No                         |
| RECOMMENDED → SAVED           | User                     | No                         |
| SAVED/RECOMMENDED → PREPARING | User or system           | No                         |
| PREPARING → READY_FOR_REVIEW  | System                   | No                         |
| READY_FOR_REVIEW → APPROVED   | **User only**            | **Yes**                    |
| APPROVED → SUBMITTED          | **User only**            | **Yes**                    |
| SUBMITTED → OA/INTERVIEW      | User                     | No                         |
| Any → REJECTED                | User                     | No                         |
| Any → WITHDRAWN               | User                     | No                         |

**Invalid transitions:**

- Cannot go from DISCOVERED directly to SUBMITTED
- Cannot skip APPROVED before SUBMITTED
- Cannot reverse from SUBMITTED to PREPARING

---

## Human-in-the-Loop

The user must be able to:

```
View recommended jobs
  ↓
Review match explanation
  ↓
Request resume generation
  ↓
Review generated resume
  ↓
Review complete application package
  ↓
Confirm submission
```

**Application submission must never happen because an LLM decided it was appropriate.**

---

## Design Principles

| #   | Principle               | Description                                 |
| --- | ----------------------- | ------------------------------------------- |
| 1   | Human-in-the-loop       | User approves all application submissions   |
| 2   | Evidence-grounded       | AI uses only verified candidate information |
| 3   | Untrusted external data | JDs and websites are untrusted inputs       |
| 4   | Modular architecture    | Discord UI independent from business logic  |
| 5   | Observable automation   | All actions traceable through logs and DB   |
| 6   | Deterministic scoring   | Code computes scores, not LLM               |
