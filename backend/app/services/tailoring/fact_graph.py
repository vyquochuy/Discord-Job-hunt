import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models.candidate import Candidate
from app.schemas.tailoring_ir import FactNode, MetricFact

logger = logging.getLogger("fact_graph")


def safe_get_relation(entity: Any, rel_name: str) -> List[Any]:
    """Truy cập an toàn quan hệ SQLAlchemy (xử lý cả attached lẫn detached objects)."""
    if not entity:
        return []
    try:
        val = getattr(entity, rel_name, None)
        if val is not None:
            return list(val)
    except Exception:
        pass
    
    try:
        if hasattr(entity, "__dict__") and rel_name in entity.__dict__:
            val = entity.__dict__[rel_name]
            if val is not None:
                return list(val)
    except Exception:
        pass
        
    return []


# Taxonomy capabilities mapping for fact indexing
CAPABILITY_TAXONOMY: Dict[str, Set[str]] = {
    "api": {
        "api", "rest", "graphql", "endpoint", "endpoints", "hono", "fastapi", "http",
        "sync", "microservices", "request", "token-bucket", "rate-limiting", "middleware"
    },
    "database": {
        "database", "db", "sql", "relational", "sqlite", "d1", "cloudflare d1", "postgres",
        "postgresql", "redis", "kv", "cloudflare kv", "schema", "table", "tables", "indexeddb",
        "query", "data model", "blind storage", "pgvector", "alembic"
    },
    "realtime": {
        "websocket", "websockets", "real-time", "realtime", "durable objects", "stateful",
        "presence", "messaging", "pubsub", "concurrency", "channel"
    },
    "infra": {
        "infrastructure", "serverless", "cloudflare workers", "workers", "docker", "linux",
        "cloud", "edge", "latency", "deployment", "ci/cd", "pop", "asia-pacific pop"
    },
    "crypto": {
        "cryptography", "crypto", "encryption", "e2ee", "end-to-end", "zero-knowledge",
        "ecdh", "argon2id", "aes", "aes-256", "rsa", "rsa-2048", "sha-256", "pki",
        "x.509", "shamir", "key exchange", "salts", "hashing"
    },
    "system_programming": {
        "c++", "c++17", "system-level", "openssl", "protocol", "ieee 802.1x", "eap-tls",
        "peer", "authenticator", "authentication server", "memory", "object-oriented"
    },
    "security": {
        "security", "authentication", "auth", "anti-enumeration", "brute-force", "audit",
        "access control", "keystore", "keychain", "vulnerability", "tls", "eap"
    },
    "mobile": {
        "flutter", "dart", "android", "ios", "keystore", "keychain", "hive", "offline"
    },
    "frontend": {
        "react", "tailwind", "tailwind css", "nextjs", "javascript", "typescript", "ui", "dom", "web"
    },
    "automation": {
        "discord.js", "discord bot", "scraping", "ingestion", "pipeline", "deduplication", "batch"
    }
}


class FactGraphBuilder:
    """
    Trích xuất và quản lý Đồ thị Sự thật Bất biến (Canonical Fact Graph) của Ứng viên:
    - Gán `fact_id` định danh phân cấp duy nhất cho từng dự án, bullet, kỹ năng, học vấn.
    - Bóc tách chỉ số định lượng `MetricFact` (con số, đơn vị, ngữ cảnh) để kiểm chứng chính xác.
    - Tự động gắn nhãn các capabilities theo bộ từ điển chuẩn hóa.
    """

    METRIC_PATTERN = r"\b(\d+(?:\.\d+)?)\s*(ms|s|%|req/min|req/10s|MB|GB|KB|POPs?|PoP|tables?|devices?|threshold)\b"

    @classmethod
    def extract_metric_facts(cls, text: str, fact_prefix: str) -> List[MetricFact]:
        """Trích xuất các đối tượng MetricFact định lượng từ văn bản."""
        if not text:
            return []
        
        matches = re.finditer(cls.METRIC_PATTERN, text, re.IGNORECASE)
        metric_facts: List[MetricFact] = []
        
        for idx, m in enumerate(matches):
            val_str, unit = m.groups()
            try:
                numeric_val = float(val_str)
            except ValueError:
                continue
            
            raw_token = m.group(0).strip()
            start_pos = max(0, m.start() - 15)
            end_pos = min(len(text), m.end() + 15)
            context = text[start_pos:end_pos].strip()

            metric_facts.append(
                MetricFact(
                    metric_id=f"{fact_prefix}.metric_{idx+1}",
                    numeric_value=numeric_val,
                    unit=unit.lower(),
                    context=context,
                    raw_token=raw_token,
                    is_exact=True,
                )
            )
        
        return metric_facts

    @classmethod
    def infer_capabilities(cls, text: str, technologies: List[str]) -> List[str]:
        """Trích xuất các capability tags dựa trên taxonomy chuẩn bằng word-boundary matching."""
        combined_text = f"{text} {' '.join(technologies or [])}".lower()
        words = set(re.findall(r"[a-zA-Z0-9_\+\#\.\-]+", combined_text))
        detected = []
        for cap, keywords in CAPABILITY_TAXONOMY.items():
            is_matched = False
            for kw in keywords:
                kw_low = kw.lower()
                if " " in kw_low or "-" in kw_low or "." in kw_low:
                    if re.search(r"\b" + re.escape(kw_low) + r"\b", combined_text):
                        is_matched = True
                        break
                else:
                    if kw_low in words:
                        is_matched = True
                        break
            if is_matched:
                detected.append(cap)
        return detected or ["general"]

    @classmethod
    def build_fact_graph(cls, candidate: Candidate) -> Dict[str, FactNode]:
        """
        Xây dựng bảng tra cứu FactNode theo `fact_id`.
        """
        fact_nodes: Dict[str, FactNode] = {}

        # 1. Projects & Bullets
        candidate_projects = safe_get_relation(candidate, "projects")
        for p_idx, proj in enumerate(candidate_projects):
            p_name = getattr(proj, "name", f"Project_{p_idx+1}")
            p_slug = re.sub(r"[^a-zA-Z0-9_]", "_", p_name.lower()).strip("_")
            proj_fact_id = f"project.{p_slug}"
            
            p_summary = getattr(proj, "summary", "")
            p_techs = getattr(proj, "technologies", []) or []
            
            if p_summary:
                p_summary_id = f"{proj_fact_id}.summary"
                fact_nodes[p_summary_id] = FactNode(
                    fact_id=p_summary_id,
                    entity_type="PROJECT",
                    entity_id=p_name,
                    raw_statement=f"{p_name}: {p_summary}",
                    technologies=p_techs,
                    capabilities=cls.infer_capabilities(p_summary, p_techs),
                    metrics=cls.extract_metric_facts(p_summary, p_summary_id),
                )

            ev_points = getattr(proj, "evidence_points", []) or []
            if ev_points:
                for b_idx, ev in enumerate(ev_points):
                    title = ev.get("title", "") if isinstance(ev, dict) else ""
                    detail = ev.get("detail", "") if isinstance(ev, dict) else str(ev)
                    bullet_fact_id = f"{proj_fact_id}.bullet_{b_idx+1}"
                    
                    full_text = f"{title}: {detail}" if title else detail
                    bullet_techs = ev.get("technologies", p_techs) if isinstance(ev, dict) else p_techs
                    
                    fact_nodes[bullet_fact_id] = FactNode(
                        fact_id=bullet_fact_id,
                        entity_type="PROJECT",
                        entity_id=p_name,
                        raw_statement=full_text,
                        technologies=bullet_techs or [],
                        capabilities=cls.infer_capabilities(full_text, bullet_techs or []),
                        metrics=cls.extract_metric_facts(full_text, bullet_fact_id),
                    )

        # 2. Experiences
        candidate_experiences = safe_get_relation(candidate, "experiences")
        for e_idx, exp in enumerate(candidate_experiences):
            exp_company = getattr(exp, "company", "Company")
            exp_role = getattr(exp, "role", "Role")
            exp_slug = re.sub(r"[^a-zA-Z0-9_]", "_", exp_company.lower()).strip("_")
            exp_fact_id = f"experience.{exp_slug}"
            
            exp_desc = getattr(exp, "description", "")
            if exp_desc:
                fact_nodes[f"{exp_fact_id}.desc"] = FactNode(
                    fact_id=f"{exp_fact_id}.desc",
                    entity_type="EXPERIENCE",
                    entity_id=f"{exp_company}:{exp_role}",
                    raw_statement=exp_desc,
                    technologies=[],
                    capabilities=cls.infer_capabilities(exp_desc, []),
                    metrics=cls.extract_metric_facts(exp_desc, f"{exp_fact_id}.desc"),
                )
            
            exp_achs = getattr(exp, "achievements", []) or []
            for a_idx, ach in enumerate(exp_achs):
                ach_id = f"{exp_fact_id}.ach_{a_idx+1}"
                fact_nodes[ach_id] = FactNode(
                    fact_id=ach_id,
                    entity_type="EXPERIENCE",
                    entity_id=f"{exp_company}:{exp_role}",
                    raw_statement=str(ach),
                    technologies=[],
                    capabilities=cls.infer_capabilities(str(ach), []),
                    metrics=cls.extract_metric_facts(str(ach), ach_id),
                )

        # 3. Education
        cand_edu = getattr(candidate, "education", None) or []
        for edu_idx, edu in enumerate(cand_edu):
            if isinstance(edu, dict):
                edu_id = f"education.inst_{edu_idx+1}"
                inst = edu.get("institution", "University")
                field = edu.get("field", "")
                gpa = edu.get("gpa", "")
                coursework = ", ".join(edu.get("coursework", [])) if isinstance(edu.get("coursework"), list) else str(edu.get("coursework", ""))
                edu_statement = f"{inst} | Major: {field} | GPA: {gpa} | Coursework: {coursework}"
                
                fact_nodes[edu_id] = FactNode(
                    fact_id=edu_id,
                    entity_type="EDUCATION",
                    entity_id=inst,
                    raw_statement=edu_statement,
                    technologies=[],
                    capabilities=["education", "foundation"],
                    metrics=cls.extract_metric_facts(edu_statement, edu_id),
                )

        # 4. Candidate Identity & Summary
        cand_id_node = "candidate.identity"
        cand_summary = getattr(candidate, "summary", "") or ""
        cand_name = getattr(candidate, "full_name", "Candidate") or "Candidate"
        fact_nodes[cand_id_node] = FactNode(
            fact_id=cand_id_node,
            entity_type="CANDIDATE",
            entity_id=cand_name,
            raw_statement=cand_summary,
            technologies=[],
            capabilities=cls.infer_capabilities(cand_summary, []),
            metrics=cls.extract_metric_facts(cand_summary, cand_id_node),
        )

        return fact_nodes


fact_graph_builder = FactGraphBuilder()
