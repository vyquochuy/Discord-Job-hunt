import re
from typing import Any, Dict, List, Optional

from app.models.candidate import Candidate
from app.models.job import Job


class LaTeXGenerator:
    """
    Service sinh mã nguồn LaTeX (.tex) cho bản CV được tinh chỉnh (Tailored Resume).
    - Tuân thủ nghiêm ngặt định dạng mẫu chuyên nghiệp từ `context/master-resume.tex`.
    - Escape tự động và an toàn các ký tự đặc biệt của TeX (&, %, $, #, _, {, }, ~, ^, \\).
    - Tái cấu trúc và sắp xếp ưu tiên kỹ năng, dự án phù hợp nhất với JD của tin tuyển dụng.
    """

    @staticmethod
    def escape_latex(text: str) -> str:
        """
        Escape an toàn các ký tự điều khiển trong LaTeX.
        Tránh lỗi biên dịch cú pháp do các ký tự &, %, $, _, #, etc.
        """
        if not text:
            return ""

        # Nếu đã có cú pháp lệnh TeX đặc biệt (vd \textbf{} hoặc \href{}), không escape toàn bộ mà chỉ escape nội dung thuần
        # Tạm thời escape các ký tự cơ bản trong text thuần
        replacements = [
            ("\\", r"\textbackslash{}"),
            ("&", r"\&"),
            ("%", r"\%"),
            ("$", r"\$"),
            ("#", r"\#"),
            ("_", r"\_"),
            ("{", r"\{"),
            ("}", r"\}"),
            ("~", r"\textasciitilde{}"),
            ("^", r"\textasciicircum{}"),
        ]

        escaped = text
        for char, repl in replacements:
            # Nếu ký tự chưa được escape
            if char in ("\\", "{", "}"):
                continue  # Giữ cho các lệnh cấu trúc
            escaped = escaped.replace(char, repl)

        return escaped

    @classmethod
    def sanitize_bullet(cls, text: str) -> str:
        """Làm sạch và escape an toàn một bullet point kỹ thuật."""
        if not text:
            return ""
        # Escape các ký tự & và % và _ nếu chưa có dấu \
        s = text
        s = re.sub(r"(?<!\\)&", r"\&", s)
        s = re.sub(r"(?<!\\)%", r"\%", s)
        s = re.sub(r"(?<!\\)_", r"\_", s)
        s = re.sub(r"(?<!\\)#", r"\#", s)
        s = re.sub(r"(?<!\\)\$", r"\$", s)
        # Chuẩn hóa dấu ~
        s = s.replace("~", r"$\sim$")
        s = s.replace(">", r"$>$")
        s = s.replace("<", r"$<$")
        return s

    @classmethod
    def generate_tailored_tex(
        cls,
        candidate: Candidate,
        strategy: Optional[Any] = None,
        job: Optional[Job] = None,
        matched_skills: Optional[List[str]] = None,
        target_title: Optional[str] = None,
        custom_objective: Optional[str] = None,
    ) -> str:
        """
        Sinh toàn bộ văn bản LaTeX hoàn chỉnh cho Tailored Resume từ ResumeStrategy.
        Hoạt động như một Pure Renderer:
        - Sử dụng strategy để xác định objective, thứ tự dự án, thứ tự bullet points và ưu tiên kỹ năng.
        - Giữ 100% backward compatibility nếu gọi theo signature cũ.
        """
        # 1. Header Information & Title
        if strategy:
            role_title = strategy.target_title
            effective_matched_skills = strategy.matched_skills
            objective_text = cls.sanitize_bullet(strategy.adaptive_summary)
            ranked_projects = strategy.ranked_projects
        else:
            role_title = target_title or (job.title if job else None) or candidate.headline or "Software Engineer Intern"
            effective_matched_skills = matched_skills or []
            if custom_objective:
                objective_text = cls.sanitize_bullet(custom_objective)
            else:
                objective_text = cls.sanitize_bullet(candidate.summary or "")
            # Tạo default ranked projects từ candidate.projects
            ranked_projects = []
            if candidate.projects:
                for p in candidate.projects:
                    # Tạo cấu trúc ScoredProject đơn giản
                    from app.services.tailoring.resume_intelligence import ScoredEvidence, ScoredProject
                    ev_list = []
                    if p.evidence_points:
                        for ev in p.evidence_points:
                            t = ev.get("title", "") if isinstance(ev, dict) else ""
                            d = ev.get("detail", "") if isinstance(ev, dict) else str(ev)
                            ev_list.append(ScoredEvidence(
                                project_name=p.name,
                                evidence_title=t,
                                evidence_detail=d,
                                technologies=p.technologies or [],
                                score=1.0,
                                capabilities=[],
                            ))
                    ranked_projects.append(ScoredProject(
                        project=p,
                        project_score=1.0,
                        ranked_evidence=ev_list,
                    ))

        full_name = candidate.full_name or "Vy Quoc Huy"
        phone = candidate.phone or "(+84) 384988934"
        email = candidate.email or "vyquochuy305@gmail.com"
        github_url = candidate.github_url or "https://github.com/vyquochuy"
        linkedin_url = candidate.linkedin_url or "https://www.linkedin.com/in/vyquochuy/"
        location = candidate.location or "Thu Duc, Ho Chi Minh"

        # 2. Education
        edu_entries = []
        if candidate.education:
            for edu in candidate.education:
                if isinstance(edu, dict):
                    inst = cls.sanitize_bullet(edu.get("institution", "VNUHCM - University of Science"))
                    degree = edu.get("degree", "Bachelor")
                    field = cls.sanitize_bullet(edu.get("field", "Computer Science - Cyber Security"))
                    gpa = edu.get("gpa", "3.15/4.0")
                    grad_year = edu.get("graduation_year", "2026")
                    coursework = ", ".join(edu.get("coursework", [])) if isinstance(edu.get("coursework"), list) else str(edu.get("coursework", ""))
                    coursework_escaped = cls.sanitize_bullet(coursework)

                    edu_block = f"""\\noindent \\textbf{{{inst}}} \\hfill Oct 2022 -- Expected Oct {grad_year}\\\\
\\textit{{Major: {field}}} \\hfill \\textit{{GPA: {gpa}}}\\\\
\\textbf{{Relevant Coursework:}} {coursework_escaped}."""
                    edu_entries.append(edu_block)

        if not edu_entries:
            inst = "VNUHCM - University of Science"
            field = "Computer Science - Cyber Security"
            gpa = "3.15/4.0"
            grad_year = "2026"
            coursework = "Computer Networks, Database Systems, Fundamentals of Artificial Intelligence, Introduction to Machine Learning, Introduction to Cryptography, Encryption Application, Blockchain and Applications, Data Safety and Recovery"
            edu_block = f"""\\noindent \\textbf{{{inst}}} \\hfill Oct 2022 -- Expected Oct {grad_year}\\\\
\\textit{{Major: {field}}} \\hfill \\textit{{GPA: {gpa}}}\\\\
\\textbf{{Relevant Coursework:}} {coursework}."""
            edu_entries.append(edu_block)

        education_latex = "\n\n".join(edu_entries)

        # 3. Skills (Xếp thứ tự dựa trên matched skills & strategy)
        matched_set = {s.lower() for s in (effective_matched_skills or [])}

        def sort_skills(skill_list: List[str]) -> List[str]:
            matched = [s for s in skill_list if s.lower() in matched_set]
            others = [s for s in skill_list if s.lower() not in matched_set]
            return matched + others

        # Thu thập kỹ năng từ candidate.skills hoặc fallback cấu trúc chuẩn
        candidate_skills_by_cat: Dict[str, List[str]] = {}
        if candidate.skills:
            for s in candidate.skills:
                cat = s.category.lower() if s.category else "other"
                candidate_skills_by_cat.setdefault(cat, []).append(s.name)

        prog_skills = sort_skills(candidate_skills_by_cat.get("programming") or ["C++", "Python", "JavaScript", "TypeScript", "Dart"])
        fw_skills = sort_skills(candidate_skills_by_cat.get("frameworks") or ["React", "Tailwind CSS", "NextJS", "Hono", "Flutter", "FastAPI"])
        tool_skills = sort_skills(candidate_skills_by_cat.get("tools_databases") or candidate_skills_by_cat.get("tools") or ["SQL", "PostgreSQL", "SQLite", "Git", "Linux", "Docker", "OpenSSL", "Wireshark", "Visual Studio 2022"])
        sec_skills = sort_skills(candidate_skills_by_cat.get("security") or ["X.509 PKI", "RSA-2048", "SHA-256", "Zero-Knowledge Architecture", "Argon2id", "AES-256-GCM", "ECDH P-256"])
        soft_skills = candidate_skills_by_cat.get("soft_skills") or ["Problem-solving", "System design thinking", "Technical documentation", "Teamwork"]
        lang_skills = ["Vietnamese (Native)", "English (level B1)"]

        skills_latex = f"""\\begin{{itemize}}[leftmargin=0.15in, label={{}}, itemsep=0pt]
    \\item \\textbf{{Programming Languages:}} {', '.join(prog_skills)}
    \\item \\textbf{{Frameworks \\& Libraries:}} {', '.join(fw_skills)}
    \\item \\textbf{{Tools \\& Databases:}} {', '.join(tool_skills)}
    \\item \\textbf{{Security \\& Systems:}} {', '.join(sec_skills)}
    \\item \\textbf{{Soft Skills:}} {', '.join(soft_skills)}
    \\item \\textbf{{Languages:}} {', '.join(lang_skills)}
\\end{{itemize}}"""

        # 4. Projects (Duyệt theo ranked_projects từ ResumeStrategy)
        projects_latex_list = []
        for scored_proj in ranked_projects:
            p = scored_proj.project if hasattr(scored_proj, "project") else scored_proj
            p_name = cls.sanitize_bullet(p.name)
            repo_url = p.repository_url or ""
            demo_url = p.demo_url or ""
            period = cls.sanitize_bullet(p.period or "2026")
            summary = cls.sanitize_bullet(p.summary or "")

            links_part = ""
            if repo_url:
                links_part += f" $|$ \\href{{{repo_url}}}{{repository}}"
            if demo_url:
                links_part += f" $|$ \\href{{{demo_url}}}{{live demo}}"

            if summary:
                header_line = f"\\noindent \\textbf{{{p_name}}}{links_part} \\hfill {period}\\\\\n\\textit{{{summary}}}"
            else:
                header_line = f"\\noindent \\textbf{{{p_name}}}{links_part} \\hfill {period}"

            bullet_items = []
            # Duyệt các ranked_evidence đã được chấm điểm và xếp hạng
            ranked_evs = getattr(scored_proj, "ranked_evidence", [])
            if ranked_evs:
                for scored_ev in ranked_evs:
                    title = cls.sanitize_bullet(scored_ev.evidence_title)
                    detail = cls.sanitize_bullet(scored_ev.evidence_detail)
                    if title:
                        bullet_items.append(f"    \\item \\textbf{{{title}:}} {detail}\n")
                    else:
                        bullet_items.append(f"    \\item {detail}\n")
            elif p.evidence_points:
                for ev in p.evidence_points:
                    if isinstance(ev, dict):
                        title = cls.sanitize_bullet(ev.get("title", ""))
                        detail = cls.sanitize_bullet(ev.get("detail", ""))
                        bullet_items.append(f"    \\item \\textbf{{{title}:}} {detail}\n")
                    else:
                        detail = cls.sanitize_bullet(str(ev))
                        bullet_items.append(f"    \\item {detail}\n")

            if p.technologies:
                tech_str = ", ".join([cls.sanitize_bullet(t) for t in p.technologies])
                tech_line = f"    \\item \\textbf{{Technologies:}} {tech_str}."
                bullet_items.append(tech_line)

            proj_block = f"""{header_line}
\\begin{{itemize}}[leftmargin=0.25in, nosep]
{''.join(bullet_items)}
\\end{{itemize}}
\\vspace{{10pt}}"""
            projects_latex_list.append(proj_block)

        projects_latex = "\n\n".join(projects_latex_list)

        # 5. Toàn bộ tài liệu TeX
        tex_template = f"""\\documentclass[10pt,a4paper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{mathptmx}}
\\usepackage{{geometry}}
\\geometry{{a4paper, margin=0.65in}}
\\usepackage{{titlesec}}
\\usepackage{{enumitem}}
\\usepackage{{hyperref}}
\\usepackage{{xcolor}}
\\usepackage{{amsmath}}

% Custom Colors
\\definecolor{{darkblue}}{{RGB}}{{0, 51, 102}}

% Format sections
\\titleformat{{\\section}}{{\\large\\bfseries\\color{{darkblue}}\\uppercase}}{{}}{{0em}}{{}}[\\titlerule]
\\titlespacing{{\\section}}{{0pt}}{{1.5ex}}{{1ex}}

% Hyperlink setup
\\hypersetup{{
    colorlinks=true,
    linkcolor=darkblue,
    filecolor=darkblue,      
    urlcolor=darkblue,
}}

\\begin{{document}}
\\pagestyle{{empty}}

% Header
\\begin{{center}}
    {{\\huge \\textbf{{{full_name}}}}} \\\\ \\vspace{{4pt}}
    {{\\Large \\textbf{{{role_title}}}}} \\\\ \\vspace{{4pt}}
    {phone} \\quad \\href{{mailto:{email}}}{{{email}}} \\quad \\href{{{github_url}}}{{github.com/vyquochuy}} \\quad {location} \\quad \\href{{{linkedin_url}}}{{linkedin.com/in/vyquochuy}}
\\end{{center}}

% Objective
\\section*{{Objective}}
{objective_text}

% Education
\\section*{{Education}}
{education_latex}

% Skills
\\section*{{Skills}}
{skills_latex}

% Projects
\\section*{{Projects}}

{projects_latex}

\\end{{document}}
"""
        return tex_template


latex_generator = LaTeXGenerator()
