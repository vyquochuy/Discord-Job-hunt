import json
from typing import Any, Dict, List, Optional
from app.schemas.tailoring_ir import EvidenceBundle, ValidationViolation


# ============================================================================
# Prompt Architecture for Gemini Semantic Resume Writer
# ============================================================================

RESUME_WRITER_SYSTEM_PROMPT = """You are an expert Semantic Resume Writer and Technical Career Strategist.
You are NOT a source of candidate facts.
Your sole job is to rewrite, reorganize, combine, and semantically refine verified candidate evidence to highlight relevance for the target Job Description.

ABSOLUTE ZERO-HALLUCINATION INVARIANTS:
1. Every factual statement must cite one or more valid Evidence IDs from the provided EVIDENCE BUNDLE.
2. For every bullet, you MUST break down the sentence into atomic claims under `claims`, each citing the exact `evidence_ids` that prove that specific fragment.
3. YOU MUST NOT INVENT TECHNOLOGIES: You may only use technologies that are explicitly supported by the cited evidence.
4. YOU MUST NOT INVENT OR EXTRAPOLATE METRICS: Numbers, percentages, latencies, request rates, database scale, or team sizes must match the evidence exactly.
5. YOU MUST NOT INFLATE EXPERIENCE: Do not turn academic, student, or personal coursework into "production", "enterprise", or "team lead" roles unless explicitly documented in the evidence.
6. ARCHITECTURAL MODIFIER INTEGRITY: Never drop, swap, or relocate architectural scope modifiers such as 'client-side', 'server-side', 'zero-knowledge', 'offline-first', 'hardware-backed'. If an operation is documented as 'client-side Argon2id password hashing', you MUST NOT write it as 'server-side Argon2id hashing' or drop 'client-side'.
7. UNSUPPORTED JD REQUIREMENTS ARE FORBIDDEN: If a JD requires a skill or technology listed under 'UNSUPPORTED_REQUIREMENTS', YOU MUST NOT FABRICATE EXPERIENCE FOR IT.
8. Output MUST strictly adhere to the requested JSON schema.
"""


def build_resume_generation_prompt(bundle: EvidenceBundle) -> str:
    """Xây dựng prompt sinh Resume đầy đủ từ EvidenceBundle."""
    strategy = bundle.strategy
    jd_summary = bundle.target_jd_summary
    facts = bundle.evidence_facts

    facts_formatted = []
    for f in facts:
        facts_formatted.append({
            "evidence_id": f.id,
            "category": f.category.value,
            "subject": f.subject,
            "claim": f.claim,
            "supported_technologies": f.technologies,
            "supported_metrics": f.metrics,
            "is_core": f.is_core,
        })

    prompt_data = {
        "TARGET_ROLE": strategy.target_role,
        "POSITIONING_ANGLE": strategy.positioning,
        "ROLE_FAMILY": strategy.role_family,
        "TARGET_JOB_SUMMARY": jd_summary,
        "UNSUPPORTED_REQUIREMENTS_DO_NOT_FABRICATE": strategy.unsupported_requirements,
        "ALLOWED_PROJECTS": strategy.selected_projects,
        "VERIFIED_EVIDENCE_FACTS": facts_formatted,
        "LAYOUT_BUDGET": {
            "max_projects": bundle.layout_budget.max_projects,
            "max_total_bullets": bundle.layout_budget.max_total_bullets,
            "max_bullets_per_project": bundle.layout_budget.max_bullets_per_project,
        }
    }

    instructions = f"""Please generate a tailored, professional resume draft using ONLY the provided verified facts.

CONTEXT & CONSTRAINTS:
{json.dumps(prompt_data, indent=2, ensure_ascii=False)}

OUTPUT JSON SCHEMA:
{{
  "target_title": "{strategy.target_role}",
  "professional_summary": {{
    "text": "Adaptive 2-3 sentence professional summary highlighting verified technical foundations.",
    "evidence_ids": ["education.inst_1", "project.account_manager.bullet_1"],
    "claims": [
      {{
        "claim": "Academic foundation in Computer Science and Security",
        "evidence_ids": ["education.inst_1"]
      }},
      {{
        "claim": "Experience with serverless APIs and applied cryptography",
        "evidence_ids": ["project.account_manager.bullet_1"]
      }}
    ]
  }},
  "priority_skills": {json.dumps(strategy.prioritized_skills[:8], ensure_ascii=False)},
  "projects": [
    {{
      "source_project_name": "Project Name Exactly Matching Source",
      "bullets": [
        {{
          "text": "Action verb + technical architecture + verified metric outcome.",
          "evidence_ids": ["project.slug.bullet_1", "project.slug.bullet_2"],
          "claims": [
            {{
              "claim": "Action and architecture",
              "evidence_ids": ["project.slug.bullet_1"]
            }},
            {{
              "claim": "Metric or specific tech used",
              "evidence_ids": ["project.slug.bullet_2"]
            }}
          ]
        }}
      ]
    }}
  ]
}}

Remember: Every claim fragment must trace to valid evidence_ids. Do NOT invent technologies or numbers!
"""
    return instructions


def build_bullet_regeneration_prompt(
    unit_id: str,
    project_name: str,
    failed_text: str,
    violations: List[ValidationViolation],
    supported_evidence_facts: List[Any],
    target_role: str,
) -> str:
    """Xây dựng prompt viết lại có mục tiêu cho DUY NHẤT một bullet bị vi phạm kiểm chứng."""
    violation_notes = []
    for v in violations:
        violation_notes.append(f"- [{v.violation_type.value}] {v.reason}")

    facts_subset = []
    for f in supported_evidence_facts:
        facts_subset.append({
            "evidence_id": f.id,
            "claim": f.claim,
            "technologies": f.technologies,
            "metrics": f.metrics,
        })

    prompt = f"""You previously wrote a bullet for project '{project_name}' that FAILED strict anti-hallucination validation:

FAILED TEXT:
"{failed_text}"

VALIDATION VIOLATIONS DETECTED:
{chr(10).join(violation_notes)}

AVAILABLE VERIFIED EVIDENCE FOR THIS PROJECT:
{json.dumps(facts_subset, indent=2, ensure_ascii=False)}

TASK:
Rewrite ONLY this single bullet to be 100% compliant with the evidence.
- Remove any unsupported technologies, metrics, or inflated claims.
- Cite the valid evidence_ids.
- Break down the sentence into atomic `claims`.

OUTPUT JSON:
{{
  "text": "Rewritten compliant bullet text.",
  "evidence_ids": ["project.slug.bullet_1"],
  "claims": [
    {{
      "claim": "Specific factual action",
      "evidence_ids": ["project.slug.bullet_1"]
    }}
  ]
}}
"""
    return prompt
