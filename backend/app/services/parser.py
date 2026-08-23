import io
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pypdf import PdfReader

logger = logging.getLogger("parser")


class CandidateProfileParser:
    """
    Parser chịu trách nhiệm phân tích cú pháp và trích xuất dữ liệu từ các file ngữ cảnh:
    - candidate-profile.yaml (hoặc .yml)
    - master-resume.tex (LaTeX)
    - master-resume.md (Markdown)
    - resume.pdf (PDF documents via pypdf)
    - JSON profile data
    """

    @staticmethod
    def parse_yaml(content: str) -> Dict[str, Any]:
        """Parse nội dung file candidate-profile.yaml."""
        if not content or not content.strip():
            return {}
        data = yaml.safe_load(content) or {}
        return data

    @staticmethod
    def parse_latex(content: str) -> Dict[str, Any]:
        """
        Trích xuất các thông tin chính từ file LaTeX .tex (Header, Objective, Education, Skills, Projects).
        """
        result: Dict[str, Any] = {
            "candidate": {},
            "education": [],
            "skills": {},
            "projects": [],
            "experience": [],
        }

        # 1. Trích xuất Tên ứng viên
        name_match = re.search(r"\{\\huge\s+\\textbf\{([^}]+)\}\}", content)
        if not name_match:
            name_match = re.search(r"\\textbf\{\\Huge\s+([^}]+)\}", content)
        if name_match:
            result["candidate"]["name"] = name_match.group(1).strip()

        # 2. Trích xuất Headline
        headline_match = re.search(r"\{\\Large\s+\\textbf\{([^}]+)\}\}", content)
        if not headline_match:
            headline_match = re.search(r"\\textbf\{\\large\s+([^}]+)\}", content)
        if headline_match:
            result["candidate"]["headline"] = headline_match.group(1).strip()

        # 3. Trích xuất Liên hệ: Phone, Email, GitHub, LinkedIn, Location
        phone_match = re.search(r"(\(?\+?\d{1,3}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4})", content)
        if phone_match:
            result["candidate"]["phone"] = phone_match.group(1).strip()

        email_match = re.search(r"\\href\{mailto:([^}]+)\}", content)
        if not email_match:
            email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", content)
        if email_match:
            result["candidate"]["email"] = email_match.group(1).strip()

        github_match = re.search(r"\\href\{https?://github\.com/([^}]+)\}", content)
        if github_match:
            result["candidate"]["github"] = f"https://github.com/{github_match.group(1).strip()}"

        linkedin_match = re.search(r"\\href\{https?://(?:www\.)?linkedin\.com/in/([^/]+)/?\}", content)
        if linkedin_match:
            result["candidate"]["linkedin"] = f"https://www.linkedin.com/in/{linkedin_match.group(1).strip()}/"

        location_match = re.search(r"(?:\\faMapMarker\s*\\quad\s*|\\quad\s+)([^\\|\n\t]+(?:Ho Chi Minh|Hanoi|Da Nang|Thu Duc|Vietnam)[^\\|\n\t]*)", content, re.IGNORECASE)
        if location_match:
            result["candidate"]["location"] = location_match.group(1).strip()

        # 4. Trích xuất Objective / Summary
        obj_match = re.search(r"\\section\*?\{(?:Objective|Summary)\}\s*([\s\S]*?)(?=\\section\*?|\Z)", content, re.IGNORECASE)
        if obj_match and obj_match.group(1):
            obj_text = re.sub(r"%.*$", "", obj_match.group(1), flags=re.MULTILINE)
            result["candidate"]["summary"] = obj_text.strip()

        # 5. Trích xuất Education
        edu_match = re.search(r"\\section\*?\{Education\}\s*([\s\S]*?)(?=\\section\*?|\Z)", content, re.IGNORECASE)
        if edu_match and edu_match.group(1):
            edu_text = edu_match.group(1)
            inst_match = re.search(r"\\textbf\{([^}]+)\}", edu_text)
            institution = inst_match.group(1) if inst_match else ""
            
            gpa_match = re.search(r"GPA:\s*([0-9\./]+)", edu_text)
            gpa = gpa_match.group(1) if gpa_match else None

            major_match = re.search(r"(?:Major|Bachelor of Science in|Degree):\s*([^\\}\n]+)", edu_text, re.IGNORECASE)
            major = major_match.group(1).strip() if major_match else "Computer Science"

            coursework_match = re.search(r"Relevant Coursework:\s*([^\n\\]+)", edu_text, re.IGNORECASE)
            coursework = []
            if coursework_match and coursework_match.group(1):
                coursework = [c.strip() for c in coursework_match.group(1).split(",") if c.strip()]

            if institution or major:
                result["education"].append({
                    "institution": institution or "University",
                    "degree": "Bachelor",
                    "field": major,
                    "graduation_year": 2026,
                    "gpa": gpa,
                    "coursework": coursework,
                })

        # 6. Trích xuất Skills
        skills_match = re.search(r"\\section\*?\{Skills\}\s*([\s\S]*?)(?=\\section\*?|\Z)", content, re.IGNORECASE)
        if skills_match and skills_match.group(1):
            skills_text = skills_match.group(1)
            for item in re.finditer(r"\\item\s+\\textbf\{([^}:]+):?\}\s*([^\n\\]+)", skills_text):
                cat_raw = item.group(1).strip().lower()
                val_raw = item.group(2).strip()
                skills_list = [s.strip() for s in val_raw.split(",") if s.strip()]

                if "programming" in cat_raw or ("language" in cat_raw and "spoken" not in cat_raw and "vietnamese" not in val_raw.lower()):
                    result["skills"]["programming"] = skills_list
                elif "framework" in cat_raw or "library" in cat_raw:
                    result["skills"]["frameworks"] = skills_list
                elif "tool" in cat_raw or "database" in cat_raw:
                    result["skills"]["tools_databases"] = skills_list
                elif "soft" in cat_raw:
                    result["skills"]["soft_skills"] = skills_list
                elif "language" in cat_raw:
                    result["skills"]["languages"] = [
                        {"language": s.split("(")[0].strip(), "level": s.split("(")[1].replace(")", "").strip()}
                        if "(" in s else {"language": s, "level": "Proficient"}
                        for s in skills_list
                    ]

        return result

    @classmethod
    def parse_pdf(cls, file_bytes: bytes) -> Dict[str, Any]:
        """
        Trích xuất văn bản từ file PDF và bóc tách thành thông tin hồ sơ ứng viên có cấu trúc.
        """
        if not file_bytes:
            return {}

        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            raw_text = "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception as e:
            logger.error(f"Failed to read PDF file: {e}")
            return {}

        return cls.parse_text_resume(raw_text)

    @classmethod
    def parse_text_resume(cls, raw_text: str) -> Dict[str, Any]:
        """
        Phân tích văn bản thô (từ PDF, DOCX, TXT) thành cấu trúc hồ sơ Candidate.
        """
        result: Dict[str, Any] = {
            "candidate": {},
            "education": [],
            "skills": {},
            "projects": [],
            "experience": [],
            "raw_master_resume_md": raw_text,
        }

        if not raw_text or not raw_text.strip():
            return result

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        # 1. Trích xuất Tên ứng viên (thường ở dòng đầu tiên)
        if lines:
            first_line = lines[0]
            # Nếu dòng đầu ngắn và không phải tiêu đề mục
            if len(first_line.split()) <= 6 and not any(kw in first_line.lower() for kw in ["resume", "curriculum", "cv", "page"]):
                result["candidate"]["name"] = first_line

        # 2. Trích xuất Email
        email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", raw_text)
        if email_match:
            result["candidate"]["email"] = email_match.group(1).strip()

        # 3. Trích xuất Phone
        phone_match = re.search(r"(?:\+84|0|\(\+84\))[\s.-]?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}", raw_text)
        if phone_match:
            result["candidate"]["phone"] = phone_match.group(0).strip()

        # 4. Trích xuất GitHub & LinkedIn
        github_match = re.search(r"(?:https?://)?github\.com/([a-zA-Z0-9_-]+)", raw_text, re.IGNORECASE)
        if github_match:
            result["candidate"]["github"] = f"https://github.com/{github_match.group(1).strip()}"

        linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)", raw_text, re.IGNORECASE)
        if linkedin_match:
            result["candidate"]["linkedin"] = f"https://www.linkedin.com/in/{linkedin_match.group(1).strip()}/"

        # 5. Trích xuất Headline / Summary
        summary_match = re.search(
            r"(?:Summary|Objective|Profile|About Me)[:\n]\s*([\s\S]*?)(?=(?:Education|Skills|Experience|Projects|Certifications|\Z))",
            raw_text,
            re.IGNORECASE,
        )
        if summary_match:
            result["candidate"]["summary"] = summary_match.group(1).strip()

        # 6. Trích xuất Kỹ năng phổ biến (heuristic taxonomy extraction)
        known_prog_languages = ["Python", "JavaScript", "TypeScript", "C++", "C#", "Java", "Go", "Golang", "Rust", "PHP", "Ruby", "Swift", "Kotlin", "Dart", "SQL"]
        known_frameworks = ["FastAPI", "React", "NextJS", "Vue", "Angular", "Express", "NestJS", "Django", "Flask", "Spring Boot", "Flutter", "Tailwind CSS", "Hono"]
        known_tools = ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes", "Git", "Linux", "AWS", "GCP", "Cloudflare", "Alembic", "SQLAlchemy"]

        found_langs = [kw for kw in known_prog_languages if re.search(r"\b" + re.escape(kw) + r"\b", raw_text, re.IGNORECASE)]
        found_fw = [kw for kw in known_frameworks if re.search(r"\b" + re.escape(kw) + r"\b", raw_text, re.IGNORECASE)]
        found_tools = [kw for kw in known_tools if re.search(r"\b" + re.escape(kw) + r"\b", raw_text, re.IGNORECASE)]

        if found_langs:
            result["skills"]["programming"] = found_langs
        if found_fw:
            result["skills"]["frameworks"] = found_fw
        if found_tools:
            result["skills"]["tools_databases"] = found_tools

        return result

    @classmethod
    def parse_raw_file(cls, filename: str, content_bytes: bytes) -> Dict[str, Any]:
        """
        Tự động nhận diện định dạng file (.pdf, .tex, .yaml, .yml, .json, .md) và phân tích cú pháp.
        """
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            return cls.parse_pdf(content_bytes)
        
        text_content = content_bytes.decode("utf-8", errors="ignore")
        if ext in [".yaml", ".yml"]:
            parsed = cls.parse_yaml(text_content)
            # Nếu YAML có root 'candidate', chuẩn hóa theo merged format
            if isinstance(parsed, dict) and "candidate" in parsed:
                return parsed
            return {"candidate": parsed}
        elif ext == ".tex":
            parsed = cls.parse_latex(text_content)
            parsed["raw_master_resume_tex"] = text_content
            return parsed
        elif ext == ".json":
            try:
                data = json.loads(text_content)
                return data if isinstance(data, dict) else {"candidate": data}
            except Exception:
                return {}
        elif ext == ".md":
            parsed = cls.parse_text_resume(text_content)
            parsed["raw_master_resume_md"] = text_content
            return parsed
        else:
            return cls.parse_text_resume(text_content)

    @classmethod
    def load_and_merge_context(cls, context_dir: Path | str) -> Dict[str, Any]:
        """
        Nạp toàn bộ file trong thư mục context/ (YAML, TeX, MD, PDF).
        Nếu thư mục không có file hoặc không tồn tại, tự động fallback sang context.example/
        """
        context_path = Path(context_dir)
        
        # Nếu context_path không tồn tại hoặc không có file yaml/tex/pdf, thử tìm context.example/
        if not context_path.exists() or not any(context_path.glob("*.*")):
            alt_example = context_path.parent / "context.example"
            if alt_example.exists() and any(alt_example.glob("*.*")):
                logger.info(f"Using template fallback context directory: {alt_example}")
                context_path = alt_example

        yaml_file = context_path / "candidate-profile.yaml"
        if not yaml_file.exists():
            yaml_file = context_path / "candidate-profile.example.yaml"

        tex_file = context_path / "master-resume.tex"
        md_file = context_path / "master-resume.md"
        pdf_file = context_path / "master-resume.pdf"

        merged: Dict[str, Any] = {
            "candidate": {},
            "education": [],
            "target_roles": [],
            "target_locations": [],
            "skills": {},
            "projects": [],
            "experience": [],
            "certifications": [],
            "preferences": {},
            "raw_master_resume_md": None,
            "raw_master_resume_tex": None,
        }

        # 1. Đọc PDF nếu có
        if pdf_file.exists():
            try:
                pdf_bytes = pdf_file.read_bytes()
                parsed_pdf = cls.parse_pdf(pdf_bytes)
                merged["candidate"].update(parsed_pdf.get("candidate", {}))
                if parsed_pdf.get("skills"):
                    merged["skills"].update(parsed_pdf["skills"])
            except Exception as e:
                logger.warning(f"Could not parse context PDF: {e}")

        # 2. Đọc TeX nếu có
        if tex_file.exists():
            tex_content = tex_file.read_text(encoding="utf-8", errors="ignore")
            merged["raw_master_resume_tex"] = tex_content
            parsed_tex = cls.parse_latex(tex_content)
            
            merged["candidate"].update(parsed_tex.get("candidate", {}))
            if parsed_tex.get("education"):
                merged["education"] = parsed_tex["education"]
            if parsed_tex.get("skills"):
                merged["skills"].update(parsed_tex["skills"])

        # 3. Đọc Markdown nếu có
        if md_file.exists():
            merged["raw_master_resume_md"] = md_file.read_text(encoding="utf-8", errors="ignore")

        # 4. Đọc YAML (ưu tiên dữ liệu cấu trúc chặt chẽ nhất)
        if yaml_file.exists():
            yaml_content = yaml_file.read_text(encoding="utf-8", errors="ignore")
            parsed_yaml = cls.parse_yaml(yaml_content)

            if "candidate" in parsed_yaml and isinstance(parsed_yaml["candidate"], dict):
                for k, v in parsed_yaml["candidate"].items():
                    if v:
                        merged["candidate"][k] = v

            if parsed_yaml.get("education"):
                merged["education"] = parsed_yaml["education"]
            if parsed_yaml.get("target_roles"):
                merged["target_roles"] = parsed_yaml["target_roles"]
            if parsed_yaml.get("target_locations"):
                merged["target_locations"] = parsed_yaml["target_locations"]
            if parsed_yaml.get("skills"):
                merged["skills"].update(parsed_yaml["skills"])
            if parsed_yaml.get("projects"):
                merged["projects"] = parsed_yaml["projects"]
            if parsed_yaml.get("experience"):
                merged["experience"] = parsed_yaml["experience"]
            if parsed_yaml.get("certifications"):
                merged["certifications"] = parsed_yaml["certifications"]
            if parsed_yaml.get("preferences"):
                merged["preferences"] = parsed_yaml["preferences"]

        return merged
