import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import Skill, SkillAlias, SkillCategoryEnum

logger = logging.getLogger("skill_normalizer")

# Bộ từ điển khởi tạo mặc định (Predefined Canonical Taxonomy)
DEFAULT_SKILL_TAXONOMY: Dict[str, Dict[str, any]] = {
    # Programming Languages
    "Python": {
        "category": SkillCategoryEnum.LANGUAGE,
        "aliases": ["python", "python3", "python 3", "py", "python2", "python 3.x"],
    },
    "JavaScript": {
        "category": SkillCategoryEnum.LANGUAGE,
        "aliases": ["javascript", "js", "ecmascript", "es6", "es6+"],
    },
    "TypeScript": {
        "category": SkillCategoryEnum.LANGUAGE,
        "aliases": ["typescript", "ts"],
    },
    "Go": {
        "category": SkillCategoryEnum.LANGUAGE,
        "aliases": ["go", "golang"],
    },
    "Java": {
        "category": SkillCategoryEnum.LANGUAGE,
        "aliases": ["java", "core java", "java 8", "java 11", "java 17", "java 21"],
    },
    "C++": {
        "category": SkillCategoryEnum.LANGUAGE,
        "aliases": ["c++", "cpp"],
    },
    "C#": {
        "category": SkillCategoryEnum.LANGUAGE,
        "aliases": ["c#", "csharp", "c sharp", ".net c#"],
    },
    "Rust": {
        "category": SkillCategoryEnum.LANGUAGE,
        "aliases": ["rust", "rustlang"],
    },
    "PHP": {
        "category": SkillCategoryEnum.LANGUAGE,
        "aliases": ["php", "php7", "php8"],
    },
    "SQL": {
        "category": SkillCategoryEnum.LANGUAGE,
        "aliases": ["sql", "structured query language", "t-sql", "pl/sql"],
    },

    # Frameworks & Libraries
    "FastAPI": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["fastapi", "fast api"],
    },
    "Django": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["django", "django rest framework", "drf"],
    },
    "Flask": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["flask"],
    },
    "Node.js": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["nodejs", "node.js", "node js", "node"],
    },
    "React": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["react", "reactjs", "react.js", "react js", "react native"],
    },
    "Vue.js": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["vue", "vuejs", "vue.js", "vue 3", "vue 2"],
    },
    "Next.js": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["nextjs", "next.js", "next js"],
    },
    "Spring Boot": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["spring boot", "springboot", "spring framework", "spring"],
    },
    "Express.js": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["express", "expressjs", "express.js"],
    },
    "NestJS": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["nestjs", "nest.js", "nest js"],
    },

    # Databases
    "PostgreSQL": {
        "category": SkillCategoryEnum.DATABASE,
        "aliases": ["postgres", "postgresql", "pgsql", "postgre sql", "postgres db"],
    },
    "MySQL": {
        "category": SkillCategoryEnum.DATABASE,
        "aliases": ["mysql", "my sql"],
    },
    "MongoDB": {
        "category": SkillCategoryEnum.DATABASE,
        "aliases": ["mongodb", "mongo", "mongo db"],
    },
    "Redis": {
        "category": SkillCategoryEnum.DATABASE,
        "aliases": ["redis", "redis cache"],
    },
    "Elasticsearch": {
        "category": SkillCategoryEnum.DATABASE,
        "aliases": ["elasticsearch", "elastic search", "elastic"],
    },
    "SQLite": {
        "category": SkillCategoryEnum.DATABASE,
        "aliases": ["sqlite", "sqlite3"],
    },

    # Cloud & DevOps
    "AWS": {
        "category": SkillCategoryEnum.CLOUD,
        "aliases": ["aws", "amazon web services", "amazon aws", "aws cloud"],
    },
    "Google Cloud Platform": {
        "category": SkillCategoryEnum.CLOUD,
        "aliases": ["gcp", "google cloud", "google cloud platform"],
    },
    "Microsoft Azure": {
        "category": SkillCategoryEnum.CLOUD,
        "aliases": ["azure", "ms azure", "microsoft azure"],
    },
    "Docker": {
        "category": SkillCategoryEnum.TOOL,
        "aliases": ["docker", "docker container", "dockerfile"],
    },
    "Kubernetes": {
        "category": SkillCategoryEnum.TOOL,
        "aliases": ["kubernetes", "k8s", "k8"],
    },
    "CI/CD": {
        "category": SkillCategoryEnum.TOOL,
        "aliases": ["ci/cd", "cicd", "ci cd", "continuous integration", "github actions", "gitlab ci", "jenkins"],
    },
    "Linux": {
        "category": SkillCategoryEnum.TOOL,
        "aliases": ["linux", "ubuntu", "debian", "centos", "redhat", "unix"],
    },
    "Git": {
        "category": SkillCategoryEnum.TOOL,
        "aliases": ["git", "github", "gitlab", "bitbucket", "version control"],
    },

    # AI & ML & Concepts
    "Machine Learning": {
        "category": SkillCategoryEnum.CONCEPT,
        "aliases": ["machine learning", "ml", "deep learning", "ai", "artificial intelligence"],
    },
    "PyTorch": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["pytorch", "py torch", "torch"],
    },
    "TensorFlow": {
        "category": SkillCategoryEnum.FRAMEWORK,
        "aliases": ["tensorflow", "tensor flow", "tf"],
    },
    "RESTful API": {
        "category": SkillCategoryEnum.CONCEPT,
        "aliases": ["rest", "restful", "rest api", "restful api", "rest apis", "restful apis"],
    },
    "GraphQL": {
        "category": SkillCategoryEnum.CONCEPT,
        "aliases": ["graphql", "graph ql"],
    },
    "Microservices": {
        "category": SkillCategoryEnum.CONCEPT,
        "aliases": ["microservices", "microservice", "micro-services", "micro-service architecture"],
    },
    "OOP": {
        "category": SkillCategoryEnum.CONCEPT,
        "aliases": ["oop", "object oriented programming", "lap trinh huong doi tuong"],
    },
}


class SkillNormalizer:
    """
    Service chuẩn hóa kỹ năng dựa trên Taxonomy và Từ điển đồng nghĩa.
    Hỗ trợ cả In-Memory caching và Database Sync.
    """

    def __init__(self):
        self._alias_to_canonical: Dict[str, str] = {}
        self._canonical_to_category: Dict[str, SkillCategoryEnum] = {}
        self._load_default_taxonomy()

    def _load_default_taxonomy(self):
        """Khởi tạo mapping từ từ điển mặc định."""
        for canonical, data in DEFAULT_SKILL_TAXONOMY.items():
            self._canonical_to_category[canonical] = data["category"]
            self._alias_to_canonical[canonical.lower()] = canonical
            for alias in data.get("aliases", []):
                self._alias_to_canonical[alias.lower().strip()] = canonical

    def clean_alias(self, text: str) -> str:
        """Làm sạch chuỗi skill để tra cứu: lowercase, xóa khoảng trắng thừa."""
        if not text:
            return ""
        # Xóa các ký tự đặc biệt ở đầu/cuối chuỗi trừ +, # (để giữ C++, C#)
        cleaned = text.strip().lower()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    def normalize_skill(self, raw_skill: str) -> Tuple[str, SkillCategoryEnum]:
        """
        Chuẩn hóa 1 skill thô về dạng canonical_name và category.
        Nếu không có trong từ điển, định dạng Title Case và gán OTHER.
        """
        if not raw_skill or not raw_skill.strip():
            return "", SkillCategoryEnum.OTHER

        cleaned = self.clean_alias(raw_skill)
        
        # 1. Tra cứu trực tiếp trong alias table
        if cleaned in self._alias_to_canonical:
            canonical = self._alias_to_canonical[cleaned]
            category = self._canonical_to_category.get(canonical, SkillCategoryEnum.OTHER)
            return canonical, category

        # 2. Xử lý fallback cho skill chưa có trong từ điển
        # Giữ nguyên nếu có dấu đặc biệt (C#, C++), hoặc format chuẩn
        words = raw_skill.strip().split()
        if len(words) == 1 and raw_skill.isupper() and len(raw_skill) <= 4:
            canonical = raw_skill.strip()  # ví dụ "NLP", "LLM", "SDK"
        else:
            canonical = " ".join(w.capitalize() for w in words)

        return canonical, SkillCategoryEnum.OTHER

    def is_known_skill(self, name: str) -> bool:
        """Kiểm tra skill có thuộc Canonical Taxonomy chính thức hay không."""
        if not name:
            return False
        cleaned = self.clean_alias(name)
        return cleaned in self._alias_to_canonical

    def normalize_skills(self, raw_skills: List[str]) -> List[Tuple[str, SkillCategoryEnum]]:
        """Chuẩn hóa một danh sách skills, loại bỏ trùng lặp."""

        seen_canonical: Set[str] = set()
        result: List[Tuple[str, SkillCategoryEnum]] = []

        for item in raw_skills:
            if not item:
                continue
            canonical, category = self.normalize_skill(item)
            if canonical and canonical not in seen_canonical:
                seen_canonical.add(canonical)
                result.append((canonical, category))

        return result

    def extract_skills_from_text(self, text: str) -> List[str]:
        """
        Trích xuất kỹ năng từ văn bản tự do hoàn toàn deterministic (0 LLM cost).
        Quét các alias đã biết trong từ điển chuẩn bằng regex.
        """
        if not text:
            return []

        found_canonical: Set[str] = set()
        cleaned_text = f" {text.lower()} "

        # Sắp xếp alias theo độ dài giảm dần để ưu tiên cụm từ dài (vd 'spring boot' trước 'spring')
        sorted_aliases = sorted(self._alias_to_canonical.keys(), key=len, reverse=True)

        for alias in sorted_aliases:
            # Bỏ qua alias quá ngắn (<2 ký tự) nếu không phải C / R
            if len(alias) < 2:
                continue

            # Sử dụng regex word boundary hoặc escape ký tự đặc biệt như c++, c#
            escaped_alias = re.escape(alias)
            # Kiểm tra boundary: nếu kết thúc bằng +, # thì không dùng \b ở cuối
            pattern = rf"(?<!\w){escaped_alias}(?!\w)"
            if re.search(pattern, cleaned_text, re.IGNORECASE):
                canonical = self._alias_to_canonical[alias]
                found_canonical.add(canonical)

        return list(found_canonical)

    async def seed_or_sync_db(self, db: AsyncSession):
        """Đồng bộ từ điển chuẩn vào Database (bảng skills và skill_aliases)."""
        for canonical, data in DEFAULT_SKILL_TAXONOMY.items():
            stmt = select(Skill).where(Skill.canonical_name == canonical)
            result = await db.execute(stmt)
            skill = result.scalar_one_or_none()

            if not skill:
                skill = Skill(canonical_name=canonical, category=data["category"])
                db.add(skill)
                await db.flush()

            # Seed aliases
            aliases_to_add = set(data.get("aliases", []))
            aliases_to_add.add(canonical.lower())

            for alias in aliases_to_add:
                alias_clean = alias.strip().lower()
                stmt_alias = select(SkillAlias).where(SkillAlias.alias == alias_clean)
                res_alias = await db.execute(stmt_alias)
                if not res_alias.scalar_one_or_none():
                    db.add(SkillAlias(skill_id=skill.id, alias=alias_clean))

        await db.commit()


# Singleton Instance
skill_normalizer = SkillNormalizer()
