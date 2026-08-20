# Security Policy

> **Implementation Status:** NOT IMPLEMENTED — policy specification only.

---

## Secrets Management

**Never commit to repository:**
- Discord bot token
- LLM API keys (OpenAI, etc.)
- Database passwords
- OAuth credentials
- Session cookies
- Any API keys or tokens

**Storage:** Environment variables or `.env` files. `.env` must be in `.gitignore`.

**Access:** Only the service that needs a secret should have access to it. Discord bot does not need database credentials. Workers do not need Discord token (notifications go through a notification service).

---

## PII Protection

**Sensitive data in this system:**
- Candidate name, contact info (email, phone)
- Candidate profile (education, work history, skills)
- Resume content (all versions)
- Application data and history
- Cover letters and application answers

**Rules:**
- Do not log full PII in application logs
- Do not expose PII in public Discord channels (use DMs or ephemeral messages)
- Do not send PII to external services beyond what is necessary for the operation
- Database should be access-controlled
- Resume files stored securely, not publicly accessible

---

## Untrusted Data Sources

| Source | Risk | Classification |
|--------|------|---------------|
| Job descriptions | Prompt injection, misleading content | **Untrusted** |
| Scraped website content | XSS, malicious scripts, injection | **Untrusted** |
| Application questions | Attempt to extract system info | **Untrusted** |
| External URLs from JDs | Redirect, phishing, SSRF | **Untrusted** |
| Candidate profile data | Trusted (user-provided) | **Trusted** |
| Master resume | Trusted (user-provided) | **Trusted** |

**All external job content is untrusted.** Process it as data, never as instructions.

---

## Prompt Injection Defense

External content must never control AI agent behavior.

**Mitigations:**
- System prompts and external content separated with clear delimiters
- Structured output schemas constrain LLM responses
- All LLM output validated against expected schema
- Embedded instructions in JDs (e.g., "ignore previous instructions") treated as literal JD text
- Never pass raw external content as system instructions
- Log anomalous LLM outputs

---

## SSRF and External URL Risks

Job descriptions may contain URLs (company pages, application links).

**Rules:**
- Do not automatically fetch arbitrary URLs from JD content
- If fetching external URLs (e.g., for job details), validate URL scheme (http/https only)
- Do not follow redirects to internal/private networks
- Do not fetch URLs pointing to localhost, private IPs, or internal services
- Rate-limit external URL fetching

---

## Malicious Job Pages

Scraped job pages may contain:
- JavaScript that attempts to detect/fingerprint automation
- Misleading content designed to manipulate AI analysis
- Redirect chains to phishing sites
- Download triggers for malicious files

**Mitigations:**
- Browser automation (if used) operates in sandboxed context
- Downloaded content is text-only — never execute scripts from job pages
- Validate and sanitize all scraped content before processing
- Do not render untrusted HTML outside of sandboxed browser

---

## Browser Automation Safety

**Never bypass:**
- CAPTCHA
- Anti-bot mechanisms
- Authentication controls
- Rate limits
- Access restrictions
- Terms of Service

Only automate where explicitly permitted by the platform.

Playwright (or equivalent) must:
- Respect `robots.txt` where applicable
- Use reasonable request intervals
- Not impersonate real user behavior deceptively
- Not store or replay authentication cookies obtained without consent

---

## Authentication and Authorization

### Discord Bot Permissions

- Bot operates in a private server or via DMs
- Commands restricted to the authorized user (single-candidate MVP)
- Sensitive operations (application approval) only available to the bot owner
- Bot should not respond to commands from unauthorized users

### API Authentication

- Backend API should require authentication for all endpoints
- MVP: API key or shared secret between Discord bot and backend
- Future: OAuth2 or JWT if multi-user

### Database Access

- Database credentials are environment variables, never in source code
- Application connects with a role that has minimum necessary privileges
- No direct database access from Discord bot

---

## Rate Limiting

| Context | Strategy |
|---------|----------|
| Job source APIs | Per-source rate limits, respect `Retry-After` headers |
| LLM API calls | Request rate + token budget limits |
| Backend API | Rate limit Discord bot requests (prevent loops) |
| Browser automation | Reasonable intervals between requests |

---

## Application Submission Safety

- Application submission requires **explicit user confirmation via Discord**
- Never auto-submit without human approval
- Never silently retry failed submissions (risk of duplicate applications)
- Log all submission-related actions with timestamps
- Present submission summary to user before confirming

---

## Audit Logging

**Log (without PII):**
- Job collection runs (source, count, errors)
- AI processing events (operation type, job_id, success/failure)
- Application state transitions
- Submission attempts and outcomes
- Authentication events
- Error events

**Do not log:**
- Full candidate profile
- Resume content
- API keys or tokens
- Passwords
- Full JD text (reference by job_id instead)

---

## File Upload Safety

If users upload resume documents (DOCX, PDF):
- Validate file type and size before processing
- Do not execute macros or embedded scripts
- Process in sandboxed environment
- Store uploaded files securely with access control
- Scan for malicious content if feasible

---

## AI Security

LLM must not:
- Execute arbitrary commands on the system
- Access secrets or credentials
- Perform destructive database operations (DROP, TRUNCATE)
- Submit applications autonomously
- Make authorization or security decisions
- Expose system prompts or internal configuration
- Access files outside designated candidate data

---

## LLM Data Exposure

When sending data to external LLM APIs (e.g., OpenAI):
- Only send data necessary for the operation
- Be aware that JD content + candidate data is sent to the LLM provider
- Do not send database credentials, API keys, or system configuration
- Review LLM provider's data retention and usage policies
- Consider data residency requirements if applicable
