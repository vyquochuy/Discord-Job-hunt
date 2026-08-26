import pytest
from typing import List

from app.models.candidate import Candidate, CandidateProject
from app.models.job import Job
from app.schemas.tailoring_ir import (
    FactNode,
    LayoutBudget,
    ProjectEvidenceModel,
    CoreEvidence,
    SupportingEvidence,
    ScoredEvidenceItem,
    ScoredProjectCandidate,
)
from app.services.tailoring.resume_intelligence import (
    EvidenceScorer,
    ResumeIntelligenceEngine,
    resume_intelligence,
)
from app.services.tailoring.layout_planner import LayoutPlanner, layout_planner
from app.services.tailoring.fact_graph import fact_graph_builder


@pytest.fixture
def sample_candidate() -> Candidate:
    """Fixture cung cấp ứng viên mẫu với Project Evidence Model 3 lớp."""
    candidate = Candidate(
        full_name="Vy Quoc Huy",
        headline="Final-year Computer Science student",
        summary="Final-year student specializing in Cyber Security and Distributed Systems.",
        education=[{
            "institution": "VNUHCM - University of Science",
            "field": "Computer Science (Cyber Security)",
            "graduation_year": 2026,
            "gpa": "3.15/4.0",
        }],
    )

    p1 = CandidateProject(
        name="Account Manager: Zero-Knowledge Password Vault",
        role="Author & Lead Developer",
        summary="Offline-first password manager with encrypted cloud synchronization.",
        technologies=["Flutter", "Dart", "Cloudflare Workers", "Hono", "Hive", "Argon2id", "AES-256-GCM", "Shamir Secret Sharing"],
        evidence_points=[
            {
                "title": "Zero-Knowledge Key Recovery",
                "detail": "Designed a recovery mechanism using Shamir Secret Sharing to reconstruct encryption keys without exposing the master key.",
                "is_core": True,
                "technology_refs": ["Shamir Secret Sharing", "Argon2id", "AES-256-GCM"],
            },
            {
                "title": "Serverless API & Real-time Sync",
                "detail": "Engineered high-throughput REST and WebSocket APIs on Cloudflare Workers and Hono with KV sliding window rate limiting sustaining 200 req/min.",
                "is_core": False,
                "technologies": ["Cloudflare Workers", "Hono", "TypeScript"],
            },
            {
                "title": "Offline-First Storage Engine",
                "detail": "Implemented local encrypted state persistence using Hive and hardware keystore biometric unlock on Android.",
                "is_core": False,
                "technologies": ["Flutter", "Dart", "Hive"],
            }
        ],
        order=0,
    )

    p2 = CandidateProject(
        name="VYVYCHAT",
        role="Full-stack Developer",
        summary="Real-time messaging platform built on Cloudflare serverless edge infrastructure.",
        technologies=["React", "TypeScript", "Tailwind CSS", "Cloudflare Workers", "Durable Objects", "Cloudflare D1", "Cloudflare KV"],
        evidence_points=[
            {
                "title": "Stateful Real-Time Edge",
                "detail": "Engineered a stateful WebSocket layer using Cloudflare Durable Objects to manage persistent edge connections with ~45ms latency.",
                "is_core": True,
            },
            {
                "title": "Serverless Infrastructure & D1 Database",
                "detail": "Designed relational schema in SQLite/D1 and token-bucket rate limiting on Cloudflare KV sustaining 200 req/min.",
                "is_core": False,
            }
        ],
        order=1,
    )

    candidate.projects = [p1, p2]
    return candidate


def test_core_evidence_invariant_survives_under_unrelated_jd(sample_candidate):
    """
    INVARIANT 1: CORE MUST ALWAYS SURVIVE TAILORING.
    Khi JD là Web Developer (ít liên quan đến Shamir Secret Sharing),
    Core evidence vẫn được giữ lại 100% trong strategy.
    """
    web_dev_job = Job(
        title="Web Developer (React / TypeScript / Serverless)",
        description="Looking for Web Developer with experience in React, TypeScript, WebSocket APIs, and Cloudflare Workers.",
        requirements_summary="React, TypeScript, WebSocket, REST API, Serverless",
    )

    strategy = resume_intelligence.build_strategy(
        candidate=sample_candidate,
        job=web_dev_job,
    )

    assert len(strategy.selected_projects) >= 1
    
    # Tìm project Account Manager trong selected projects
    am_proj = next((sp for sp in strategy.selected_projects if "Account Manager" in sp.project.name), None)
    assert am_proj is not None, "Account Manager must be selected or preserved"

    # Kiểm tra Core evidence của Account Manager luôn tồn tại
    has_core = any(
        getattr(ev, "is_core", False) or "Shamir" in ev.evidence_detail or "Zero-Knowledge" in ev.evidence_title
        for ev in am_proj.ranked_evidence
    )
    assert has_core, "Core evidence (Shamir Secret Sharing) MUST NEVER be deleted despite low JD relevance"


def test_dynamic_relevance_display_ordering(sample_candidate):
    """
    INVARIANT 2: CORE DISPLAY POSITION IS DYNAMICALLY RANKED BY RELEVANCE.
    - Với Web Developer JD: 'Serverless API & Real-time Sync' (relevance cao) phải đứng TRƯỚC Core (Shamir).
    - Với Security JD: Core (Shamir Secret Sharing) phải đứng TRƯỚC Serverless API.
    """
    # 1. Test với Web Developer JD
    web_job = Job(
        title="Web & Serverless Backend Developer",
        description="Seeking a Backend Web Developer skilled in Cloudflare Workers, Hono, REST APIs, WebSockets, and Rate Limiting.",
        requirements_summary="Cloudflare Workers, Hono, REST API, WebSocket, Rate Limiting",
    )
    web_strategy = resume_intelligence.build_strategy(sample_candidate, web_job)
    am_web = next(sp for sp in web_strategy.selected_projects if "Account Manager" in sp.project.name)

    # Bullet 0 của Web JD phải là Serverless API (relevance cao hơn), Core nằm ở vị trí tiếp theo
    bullet_titles_web = [ev.evidence_title for ev in am_web.ranked_evidence]
    assert len(bullet_titles_web) >= 2
    assert "Serverless API & Real-time Sync" == bullet_titles_web[0]
    assert "Zero-Knowledge Key Recovery" == bullet_titles_web[1]

    # 2. Test với Cyber Security JD
    sec_job = Job(
        title="Cyber Security & Cryptography Engineer",
        description="Seeking an Engineer with deep knowledge of Zero-Knowledge proofs, Shamir Secret Sharing, Argon2id, AES-GCM, and key recovery.",
        requirements_summary="Zero-Knowledge, Cryptography, Shamir Secret Sharing, Argon2id, Key Recovery",
    )
    sec_strategy = resume_intelligence.build_strategy(sample_candidate, sec_job)
    am_sec = next(sp for sp in sec_strategy.selected_projects if "Account Manager" in sp.project.name)

    bullet_titles_sec = [ev.evidence_title for ev in am_sec.ranked_evidence]
    assert len(bullet_titles_sec) >= 2
    # Với Security JD, Core (Zero-Knowledge) phải đứng số 1
    assert "Zero-Knowledge Key Recovery" == bullet_titles_sec[0]


def test_compression_first_layout_budget_preserves_core_at_min_1_bullet(sample_candidate):
    """
    INVARIANT 3: COMPRESSION CASCADE PRESERVES CORE UNDER TIGHT BUDGET.
    Khi Layout Budget bị ép xuống min_bullets_per_project = 1 và max_bullets_per_project = 1,
    bullet DUY NHẤT còn lại của mỗi project BẮT BUỘC là CORE evidence.
    """
    tight_budget = LayoutBudget(
        min_projects=2,
        max_projects=2,
        max_total_bullets=2,
        min_bullets_per_project=1,
        max_bullets_per_project=1,
    )

    job = Job(
        title="Software Engineer Intern",
        description="General Software Engineering internship.",
        requirements_summary="Python, TypeScript, SQL",
    )

    strategy = resume_intelligence.build_strategy(
        candidate=sample_candidate,
        job=job,
        layout_budget=tight_budget,
    )

    for sp in strategy.selected_projects:
        assert len(sp.ranked_evidence) == 1, f"Project {sp.project.name} must have exactly 1 bullet under tight budget"
        single_ev = sp.ranked_evidence[0]
        assert getattr(single_ev, "is_core", False) is True, (
            f"When budget allows only 1 bullet for {sp.project.name}, that bullet MUST be CORE evidence!"
        )


def test_single_source_of_truth_technologies_invariant(sample_candidate):
    """
    INVARIANT 4: NO TECHNOLOGY HALLUCINATION OUTSIDE CANDIDATE GROUND TRUTH.
    Công nghệ của project không được thêm bớt bất kỳ buzzword nào chỉ xuất hiện trong JD.
    """
    hallucination_bait_job = Job(
        title="Kubernetes & Golang Backend Lead",
        description="Must have 5 years with Kubernetes, Golang, Apache Kafka, Cassandra, gRPC, and Istio Service Mesh.",
        requirements_summary="Golang, Kubernetes, Kafka, Cassandra, gRPC, Istio",
    )

    strategy = resume_intelligence.build_strategy(sample_candidate, hallucination_bait_job)

    for sp in strategy.selected_projects:
        proj_techs = set(sp.project.technologies)
        # Khẳng định không có công nghệ bịa đặt nào lọt vào project technologies
        assert "Golang" not in proj_techs
        assert "Kubernetes" not in proj_techs
        assert "Apache Kafka" not in proj_techs
        assert "Cassandra" not in proj_techs
