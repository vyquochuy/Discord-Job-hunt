import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


class CandidateProfileParser:
    """
    Parser chịu trách nhiệm phân tích cú pháp và trích xuất dữ liệu từ các file trong context/:
    - candidate-profile.yaml
    - master-resume.tex (LaTeX)
    - master-resume.md (Markdown)
    """

    @staticmethod
    def parse_yaml(content: str) -> Dict[str, Any]:
        """Parse nội dung file candidate-profile.yaml."""
        if not content.strip():
            return {}
        data = yaml.safe_load(content) or {}
        return data

    @staticmethod
    def parse_latex(content: str) -> Dict[str, Any]:
        """
        Trích xuất các thông tin chính từ file master-resume.tex (Header, Objective, Education, Skills, Projects).
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
        if name_match:
            result["candidate"]["name"] = name_match.group(1).strip()

        # 2. Trích xuất Headline
        headline_match = re.search(r"\{\\Large\s+\\textbf\{([^}]+)\}\}", content)
        if headline_match:
            result["candidate"]["headline"] = headline_match.group(1).strip()

        # 3. Trích xuất Liên hệ: Phone, Email, GitHub, LinkedIn, Location
        phone_match = re.search(r"(\(\+\d+\)\s*\d+)", content)
        if phone_match:
            result["candidate"]["phone"] = phone_match.group(1).strip()

        email_match = re.search(r"\\href\{mailto:([^}]+)\}", content)
        if email_match:
            result["candidate"]["email"] = email_match.group(1).strip()

        github_match = re.search(r"\\href\{https://github\.com/([^}]+)\}", content)
        if github_match:
            result["candidate"]["github"] = f"https://github.com/{github_match.group(1).strip()}"

        linkedin_match = re.search(r"\\href\{https://www\.linkedin\.com/in/([^/]+)/?\}", content)
        if linkedin_match:
            result["candidate"]["linkedin"] = f"https://www.linkedin.com/in/{linkedin_match.group(1).strip()}/"

        location_match = re.search(r"\\quad\s+([^\\|\n\t]+(?:Ho Chi Minh|Hanoi|Da Nang)[^\\|\n\t]*)\s+\\quad", content)
        if location_match:
            result["candidate"]["location"] = location_match.group(1).strip()

        # 4. Trích xuất Objective
        obj_match = re.search(r"\\section\*\{Objective\}\s*([\s\S]*?)(?=\\section\*|\Z)", content)
        if obj_match:
            obj_text = re.sub(r"%.*$", "", obj_match.group(1), flags=re.MULTILINE)
            result["candidate"]["summary"] = obj_text.strip()

        # 5. Trích xuất Education
        edu_match = re.search(r"\\section\*\{Education\}\s*([\s\S]*?)(?=\\section\*|\Z)", content)
        if edu_match:
            edu_text = edu_match.group(1)
            inst_match = re.search(r"\\textbf\{([^}]+)\}", edu_text)
            institution = inst_match.group(1) if inst_match else ""
            
            gpa_match = re.search(r"GPA:\s*([0-9\./]+)", edu_text)
            gpa = gpa_match.group(1) if gpa_match else None

            major_match = re.search(r"Major:\s*([^\\}\n]+)", edu_text)
            major = major_match.group(1).strip() if major_match else ""

            coursework_match = re.search(r"Relevant Coursework:\s*([^\n\\]+)", edu_text)
            coursework = []
            if coursework_match:
                coursework = [c.strip() for c in coursework_match.group(1).split(",") if c.strip()]

            if institution or major:
                result["education"].append({
                    "institution": institution,
                    "degree": "Bachelor",
                    "field": major,
                    "graduation_year": 2026,
                    "gpa": gpa,
                    "coursework": coursework,
                })

        # 6. Trích xuất Skills
        skills_match = re.search(r"\\section\*\{Skills\}\s*([\s\S]*?)(?=\\section\*|\Z)", content)
        if skills_match:
            skills_text = skills_match.group(1)
            for item in re.finditer(r"\\item\s+\\textbf\{([^}:]+):?\}\s*([^\n\\]+)", skills_text):
                cat_raw = item.group(1).strip().lower()
                val_raw = item.group(2).strip()
                skills_list = [s.strip() for s in val_raw.split(",") if s.strip()]

                if "programming" in cat_raw:
                    result["skills"]["programming"] = skills_list
                elif "framework" in cat_raw:
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
    def load_and_merge_context(cls, context_dir: Path | str) -> Dict[str, Any]:
        """
        Nạp toàn bộ file trong thư mục context/ (YAML, TeX, MD) và gộp thành một payload hoàn chỉnh
        để lưu trữ vào cơ sở dữ liệu.
        """
        context_path = Path(context_dir)
        yaml_file = context_path / "candidate-profile.yaml"
        tex_file = context_path / "master-resume.tex"
        md_file = context_path / "master-resume.md"

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

        # 1. Đọc TeX nếu có
        if tex_file.exists():
            tex_content = tex_file.read_text(encoding="utf-8")
            merged["raw_master_resume_tex"] = tex_content
            parsed_tex = cls.parse_latex(tex_content)
            
            # Gộp thông tin cơ bản từ TeX
            merged["candidate"].update(parsed_tex.get("candidate", {}))
            if parsed_tex.get("education"):
                merged["education"] = parsed_tex["education"]
            if parsed_tex.get("skills"):
                merged["skills"].update(parsed_tex["skills"])

        # 2. Đọc Markdown nếu có
        if md_file.exists():
            merged["raw_master_resume_md"] = md_file.read_text(encoding="utf-8")

        # 3. Đọc YAML (ưu tiên ghi đè với dữ liệu cấu trúc chặt chẽ nhất)
        if yaml_file.exists():
            yaml_content = yaml_file.read_text(encoding="utf-8")
            parsed_yaml = cls.parse_yaml(yaml_content)

            if "candidate" in parsed_yaml and isinstance(parsed_yaml["candidate"], dict):
                # Update non-empty fields
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
