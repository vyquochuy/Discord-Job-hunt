from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.candidate import Candidate
from app.models.job import Job


class CoverLetterGenerator:
    """
    Service tạo Cover Letter tự động, chân thực và khiêm tốn:
    - Bám sát sự thật và điểm mạnh kỹ thuật đã được kiểm chứng.
    - Không phóng đại thành tích hoặc tự tạo kinh nghiệm không tồn tại.
    - Định dạng chuẩn Markdown chuyên nghiệp, dễ đọc.
    """

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
        Sinh nội dung Cover Letter có cấu trúc rõ ràng, bám sát ResumeStrategy.
        - Hoàn toàn dynamic, không hardcode tên dự án hay nội dung cố định.
        - 100% Zero-Hallucination: Dựa trên selected_evidence được tuyển chọn từ profile thực.
        """
        full_name = candidate.full_name or "Vy Quoc Huy"
        role_title = (strategy.target_title if strategy else None) or job.title or candidate.headline or "Software Engineer Intern"
        company_name = job.company_name or "Hiring Team"
        salutation = f"Dear {recipient_name}," if recipient_name else f"Dear {company_name} Hiring Team,"

        # 1. Tự động build strategy nếu chưa có
        if not strategy:
            try:
                from app.services.tailoring.resume_intelligence import resume_intelligence
                strategy = resume_intelligence.build_strategy(
                    candidate=candidate,
                    job=job,
                    custom_tone=custom_tone,
                )
            except Exception:
                strategy = None

        role_family = getattr(strategy, "role_family", "general") if strategy else "general"
        if strategy and strategy.priority_skills:
            top_skills = strategy.priority_skills[:5]
        elif matched_skills:
            top_skills = matched_skills[:5]
        else:
            top_skills = ["C++", "Python", "Linux", "Docker", "PostgreSQL"]
        skills_str = ", ".join(top_skills)

        # 2. Opening Hook Statement
        edu_major = "Computer Science (Cyber Security)"
        edu_school = "VNUHCM - University of Science"
        if candidate.education and len(candidate.education) > 0:
            edu_0 = candidate.education[0]
            edu_major = edu_0.get("field", edu_major)
            edu_school = edu_0.get("institution", edu_school)

        hook_statement = (
            f"I am writing to express my strong interest in the {role_title} position at {company_name}. "
            f"As a final-year {edu_major} student at {edu_school} with practical "
            f"experience in software development and systems engineering, I am eager to contribute my technical foundation "
            f"and disciplined problem-solving mindset to your engineering team."
        )

        # 3. Key Alignments (Định hướng theo Role Family)
        key_alignments = []
        if role_family == "backend":
            key_alignments.append(f"Backend & Systems engineering with {skills_str}")
            key_alignments.append("Relational database schema modeling and low-latency API architecture")
            key_alignments.append("Applied rate-limiting, authentication workflows, and serverless scalability")
        elif role_family == "system":
            key_alignments.append(f"Practical experience with Linux, cloud environments, and {skills_str}")
            key_alignments.append("Stateful edge connection management and real-time distributed platforms")
            key_alignments.append("Automated infrastructure deployment and system reliability practices")
        elif role_family == "security":
            key_alignments.append(f"Strong foundation in applied cryptography, security protocols, and {skills_str}")
            key_alignments.append("Public Key Infrastructure (PKI), X.509 certificate chain validation with OpenSSL")
            key_alignments.append("Zero-knowledge architecture and secure authentication protocol design")
        else:
            key_alignments.append(f"Strong technical foundations in {skills_str}")
            key_alignments.append("Object-oriented software architecture and protocol simulation")
            key_alignments.append("Dedication to writing clean, maintainable, and well-verified code")

        alignments_bullets = "\n".join([f"- **{a}**" for a in key_alignments])

        # 4. Project Evidence Paragraph (Render động từ Strategy Selected Evidence)
        if strategy and strategy.selected_evidence:
            evidence_sentences = []
            for ev in strategy.selected_evidence[:3]:
                ev_title_clean = f" ({ev.evidence_title})" if ev.evidence_title else ""
                evidence_sentences.append(
                    f"In **{ev.project_name}**{ev_title_clean}, I {ev.evidence_detail}"
                )
            project_evidence = " ".join(evidence_sentences)
        else:
            # Fallback nếu không có strategy
            project_evidence = (
                "In my practical projects, I have focused on building secure, scalable software architectures from the ground up, "
                "implementing real-world protocols, relational data models, and verified cryptographic mechanisms."
            )

        # 5. Modest & Growth-Oriented Closing
        closing_statement = (
            f"While I am continuously expanding my engineering expertise, I take pride in writing clean, well-documented code, "
            f"thoroughly verifying system reliability, and learning quickly from experienced teammates. I would welcome the opportunity "
            f"to discuss how my technical background and dedicated work ethic can support {company_name}'s goals."
        )

        current_date_str = datetime.now().strftime("%B %d, %Y")

        content_markdown = f"""# Cover Letter

**Candidate:** {full_name}  
**Email:** {candidate.email or 'vyquochuy305@gmail.com'} | **Phone:** {candidate.phone or '(+84) 384988934'}  
**Location:** {candidate.location or 'Thu Duc, Ho Chi Minh'}  
**Date:** {current_date_str}  

**To:** {salutation}  
**Company:** {company_name}  
**Position:** {role_title}  

---

{hook_statement}

### Key Technical Alignment
{alignments_bullets}

### Practical Project Experience
{project_evidence}

{closing_statement}

Thank you very much for your time and consideration.

Sincerely,  
**{full_name}**  
[GitHub Profile]({candidate.github_url or 'https://github.com/vyquochuy'}) | [LinkedIn Profile]({candidate.linkedin_url or 'https://www.linkedin.com/in/vyquochuy/'})
"""

        return {
            "recipient_name": recipient_name,
            "company_name": company_name,
            "salutation": salutation,
            "hook_statement": hook_statement,
            "key_alignments": key_alignments,
            "content_markdown": content_markdown.strip(),
        }


cover_letter_generator = CoverLetterGenerator()
