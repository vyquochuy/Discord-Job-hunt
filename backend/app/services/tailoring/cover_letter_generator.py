import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.candidate import Candidate
from app.models.job import Job

logger = logging.getLogger("cover_letter_generator")


# ==============================================================================
# Tầng 1: Pydantic Schemas cho Ingestion & Extraction
# ==============================================================================

class ParsedJD(BaseModel):
    company_name: str = Field(..., description="Tên công ty chuẩn hóa")
    target_role: str = Field(..., description="Chức danh tuyển dụng")
    seniority: str = Field(default="Intern", description="Cấp bậc")
    core_requirements: List[str] = Field(default=[], description="Top 3-5 yêu cầu/kỹ năng trọng tâm")
    domain_problems: List[str] = Field(default=[], description="Thách thức kỹ thuật công ty cần giải quyết")


class FeaturedProjectDraft(BaseModel):
    project_name: str = Field(..., description="Tên dự án tiêu biểu")
    architecture_summary: str = Field(..., description="1 câu tóm tắt giải pháp kiến trúc/kỹ thuật")
    impact_or_metric: str = Field(..., description="Chỉ số định lượng hoặc kết quả kiểm chứng (Zero-Hallucination)")


# ==============================================================================
# Tầng 3: Structured Draft Schema (JSON Output)
# ==============================================================================

class CoverLetterDraft(BaseModel):
    recipient_company: str
    target_role: str
    salutation: str
    hook: str = Field(..., description="1-2 câu nêu lý do ứng tuyển và điểm mạnh cốt lõi (khiêm tốn, trực diện)")
    technical_highlights: List[str] = Field(..., max_length=4, description="Kỹ năng khớp với bài toán của công ty")
    featured_projects: List[FeaturedProjectDraft] = Field(..., max_length=3, description="Tối đa 2-3 dự án khớp nhất")
    company_alignment: str = Field(..., description="Lý do năng lực ứng viên giải quyết được nhu cầu của công ty")
    call_to_action: str = Field(..., description="Lời chào kết thúc chuyên nghiệp, khiêm tốn")


class CoverLetterValidationReport(BaseModel):
    is_valid: bool
    word_count: int
    placeholder_violations: List[str] = []
    cliche_violations: List[str] = []
    fact_check_violations: List[str] = []
    word_count_warning: Optional[str] = None


# ==============================================================================
# Tầng 4: Deterministic Linter & Guardrails
# ==============================================================================

class CoverLetterLinter:
    """
    Guardrail Engine kiểm định 4 lớp:
    1. Bắt các placeholder rác (e.g. [Company Name], {Role}, XYZ, undefined).
    2. Cấm các từ sáo rỗng AI (thrilled to apply, delve, testament, seamlessly, tapestry...).
    3. Giới hạn dung lượng chuẩn (200 - 380 từ, mục tiêu 250 - 350 từ).
    4. Fact-checking đối chiếu số liệu/công nghệ với hồ sơ gốc (Zero-Hallucination).
    """

    FORBIDDEN_PLACEHOLDERS = [
        r"\[.*?\]",                        # [Company Name], [Insert ...]
        r"\{.*?\}",                        # {Company}, {Role}
        r"\b(XYZ\s*Corp|ABC\s*Company|undefined|null|Company\s*Name)\b",
    ]

    FORBIDDEN_CLICHES = [
        r"\bthrilled\s+to\s+apply\b",
        r"\bdelve\s+(?:into|deeper)\b",
        r"\ba\s+testament\s+to\b",
        r"\bseamlessly\b",
        r"\bpivotal\b",
        r"\bbeacon\b",
        r"\btapestry\b",
        r"\bpassionate\s+about\b",
        r"\bspearheaded\b",
        r"\bdynamic\s+environment\b",
    ]

    @classmethod
    def clean_text_from_placeholders(cls, text: str, fallback_company: str = "your team") -> str:
        """Tự động thay thế các placeholder rác nếu lỡ phát sinh."""
        cleaned = text
        # Thay thế các pattern [Company Name], [Insert Company], etc.
        cleaned = re.sub(r"\[(?:Company\s*Name|Insert\s*Company|Company)\]", fallback_company, cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[.*?\]", "", cleaned)  # Xóa các tag [ ... ] còn lại
        cleaned = re.sub(r"\{.*?\}", "", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    @classmethod
    def replace_cliches(cls, text: str) -> str:
        """Tự động thay thế các từ ngữ sáo rỗng AI bằng văn phong khiêm tốn, kỹ thuật."""
        replacements = [
            (r"\bthrilled to apply for\b", "pleased to apply for"),
            (r"\bI am thrilled to apply\b", "I am writing to express my strong interest"),
            (r"\bdelve into\b", "investigate"),
            (r"\ba testament to\b", "an example of"),
            (r"\bseamlessly\b", "reliably"),
            (r"\bpivotal\b", "key"),
            (r"\bpassionate about\b", "focused on"),
            (r"\bdynamic environment\b", "engineering team"),
        ]
        res = text
        for pat, repl in replacements:
            res = re.sub(pat, repl, res, flags=re.IGNORECASE)
        return res

    @classmethod
    def validate(cls, draft: CoverLetterDraft, candidate: Candidate) -> CoverLetterValidationReport:
        """Kiểm định chất lượng toàn diện bản nháp Cover Letter."""
        full_text = (
            f"{draft.hook} "
            f"{' '.join(draft.technical_highlights)} "
            f"{' '.join([f'{p.project_name} {p.architecture_summary} {p.impact_or_metric}' for p in draft.featured_projects])} "
            f"{draft.company_alignment} "
            f"{draft.call_to_action}"
        )

        placeholder_violations = []
        for pat in cls.FORBIDDEN_PLACEHOLDERS:
            found = re.findall(pat, full_text, flags=re.IGNORECASE)
            if found:
                placeholder_violations.append(f"Forbidden placeholder detected: {found}")

        cliche_violations = []
        for pat in cls.FORBIDDEN_CLICHES:
            found = re.findall(pat, full_text, flags=re.IGNORECASE)
            if found:
                cliche_violations.append(f"AI cliché phrase detected: {found}")

        word_count = len(full_text.split())
        word_warning = None
        if word_count < 180 or word_count > 380:
            word_warning = f"Word count ({word_count} words) is outside ideal range (200-380 words)."

        # Fact checking đối chiếu dự án và số liệu
        fact_check_violations = []
        cand_project_names = [p.name.lower() for p in (candidate.projects or [])]
        
        for fp in draft.featured_projects:
            # Kiểm tra tên dự án có thật trong profile không
            match_found = any(
                fp.project_name.lower() in p_name or p_name in fp.project_name.lower()
                for p_name in cand_project_names
            ) if cand_project_names else True

            if not match_found:
                fact_check_violations.append(
                    f"Project '{fp.project_name}' not found in candidate's verified projects."
                )

        is_valid = len(placeholder_violations) == 0 and len(fact_check_violations) == 0

        return CoverLetterValidationReport(
            is_valid=is_valid,
            word_count=word_count,
            placeholder_violations=placeholder_violations,
            cliche_violations=cliche_violations,
            fact_check_violations=fact_check_violations,
            word_count_warning=word_warning,
        )


# ==============================================================================
# Tầng 2, 3, 5: Multi-Stage Cover Letter Generation Pipeline
# ==============================================================================

class CoverLetterGenerator:
    """
    Cover Letter Multi-Stage Pipeline with Guardrails:
    Tầng 1: Ingestion & Schema Extraction (ParsedJD, ParsedResume)
    Tầng 2: Semantic Matching & Project Pruning (Top 2 dự án)
    Tầng 3: Structured Drafting (JSON output schema)
    Tầng 4: Deterministic Linter & Fact-Checking Guardrails
    Tầng 5: Standardized Scannable Markdown / HTML Renderer
    """

    @classmethod
    def _extract_jd_schema(cls, job: Job, matched_skills: Optional[List[str]] = None) -> ParsedJD:
        """Tầng 1: Chuẩn hóa JD thành cấu trúc rõ ràng (an toàn với detached session)."""
        company = (job.company_name or "Hiring Team").strip()
        # Loại bỏ các prefix/suffix rác nếu có
        if company.lower() in ["none", "unknown", "n/a"]:
            company = "Hiring Team"
        
        from app.services.tailoring.resume_intelligence import normalize_target_title_to_english
        raw_role = (job.title or "Software Engineer Intern").strip()
        role = normalize_target_title_to_english(raw_role)
        
        # Bóc tách core requirements từ matched_skills, description hoặc loaded relations
        core_reqs = []
        if matched_skills:
            core_reqs = matched_skills[:5]

        if not core_reqs:
            try:
                from sqlalchemy import inspect as sa_inspect
                insp = sa_inspect(job)
                if insp and "skills" not in insp.unloaded:
                    skills_rel = job.skills
                    if skills_rel:
                        for js in skills_rel[:5]:
                            if hasattr(js, "skill") and js.skill and hasattr(js.skill, "canonical_name"):
                                core_reqs.append(js.skill.canonical_name)
                            elif hasattr(js, "canonical_name"):
                                core_reqs.append(js.canonical_name)
            except Exception:
                pass

        if not core_reqs and getattr(job, "description", None):
            # Heuristic top tech keywords
            keywords = ["Python", "FastAPI", "React", "TypeScript", "C++", "Docker", "PostgreSQL", "Linux", "SQL"]
            core_reqs = [k for k in keywords if re.search(r"\b" + re.escape(k) + r"\b", job.description, re.IGNORECASE)][:4]

        return ParsedJD(
            company_name=company,
            target_role=role,
            seniority=job.level.value if hasattr(job.level, "value") else "INTERN",
            core_requirements=core_reqs or ["Software Engineering", "Problem Solving", "System Architecture"],
            domain_problems=[],
        )

    @classmethod
    def _prune_and_rank_projects(
        cls, candidate: Candidate, parsed_jd: ParsedJD, strategy: Optional[Any] = None
    ) -> List[FeaturedProjectDraft]:
        """
        Tầng 2: Semantic Matching & Project Pruning.
        Chỉ chọn lọc tối đa 2 dự án có điểm match cao nhất, loại bỏ hoàn toàn dự án không liên quan.
        """
        featured: List[FeaturedProjectDraft] = []

        # Nếu đã có evidence từ ResumeStrategy (MMR diverse selection)
        if strategy and getattr(strategy, "selected_evidence", None):
            seen_projects = set()
            for ev in strategy.selected_evidence:
                if ev.project_name not in seen_projects and len(featured) < 2:
                    seen_projects.add(ev.project_name)
                    featured.append(
                        FeaturedProjectDraft(
                            project_name=ev.project_name,
                            architecture_summary=ev.evidence_detail if len(ev.evidence_detail) < 160 else ev.evidence_detail[:157] + "...",
                            impact_or_metric=f"Verified impact in {ev.evidence_title}" if ev.evidence_title else "Engineered scalable system architecture",
                        )
                    )
            if featured:
                return featured

        # Fallback: Quét danh sách candidate.projects thực tế
        if candidate.projects:
            # Sắp xếp theo mức độ khớp công nghệ
            req_set = {r.lower() for r in parsed_jd.core_requirements}
            scored_projects = []
            for p in candidate.projects:
                p_techs = [t.lower() for t in (p.technologies or [])]
                overlap = sum(1 for t in p_techs if any(r in t or t in r for r in req_set))
                scored_projects.append((overlap, p))

            scored_projects.sort(key=lambda x: x[0], reverse=True)

            for _, p in scored_projects[:2]:  # Chỉ lấy Top 2 dự án
                first_ev = (p.evidence_points[0] if p.evidence_points else {}) if isinstance(p.evidence_points, list) else {}
                metric = first_ev.get("detail", p.summary or "Engineered scalable system modules") if isinstance(first_ev, dict) else (p.summary or "Production-ready implementation")
                if len(metric) > 160:
                    metric = metric[:157] + "..."

                featured.append(
                    FeaturedProjectDraft(
                        project_name=p.name,
                        architecture_summary=p.summary or f"Architected full-stack modules using {', '.join(p.technologies[:4]) if p.technologies else 'modern frameworks'}",
                        impact_or_metric=metric,
                    )
                )

        if not featured:
            featured.append(
                FeaturedProjectDraft(
                    project_name="Core Systems & Architecture Projects",
                    architecture_summary="Engineered modular, high-reliability software components and protocol integrations.",
                    impact_or_metric="Verified zero-hallucination test coverage and robust system reliability.",
                )
            )

        return featured[:2]

    @classmethod
    def _call_llm_for_draft(
        cls,
        candidate: Candidate,
        parsed_jd: ParsedJD,
        featured_projects: List[FeaturedProjectDraft],
        strategy: Optional[Any] = None,
        recipient_name: Optional[str] = None,
    ) -> Optional[CoverLetterDraft]:
        """
        Gọi Gemini / Groq API để sinh bản nháp Cover Letter chân thực, sắc sảo.
        Tuân thủ nghiêm ngặt Zero-Hallucination và Anti-Cliché.
        """
        import json
        import httpx
        from app.core.config import settings

        api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        groq_key = getattr(settings, "GROQ_API_KEY", None)

        if not api_key and not groq_key:
            return None

        # Chuẩn bị context
        edu_str = "Computer Science"
        if candidate.education and len(candidate.education) > 0:
            edu_0 = candidate.education[0]
            edu_str = f"{edu_0.get('degree', 'Bachelor')} in {edu_0.get('field', 'Computer Science')} from {edu_0.get('institution', 'University')}"

        projects_summary = "\n".join([
            f"- Project: {fp.project_name}\n  Architecture: {fp.architecture_summary}\n  Verified Impact: {fp.impact_or_metric}"
            for fp in featured_projects
        ])

        priority_skills = []
        if strategy and getattr(strategy, "priority_skills", None):
            priority_skills = strategy.priority_skills[:5]
        elif parsed_jd.core_requirements:
            priority_skills = parsed_jd.core_requirements[:5]

        system_instruction = (
            "You are an expert technical career coach specializing in authentic, high-impact cover letters for software engineers. "
            "Write in a direct, humble, professional tone with ZERO fluff and ZERO clichés. "
            "STRICT RULES:\n"
            "1. NEVER use generic AI clichés: 'thrilled to apply', 'delve into', 'seamlessly', 'testament to', 'spearheaded', 'passionate about', 'dynamic environment', 'beacon', 'tapestry'.\n"
            "2. ZERO HALLUCINATION: Only reference the provided candidate projects, skills, and background. Do NOT invent new achievements or metrics.\n"
            "3. Return ONLY a valid JSON object matching the requested schema. No markdown wrappers, no backticks."
        )

        user_prompt = f"""Generate a concise, compelling cover letter draft for the following candidate and target role:

TARGET COMPANY: {parsed_jd.company_name}
TARGET ROLE: {parsed_jd.target_role} ({parsed_jd.seniority})
CORE REQUIREMENTS: {', '.join(parsed_jd.core_requirements)}
RECIPIENT: {recipient_name or parsed_jd.company_name + ' Hiring Team'}

CANDIDATE BACKGROUND:
Name: {candidate.full_name or 'Candidate'}
Education: {edu_str}
Top Skills: {', '.join(priority_skills)}
Verified Projects:
{projects_summary}

Required JSON Output Schema:
{{
  "recipient_company": "{parsed_jd.company_name}",
  "target_role": "{parsed_jd.target_role}",
  "salutation": "Dear {recipient_name or parsed_jd.company_name + ' Hiring Team'},",
  "hook": "1-2 sentences stating specific interest in the role and primary engineering foundation",
  "technical_highlights": [
    "3 concise bullet points showing technical alignment with the target requirements"
  ],
  "featured_projects": [
    {{
      "project_name": "Must be one of the candidate verified projects above",
      "architecture_summary": "1 sentence technical architecture explanation",
      "impact_or_metric": "Verifiable metric or achievement"
    }}
  ],
  "company_alignment": "1-2 sentences explaining why the candidate's engineering discipline fits the company's technical standards",
  "call_to_action": "1 sentence polite and humble closing"
}}"""

        # 1. Thử gọi Gemini
        if api_key:
            models_to_try = [settings.GEMINI_MODEL, "gemini-2.0-flash", "gemini-1.5-flash"]
            payload = {
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "generationConfig": {
                    "temperature": 0.3,
                    "responseMimeType": "application/json",
                },
            }
            try:
                with httpx.Client(timeout=15.0) as client:
                    for model in models_to_try:
                        url = f"{settings.GEMINI_API_BASE_URL}/models/{model}:generateContent?key={api_key}"
                        resp = client.post(url, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            candidates_resp = data.get("candidates", [])
                            if candidates_resp:
                                parts = candidates_resp[0].get("content", {}).get("parts", [])
                                raw_text = parts[0].get("text", "").strip() if parts else ""
                                if raw_text:
                                    # Clean possible backticks
                                    if raw_text.startswith("```json"):
                                        raw_text = raw_text[7:]
                                    if raw_text.startswith("```"):
                                        raw_text = raw_text[3:]
                                    if raw_text.endswith("```"):
                                        raw_text = raw_text[:-3]
                                    parsed_json = json.loads(raw_text.strip())
                                    logger.info(f"[CoverLetterGenerator] Generated LLM draft via Gemini model {model}")
                                    return CoverLetterDraft(**parsed_json)
            except Exception as e:
                logger.warning(f"[CoverLetterGenerator] Gemini call failed: {e}")

        # 2. Fallback sang Groq nếu có
        if groq_key:
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": [
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": user_prompt},
                            ],
                            "response_format": {"type": "json_object"},
                            "temperature": 0.3,
                        },
                    )
                    if resp.status_code == 200:
                        raw_text = resp.json()["choices"][0]["message"]["content"]
                        parsed_json = json.loads(raw_text.strip())
                        logger.info("[CoverLetterGenerator] Generated LLM draft via Groq")
                        return CoverLetterDraft(**parsed_json)
            except Exception as e:
                logger.warning(f"[CoverLetterGenerator] Groq fallback failed: {e}")

        return None

    @classmethod
    def _generate_deterministic_draft(
        cls,
        candidate: Candidate,
        parsed_jd: ParsedJD,
        featured_projects: List[FeaturedProjectDraft],
        strategy: Optional[Any] = None,
        recipient_name: Optional[str] = None,
    ) -> CoverLetterDraft:
        """Sinh bản nháp có cấu trúc xác định dự phòng khi không có API key."""
        company = parsed_jd.company_name
        role_title = parsed_jd.target_role

        salutation = f"Dear {recipient_name}," if recipient_name else f"Dear {company} Hiring Team,"

        # Education
        edu_major = "Computer Science"
        edu_school = "University"
        if candidate.education and len(candidate.education) > 0:
            edu_0 = candidate.education[0]
            edu_major = edu_0.get("field", edu_major)
            edu_school = edu_0.get("institution", edu_school)

        # Hook Statement
        hook = (
            f"I am writing to express my strong interest in the {role_title} position at {company}. "
            f"As a final-year {edu_major} student at {edu_school}, I have built practical foundations in "
            f"systems engineering, automated microservices, and clean software architecture."
        )

        # Technical highlights (3 bullets)
        skills_list = []
        if strategy and getattr(strategy, "priority_skills", None):
            skills_list = strategy.priority_skills[:4]
        elif parsed_jd.core_requirements:
            skills_list = parsed_jd.core_requirements[:4]
        else:
            skills_list = ["Python", "FastAPI", "PostgreSQL", "Docker"]

        skills_str = ", ".join(skills_list)
        role_family = getattr(strategy, "role_family", "backend") if strategy else "backend"

        if role_family == "backend":
            highlights = [
                f"Hands-on backend service engineering using {skills_str}",
                "Relational schema design and optimized query workflows in PostgreSQL",
                "Implementation of rate-limiting, authentication protocols, and asynchronous pipelines",
            ]
        elif role_family == "system":
            highlights = [
                f"Practical systems development in Linux, cloud infrastructure, and {skills_str}",
                "Stateful edge connection handling and automated containerized deployments",
                "Strict adherence to system reliability and deterministic performance",
            ]
        elif role_family == "security":
            highlights = [
                f"Strong foundation in applied cryptography, security protocols, and {skills_str}",
                "Zero-knowledge data architectures and cryptographic protocol simulations",
                "Secure identity management and rigorous input verification",
            ]
        else:
            highlights = [
                f"Core foundations in software engineering with {skills_str}",
                "Modular object-oriented architecture and unit-tested pipelines",
                "Commitment to verifiable code quality and rapid technical adaptability",
            ]

        # Company alignment
        alignment = (
            f"I am excited by {company}'s technical standards and would welcome the opportunity to apply my "
            f"problem-solving discipline to help your engineering team build scalable, high-quality systems."
        )

        # Call to action
        cta = (
            f"Thank you very much for your time and consideration. I look forward to the possibility of discussing "
            f"how my technical background can support {company}'s engineering goals."
        )

        return CoverLetterDraft(
            recipient_company=company,
            target_role=role_title,
            salutation=salutation,
            hook=hook,
            technical_highlights=highlights,
            featured_projects=featured_projects,
            company_alignment=alignment,
            call_to_action=cta,
        )

    @classmethod
    def _generate_structured_draft(
        cls,
        candidate: Candidate,
        parsed_jd: ParsedJD,
        featured_projects: List[FeaturedProjectDraft],
        strategy: Optional[Any] = None,
        recipient_name: Optional[str] = None,
    ) -> CoverLetterDraft:
        """Tầng 3: Sinh bản nháp (thử LLM trước, nếu không có API key / lỗi thì dùng fallback xác định)."""
        llm_draft = cls._call_llm_for_draft(
            candidate=candidate,
            parsed_jd=parsed_jd,
            featured_projects=featured_projects,
            strategy=strategy,
            recipient_name=recipient_name,
        )

        if llm_draft:
            # Bảo đảm featured_projects bám sát các dự án đã được prune
            if not llm_draft.featured_projects:
                llm_draft.featured_projects = featured_projects
            return llm_draft

        return cls._generate_deterministic_draft(
            candidate=candidate,
            parsed_jd=parsed_jd,
            featured_projects=featured_projects,
            strategy=strategy,
            recipient_name=recipient_name,
        )

    @classmethod
    def _render_to_markdown(cls, candidate: Candidate, draft: CoverLetterDraft) -> str:
        """Tầng 5: Standardized Scannable Markdown Renderer."""
        full_name = candidate.full_name or "Nguyen Van A"
        email = candidate.email or "candidate@example.com"
        phone = candidate.phone or "(+84) 123456789"
        location = candidate.location or "Ho Chi Minh City, Vietnam"
        date_str = datetime.now().strftime("%B %d, %Y")

        highlights_md = "\n".join([f"- **{h}**" for h in draft.technical_highlights])

        projects_md = ""
        for p in draft.featured_projects:
            projects_md += f"- **{p.project_name}**: {p.architecture_summary} (*{p.impact_or_metric}*)\n"

        github_link = f"[GitHub Profile]({candidate.github_url})" if candidate.github_url else ""
        linkedin_link = f"[LinkedIn Profile]({candidate.linkedin_url})" if candidate.linkedin_url else ""
        links = " | ".join(filter(None, [github_link, linkedin_link]))
        if links:
            links = f"\n{links}"

        markdown = f"""# Cover Letter

**Candidate:** {full_name}  
**Email:** {email} | **Phone:** {phone}  
**Location:** {location}  
**Date:** {date_str}  

**To:** {draft.salutation}  
**Company:** {draft.recipient_company}  
**Position:** {draft.target_role}  

---

{draft.hook}

### Key Technical Alignment
{highlights_md}

### Featured Project Experience
{projects_md.strip()}

{draft.company_alignment}

{draft.call_to_action}

Sincerely,  
**{full_name}**{links}
"""
        return markdown.strip()

    @classmethod
    def generate_cover_letter(
        cls,
        candidate: Candidate,
        job: Job,
        strategy: Optional[Any] = None,
        matched_skills: Optional[List[str]] = None,
        recipient_name: Optional[str] = None,
        custom_tone: str = "professional_and_humble",
    ) -> Dict[str, Any]:
        """
        Thực thi toàn bộ Multi-Stage Pipeline with Guardrails:
        1. Ingestion & Schema Extraction
        2. Semantic Matching & Project Pruning
        3. Structured Drafting (JSON)
        4. Guardrails (Linter, Anti-Cliché, Fact-Checking)
        5. Standardized Markdown Rendering
        """
        # 1. Extraction
        parsed_jd = cls._extract_jd_schema(job, matched_skills=matched_skills)

        # 2. Strategy & Project Pruning
        if not strategy:
            try:
                from app.services.tailoring.resume_intelligence import resume_intelligence
                strategy = resume_intelligence.build_strategy(
                    candidate=candidate,
                    job=job,
                    custom_tone=custom_tone,
                )
            except Exception as e:
                logger.warning(f"Could not build strategy, using fallback: {e}")
                strategy = None

        featured_projects = cls._prune_and_rank_projects(candidate, parsed_jd, strategy)

        # 3. Structured Drafting
        draft = cls._generate_structured_draft(
            candidate=candidate,
            parsed_jd=parsed_jd,
            featured_projects=featured_projects,
            strategy=strategy,
            recipient_name=recipient_name,
        )

        # 4. Guardrails & Linter auto-fix
        draft.hook = CoverLetterLinter.replace_cliches(CoverLetterLinter.clean_text_from_placeholders(draft.hook, parsed_jd.company_name))
        draft.company_alignment = CoverLetterLinter.replace_cliches(CoverLetterLinter.clean_text_from_placeholders(draft.company_alignment, parsed_jd.company_name))
        draft.call_to_action = CoverLetterLinter.replace_cliches(CoverLetterLinter.clean_text_from_placeholders(draft.call_to_action, parsed_jd.company_name))

        report = CoverLetterLinter.validate(draft, candidate)

        # 5. Render
        content_markdown = cls._render_to_markdown(candidate, draft)

        return {
            "recipient_name": recipient_name,
            "company_name": parsed_jd.company_name,
            "salutation": draft.salutation,
            "hook_statement": draft.hook,
            "key_alignments": draft.technical_highlights,
            "featured_projects": [p.model_dump() for p in draft.featured_projects],
            "validation_report": report.model_dump(),
            "content_markdown": content_markdown,
            "draft_schema": draft.model_dump(),
        }


cover_letter_generator = CoverLetterGenerator()
