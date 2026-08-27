import re
from typing import Dict, List, Optional, Set, Tuple


# ============================================================================
# Canonical Technology & Concept Alias Registry
# ============================================================================

CANONICAL_TECH_ALIASES: Dict[str, Set[str]] = {
    "aes_256_gcm": {
        "aes-256-gcm", "aes_256_gcm", "aes-gcm", "aes gcm", "aes256", "aes-256", "aes"
    },
    "argon2id": {
        "argon2id", "argon2", "argon2-id", "argon 2id"
    },
    "shamir_secret_sharing": {
        "shamir secret sharing", "shamir's secret sharing", "shamir secret-sharing", "shamir", "sss"
    },
    "ecdh": {
        "ecdh", "ecdh p-256", "ecdh-p256", "elliptic curve diffie-hellman", "diffie-hellman"
    },
    "rsa": {
        "rsa", "rsa-2048", "rsa 2048", "rsa-4096", "rsa4096"
    },
    "sha256": {
        "sha-256", "sha256", "sha-2", "sha 256", "sha"
    },
    "pki_x509": {
        "x.509", "x509", "x.509 pki", "pki", "public key infrastructure", "certificate chain", "x509 certificate"
    },
    "eap_tls": {
        "ieee 802.1x", "802.1x", "eap-tls", "eap tls", "eap_tls", "eap"
    },
    "zero_knowledge": {
        "zero-knowledge", "zero knowledge", "zero-knowledge architecture", "zero knowledge architecture", "zk"
    },
    "cloudflare_workers": {
        "cloudflare workers", "workers", "cf workers", "cloudflare serverless", "cloudflare worker"
    },
    "cloudflare_d1": {
        "cloudflare d1", "d1", "d1 database", "cloudflare-d1", "sqlite/d1", "d1 sqlite"
    },
    "cloudflare_kv": {
        "cloudflare kv", "kv", "workers kv", "cloudflare-kv"
    },
    "cloudflare_durable_objects": {
        "cloudflare durable objects", "durable objects", "durable object", "cloudflare do"
    },
    "cpp": {
        "c++", "c++17", "c++20", "c++11", "c++14", "modern c++", "cpp"
    },
    "python": {
        "python", "python 3", "python3", "python 3.x"
    },
    "javascript": {
        "javascript", "js", "es6", "es2020", "esnext"
    },
    "typescript": {
        "typescript", "ts"
    },
    "fastapi": {
        "fastapi", "fastapi framework", "fast-api"
    },
    "hono": {
        "hono", "hono.js", "hono framework", "honojs"
    },
    "react": {
        "react", "react.js", "reactjs"
    },
    "tailwind_css": {
        "tailwind", "tailwind css", "tailwindcss", "tailwind-css"
    },
    "nextjs": {
        "nextjs", "next.js", "next js", "next"
    },
    "flutter": {
        "flutter", "flutter framework"
    },
    "dart": {
        "dart", "dart language"
    },
    "hive": {
        "hive", "hive db", "hive storage"
    },
    "postgresql": {
        "postgresql", "postgres", "psql", "pg"
    },
    "sqlite": {
        "sqlite", "sqlite3", "sqlite 3"
    },
    "sql": {
        "sql", "relational sql", "relational database", "relational data", "rdbms"
    },
    "docker": {
        "docker", "docker container", "docker containers", "containerization", "containers"
    },
    "linux": {
        "linux", "posix", "ubuntu", "debian", "unix"
    },
    "openssl": {
        "openssl", "openssl 3.0", "openssl library"
    },
    "wireshark": {
        "wireshark"
    },
    "websocket": {
        "websocket", "websockets", "ws", "wss"
    },
    "rest_api": {
        "rest", "rest api", "restful", "restful api", "rest apis", "http api", "http apis"
    },
    "rate_limiting": {
        "rate limiting", "rate-limiting", "token bucket", "token-bucket", "sliding window"
    },
    "git": {
        "git", "github"
    },
    "discord_bot": {
        "discord.js", "discord bot", "discord-bot"
    },
    "sqlalchemy": {
        "sqlalchemy", "orm"
    },
    "alembic": {
        "alembic", "database migration", "migrations"
    },
    "redis": {
        "redis", "redis cache"
    },
    # Common External / Industry Technologies (for Gap & Hallucination Detection)
    "kubernetes": {
        "kubernetes", "k8s", "k8s cluster", "kubernetes cluster"
    },
    "kafka": {
        "kafka", "apache kafka", "kafka brokers", "kafka broker"
    },
    "cassandra": {
        "cassandra", "apache cassandra"
    },
    "golang": {
        "golang", "go language", "go lang"
    },
    "grpc": {
        "grpc", "g-rpc", "protobuf"
    },
    "graphql": {
        "graphql", "graphql federation", "apollo graphql"
    },
    "aws": {
        "aws", "amazon web services", "aws ec2", "aws s3", "aws lambda"
    },
    "gcp": {
        "gcp", "google cloud", "google cloud platform"
    },
    "azure": {
        "azure", "microsoft azure"
    },
    "mongodb": {
        "mongodb", "mongo"
    },
    "elasticsearch": {
        "elasticsearch", "elastic search", "opensearch"
    },
    "rabbitmq": {
        "rabbitmq", "rabbit mq"
    },
    "rust": {
        "rust", "rustlang"
    },
    "java": {
        "java", "spring", "spring boot"
    },
    "django": {
        "django"
    },
    "flask": {
        "flask"
    },
    "vue": {
        "vue", "vuejs", "vue.js"
    },
    "angular": {
        "angular", "angularjs"
    },
}

# Reverse lookup: alias_lowercase -> canonical_id
_ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canonical_id, aliases in CANONICAL_TECH_ALIASES.items():
    _ALIAS_TO_CANONICAL[canonical_id] = canonical_id
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias.lower().strip()] = canonical_id


class TechnologyAliasRegistry:
    """
    Registry chuẩn hóa từ đồng nghĩa công nghệ:
    - Ánh xạ các biến thể cách viết (AES-GCM, AES-256-GCM, Workers, Cloudflare Workers)
      về ID định danh chuẩn (Canonical ID).
    - Ngăn chặn triệt để False Positives trong Technology Validation.
    """

    @classmethod
    def get_canonical_id(cls, raw_tech: str) -> str:
        """Trả về Canonical ID của một công nghệ, hoặc chuỗi lowercase đã làm sạch nếu không có trong từ điển."""
        if not raw_tech:
            return ""
        cleaned = raw_tech.lower().strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if cleaned in _ALIAS_TO_CANONICAL:
            return _ALIAS_TO_CANONICAL[cleaned]
        
        # Thử bỏ dấu gạch ngang hoặc dấu cách
        simplified = re.sub(r"[\-_\.\/]", " ", cleaned).strip()
        if simplified in _ALIAS_TO_CANONICAL:
            return _ALIAS_TO_CANONICAL[simplified]
            
        return re.sub(r"[^a-zA-Z0-9_\+]", "_", cleaned).strip("_")

    @classmethod
    def extract_technologies_from_text(cls, text: str) -> List[Tuple[str, str]]:
        """
        Trích xuất các công nghệ có trong văn bản bằng word-boundary matching.
        Trả về danh sách tuple: (matched_surface_token, canonical_id).
        """
        if not text:
            return []

        text_lower = f" {text.lower()} "
        found_canonical: Dict[str, str] = {}

        # Sắp xếp các aliases theo độ dài giảm dần để match phrase dài trước (ví dụ "Cloudflare Workers" trước "Workers")
        sorted_aliases = sorted(_ALIAS_TO_CANONICAL.keys(), key=len, reverse=True)

        for alias in sorted_aliases:
            canonical = _ALIAS_TO_CANONICAL[alias]
            if canonical in found_canonical:
                continue

            # Word boundary regex cho alias
            # Chú ý xử lý các ký tự đặc biệt như +, ., -, etc.
            escaped_alias = re.escape(alias)
            pattern = r"(?<![a-zA-Z0-9_\+\#\.\-])" + escaped_alias + r"(?![a-zA-Z0-9_\+\#\.\-])"
            
            match = re.search(pattern, text_lower)
            if match:
                found_canonical[canonical] = alias

        return [(alias, canonical) for canonical, alias in found_canonical.items()]

    @classmethod
    def is_technology_supported(
        cls,
        claimed_tech: str,
        allowed_canonical_techs: Set[str]
    ) -> Tuple[bool, str]:
        """
        Kiểm tra xem công nghệ nêu ra (claimed_tech) có thuộc tập công nghệ được phép hay không.
        Trả về: (is_supported, canonical_id).
        """
        canonical_id = cls.get_canonical_id(claimed_tech)
        if not canonical_id:
            return True, ""
        
        is_supported = canonical_id in allowed_canonical_techs
        return is_supported, canonical_id


alias_registry = TechnologyAliasRegistry()
