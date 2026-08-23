# Master Resume

> **This is the source of truth for all resume generation.**
> AI may only use information present in this document.
> Do not add information here unless it is verified and accurate.

---

## Professional Summary

Final-year Computer Science student specializing in Cyber Security with strong foundations in C++, Python, TypeScript, object-oriented programming, algorithms, computer networks, and software engineering. Experienced in developing system-level applications, asynchronous backend architectures, implementing cryptographic security protocols, and designing scalable software architectures through academic and personal projects. Seeking a Software Engineer Internship where I can contribute to real-world software development while strengthening expertise in system design and software engineering practices.

---

## Education

### Bachelor of Computer Science (Cyber Security) — VNUHCM - University of Science
**Graduation:** Expected Oct 2026  
**GPA:** 3.15/4.0  

**Relevant coursework:** Computer Networks, Database Systems, Fundamentals of Artificial Intelligence, Introduction to Machine Learning, Introduction to Cryptography, Encryption Application, Blockchain and Applications, Data Safety and Recovery.

---

## Technical Skills

| Category | Skills |
|---|---|
| Programming Languages | Python, JavaScript, TypeScript, C++, Dart, SQL |
| Frameworks & Libraries | FastAPI, React, Tailwind CSS, NextJS, Hono, Flutter |
| Databases & Caching | PostgreSQL, SQLite, Cloudflare D1, Redis, pgvector |
| DevOps & Tools | Docker, Docker Compose, Git, Linux, Alembic, LaTeX, Wireshark, OpenSSL |
| Security & Systems | Zero-Knowledge Architecture, Argon2id, AES-256-GCM, ECDH P-256, Shamir Secret Sharing, Anti-Enumeration Security, X.509 PKI, RSA-2048, SHA-256 |
| Languages | Vietnamese (Native), English (B1) |

---

## Projects

### AI Job Hunter: Autonomous Agent & Resume Intelligence System
- **Repository:** https://github.com/vyquochuy/Discord-Job-hunt
- **Period:** Jul 2026 -- Present
- **Role:** Author & Sole Developer
- **Technologies:** Python, FastAPI, PostgreSQL, pgvector, Redis, SQLAlchemy 2.0, Alembic, Docker, TypeScript, discord.js, LaTeX, RapidFuzz
- **Evidence:**
  - **Asynchronous Microservices & Ingestion Engine:** Architected an asynchronous backend engine using FastAPI, SQLAlchemy 2.0 async, Redis, and PostgreSQL with pgvector; engineered a multi-source job ingestion pipeline across 5 collectors (ITViec, Remotive, TopCV, CareerLink, Mock) utilizing SHA-256 content hashing for zero-token redundant caching.
  - **3-Tier Deduplication & 7-Signal Matching:** Designed a 3-tier deduplication pipeline (Exact Hash -> RapidFuzz -> Cosine pgvector) and a deterministic 7-signal job scoring engine with strict tri-state hard filters (ELIGIBLE/BLOCKED/UNCERTAIN) and invariant weight normalization, evaluating batches in under 6 seconds.
  - **Zero-Hallucination Resume Tailoring & LaTeX Sandbox:** Engineered an evidence-grounded resume tailoring engine with RoleClassifier, MMR-style diverse evidence selection, and ProvenanceVerifier (partial and token set fuzzy checks), paired with automated LaTeX compilation sandbox (pdflatex) generating verifiable PDF resumes and markdown cover letters with >= 90% provenance confidence.
  - **Discord Bot Automation & Full Observability:** Built an interactive Discord bot (TypeScript, discord.js v14) with rich embeds, action buttons, modals, and direct PDF streaming, orchestrating end-to-end autonomous daily batch runs across 58 automated unit and integration tests.

### EAP-TLS Authentication Protocol Demo
- **Repository:** https://github.com/vyquochuy/EAP-TLS-DEMO
- **Period:** Feb 2025 -- May 2025
- **Role:** Sole Developer
- **Technologies:** C++17, OpenSSL, X.509 PKI, RSA-2048, SHA-256, Visual Studio 2022
- **Evidence:**
  - **Protocol Simulation & Architecture:** Designed and implemented a complete simulation of the IEEE 802.1X EAP-TLS authentication protocol in C++17, developing a three-party architecture consisting of EAP Peer, Authenticator, and Authentication Server to emulate enterprise network authentication workflows.
  - **PKI & Certificate Infrastructure:** Implemented Public Key Infrastructure (PKI) components including Certificate Authority creation, X.509 certificate generation, certificate signing, and chain validation using OpenSSL.
  - **Mutual Authentication & Cryptography:** Built mutual authentication mechanisms through certificate verification and secure session establishment using RSA-OAEP encrypted key exchange and SHA-256 based key derivation.
  - **Object-Oriented System Modeling:** Applied object-oriented design principles to model authentication entities, certificate management, and protocol message flows.

### VYVYCHAT
- **Repository:** https://github.com/vyquochuy/vyvychat
- **Live Demo:** https://vyvychat.myvault-service.workers.dev/
- **Period:** May 2026 -- Jun 2026
- **Role:** Full-stack Developer
- **Technologies:** React, TypeScript, Tailwind CSS, Cloudflare Workers, Durable Objects, Web Crypto API, IndexedDB, Cloudflare D1, Cloudflare KV
- **Evidence:**
  - **Cryptography & E2EE:** Architected a zero-knowledge End-to-End Encryption (E2EE) system with secure ECDH P-256 key exchange, non-extractable local key storage, and recovery-based key rotation; verified correct decryption across 3 simultaneous device sessions with no key leakage.
  - **Stateful Real-Time Edge:** Engineered a stateful WebSocket layer using Cloudflare Durable Objects to manage persistent edge connections, achieving a measured round-trip latency of ~45ms (tested from Vietnam to Cloudflare Asia-Pacific PoP) with stable presence tracking and typing indicators under concurrent load.
  - **Serverless Infrastructure & Rate-Limiting:** Designed a relational data model on Cloudflare D1 (SQLite) and implemented token-bucket rate-limiting with Cloudflare KV to protect authentication and OTP flows; load-tested to sustain 200 req/min per user before throttling, blocking brute-force attempts within under 1 second.

### Account Manager: Zero-Knowledge Password Vault
- **Repository:** https://github.com/Chickyo/Account-Manager
- **Period:** Mar 2026 -- Present
- **Role:** Author & Lead Developer
- **Technologies:** Cloudflare Workers, Hono, TypeScript, Flutter, Dart, Android Keystore/Keychain, Hive, Argon2id, AES-256-GCM/CTR
- **Evidence:**
  - **Serverless API & Sync Architecture:** Designed a highly scalable serverless synchronization backend using Cloudflare Workers and the Hono framework (TypeScript); API endpoints benchmarked at < 80ms average response time under simulated multi-device sync load (tested with 10 concurrent devices), handling only pre-encrypted Vault Chunks to guarantee zero server-side plaintext exposure.
  - **Relational Database & Blind Storage Schema:** Modeled a robust 9-table relational database schema in Cloudflare D1 (SQLite) supporting multi-tenant user metadata, device logs, and recovery blobs via Shamir's Secret Sharing (3-of-5 threshold); paired with Cloudflare KV Namespace for high-performance session caching.
  - **Cryptographic & Anti-Enumeration Security:** Implemented server-side authentication with client-side Argon2id password hashing (t=3, m=64MB) and deterministic fake salts to eliminate user enumeration; engineered dynamic token-bucket rate-limiting capable of sustaining legitimate traffic up to 100 req/min while auto-blocking anomalous bursts (>20 req/10s) within one KV write cycle; audit logging captures 100% of auth events.

---

## Experience

<!--
### [Role] — [Company]
**Period:** [Start] to [End]

- Responsibility or achievement
- Another item with evidence

### Evidence
- Verifiable metric or outcome
-->

---

## Certifications

<!--
- [Certification Name] — [Issuer] ([Year])
-->

---

## Additional Information

<!--
- Languages spoken
- Volunteer work
- Publications
- Other relevant information
-->
