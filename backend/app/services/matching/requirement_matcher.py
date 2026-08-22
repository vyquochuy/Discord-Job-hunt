import re
from typing import List, Tuple

from app.services.matching.models import (
    CandidateProfileDTO,
    ConfidenceLevel,
    EvidenceItem,
    EvidenceStatus,
    JobMatchInputDTO,
    JobRequirementDTO,
    MatchSignal,
    RequirementEvaluation,
    RequirementType,
)


class RequirementMatcher:
    """
    Engine đối soát năng lực & bằng chứng (Evidence-Based Requirement Matcher).
    Đánh giá năng lực tư duy, kiến thức nền tảng, phong cách làm việc và kỹ năng mềm
    dựa trên toàn bộ cây dữ liệu bằng chứng (Projects, Coursework, Education, Soft Skills).
    """

    # Danh mục các năng lực cốt lõi phổ biến trong ngành kỹ thuật phần mềm
    COMPETENCY_DEFINITIONS = [
        {
            "key": "logical_thinking",
            "name": "Tư duy logic & Giải quyết vấn đề (Logical Thinking & Problem Solving)",
            "type": RequirementType.COMPETENCY,
            "patterns": [
                r"tư duy\s+(logic|thuật toán|phản biện)",
                r"logical\s+thinking",
                r"problem\s+solving",
                r"giải quyết vấn đề",
                r"chứng minh tính đúng đắn",
                r"critical\s+thinking",
                r"thuật toán",
                r"algorithm",
            ],
            "coursework_match": [
                "Artificial Intelligence", "Machine Learning", "Cryptography",
                "Database Systems", "Computer Networks", "Data Structures", "Algorithms",
            ],
            "project_keywords": [
                "algorithm", "encryption", "crypto", "zero-knowledge", "rate-limiting",
                "websocket", "stateful", "shamir", "durable objects", "concurrency",
            ],
            "soft_skill_match": ["Problem-solving", "System design thinking"],
        },
        {
            "key": "software_foundation",
            "name": "Kiến thức nền tảng phát triển phần mềm (Web / Mobile Foundation)",
            "type": RequirementType.DOMAIN_KNOWLEDGE,
            "patterns": [
                r"nền tảng.*(web|mobile|phần mềm)",
                r"software\s+(engineering|development)\s+foundation",
                r"web\s+or\s+mobile",
                r"lĩnh vực phát triển phần mềm",
                r"kiến thức nền tảng",
                r"computer science",
            ],
            "tech_match": ["React", "TypeScript", "Flutter", "Python", "FastAPI", "NextJS", "Hono", "Dart"],
            "project_keywords": ["full-stack", "messaging", "flutter", "web", "mobile", "serverless", "api"],
        },
        {
            "key": "ai_utilization",
            "name": "Hiểu biết & ứng dụng AI trong lập trình (AI & Tooling Utilization)",
            "type": RequirementType.COMPETENCY,
            "patterns": [
                r"hiểu\s+ai",
                r"tận dụng\s+ai",
                r"vibe\s+coding",
                r"ai\s+utilization",
                r"llm",
                r"artificial\s+intelligence",
                r"machine\s+learning",
            ],
            "coursework_match": ["Fundamentals of Artificial Intelligence", "Introduction to Machine Learning"],
            "project_keywords": ["ai", "copilot", "automation", "intelligent", "llm"],
        },
        {
            "key": "test_and_quality",
            "name": "Tư duy kiểm thử & Chất lượng phần mềm (Test First & Correctness)",
            "type": RequirementType.COMPETENCY,
            "patterns": [
                r"test\s+first",
                r"kiểm thử",
                r"testing",
                r"tdd",
                r"quality",
                r"chứng minh.*đúng đắn",
                r"benchmarking",
            ],
            "project_keywords": ["tested", "benchmark", "load-tested", "latency", "verified", "rate-limiting", "decryption"],
        },
        {
            "key": "communication_proactivity",
            "name": "Giao tiếp & Tinh thần chủ động (Communication & Proactivity)",
            "type": RequirementType.BEHAVIORAL,
            "patterns": [
                r"giao tiếp",
                r"communication",
                r"chủ động",
                r"proactive",
                r"teamwork",
                r"làm việc nhóm",
                r"phản biện",
            ],
            "soft_skill_match": ["Teamwork", "Technical documentation", "Communication"],
            "role_match": ["Author", "Lead Developer", "Full-stack Developer"],
        },
    ]

    def extract_requirements(self, job: JobMatchInputDTO) -> List[JobRequirementDTO]:
        """Trích xuất các yêu cầu định tính từ mô tả JD nếu chưa được cấu trúc sẵn."""
        if job.requirements and len(job.requirements) > 0:
            return job.requirements

        combined_text = f"{job.title} {job.requirements_summary or ''} {job.description}".lower()
        extracted: List[JobRequirementDTO] = []

        for comp in self.COMPETENCY_DEFINITIONS:
            for pattern in comp["patterns"]:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    extracted.append(
                        JobRequirementDTO(
                            name=comp["name"],
                            type=comp["type"],
                            importance="REQUIRED",
                            normalized_name=comp["key"],
                            raw_text=pattern,
                        )
                    )
                    break

        return extracted

    def evaluate_requirement(
        self, req: JobRequirementDTO, candidate: CandidateProfileDTO
    ) -> RequirementEvaluation:
        """Đối soát một yêu cầu với toàn bộ cây bằng chứng của ứng viên."""
        evidences: List[EvidenceItem] = []
        comp_def = next((c for c in self.COMPETENCY_DEFINITIONS if c.get("key") == req.normalized_name), None)

        if not comp_def:
            # Đối soát generic theo text search trên profile & projects
            norm_name = req.name.lower()
            # Tìm trong skills
            matched_skills = [s for s in candidate.all_skills if s.lower() in norm_name or norm_name in s.lower()]
            if matched_skills:
                evidences.append(
                    EvidenceItem(
                        source_type="SKILL",
                        source_id="skills",
                        title="Kỹ năng liên quan",
                        excerpt=", ".join(matched_skills),
                    )
                )

            # Tìm trong projects
            for proj in candidate.projects:
                p_text = f"{proj.name} {proj.summary or ''} {' '.join(proj.technologies)}".lower()
                if any(w in p_text for w in norm_name.split() if len(w) > 3):
                    evidences.append(
                        EvidenceItem(
                            source_type="PROJECT",
                            source_id=proj.name,
                            title=f"Dự án {proj.name}",
                            excerpt=proj.summary or "Dự án liên quan trực tiếp",
                        )
                    )

            if len(evidences) >= 2:
                return RequirementEvaluation(
                    requirement=req,
                    status=EvidenceStatus.SUPPORTED,
                    score=1.0,
                    confidence=ConfidenceLevel.HIGH,
                    reason=f"Tìm thấy {len(evidences)} bằng chứng xác thực trong hồ sơ",
                    evidences=evidences,
                )
            elif len(evidences) == 1:
                return RequirementEvaluation(
                    requirement=req,
                    status=EvidenceStatus.SUPPORTED,
                    score=0.8,
                    confidence=ConfidenceLevel.MEDIUM,
                    reason="Tìm thấy bằng chứng liên quan",
                    evidences=evidences,
                )
            else:
                return RequirementEvaluation(
                    requirement=req,
                    status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
                    score=0.5,
                    confidence=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
                    reason="Chưa có đủ dữ liệu bằng chứng để chứng minh hoặc bác bỏ",
                    evidences=[],
                )

        # Đánh giá theo Competency Definition chuẩn
        # 1. Kiểm tra Coursework
        cw_match = comp_def.get("coursework_match", [])
        for edu in candidate.education:
            for cw in edu.coursework:
                if any(k.lower() in cw.lower() for k in cw_match):
                    evidences.append(
                        EvidenceItem(
                            source_type="EDUCATION",
                            source_id=edu.institution,
                            title=f"Môn học: {cw}",
                            excerpt=f"Đã hoàn thành môn học nền tảng '{cw}' tại {edu.institution} ({edu.degree} {edu.field})",
                        )
                    )

        # 2. Kiểm tra Projects & Project Evidence details
        proj_keywords = comp_def.get("project_keywords", [])
        for proj in candidate.projects:
            # Check summary / tech
            p_text = f"{proj.name} {proj.summary or ''} {' '.join(proj.technologies)}".lower()
            matched_kw = [k for k in proj_keywords if k.lower() in p_text]
            if matched_kw:
                evidences.append(
                    EvidenceItem(
                        source_type="PROJECT",
                        source_id=proj.name,
                        title=f"Dự án {proj.name}",
                        excerpt=f"{proj.summary or ''} [Công nghệ: {', '.join(proj.technologies[:4])}]",
                    )
                )

            # Check detailed project evidence bullet points
            for ev in proj.evidence:
                ev_text = f"{ev.get('title', '')} {ev.get('detail', '')}".lower()
                if any(k.lower() in ev_text for k in proj_keywords):
                    evidences.append(
                        EvidenceItem(
                            source_type="PROJECT",
                            source_id=proj.name,
                            title=f"{proj.name} • {ev.get('title', 'Evidence')}",
                            excerpt=ev.get("detail", "")[:180] + "...",
                        )
                    )

        # 3. Kiểm tra Soft Skills
        soft_match = comp_def.get("soft_skill_match", [])
        for sk in candidate.soft_skills:
            if any(k.lower() in sk.lower() for k in soft_match):
                evidences.append(
                    EvidenceItem(
                        source_type="SKILL",
                        source_id="soft_skills",
                        title=f"Kỹ năng mềm: {sk}",
                        excerpt=f"Hồ sơ ghi nhận kỹ năng mềm: {sk}",
                    )
                )

        # 4. Kiểm tra Roles
        role_match = comp_def.get("role_match", [])
        for proj in candidate.projects:
            if proj.role and any(r.lower() in proj.role.lower() for r in role_match):
                evidences.append(
                    EvidenceItem(
                        source_type="PROFILE",
                        source_id=proj.name,
                        title=f"Vai trò: {proj.role}",
                        excerpt=f"Đảm nhiệm vai trò '{proj.role}' trong dự án {proj.name}",
                    )
                )

        # Quyết định điểm số dựa trên mật độ bằng chứng
        if len(evidences) >= 2:
            return RequirementEvaluation(
                requirement=req,
                status=EvidenceStatus.SUPPORTED,
                score=1.0,
                confidence=ConfidenceLevel.HIGH,
                reason=f"Có {len(evidences)} bằng chứng rõ ràng chứng minh năng lực",
                evidences=evidences,
            )
        elif len(evidences) == 1:
            return RequirementEvaluation(
                requirement=req,
                status=EvidenceStatus.SUPPORTED,
                score=0.8,
                confidence=ConfidenceLevel.MEDIUM,
                reason="Tìm thấy 1 bằng chứng xác nhận năng lực",
                evidences=evidences,
            )
        else:
            return RequirementEvaluation(
                requirement=req,
                status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
                score=0.5,
                confidence=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
                reason="Chưa đủ bằng chứng trực tiếp trong hồ sơ (cần phỏng vấn/trao đổi thêm)",
                evidences=[],
            )

    def evaluate(
        self, candidate: CandidateProfileDTO, job: JobMatchInputDTO
    ) -> Tuple[MatchSignal, List[RequirementEvaluation]]:
        """Đánh giá toàn bộ các yêu cầu phi kỹ năng / competency của JD."""
        requirements = self.extract_requirements(job)

        if not requirements:
            # Job không có yêu cầu năng lực đặc thù nào được nêu
            signal = MatchSignal(
                name="requirement_fit",
                score=1.0,
                weight=0.30,
                confidence=ConfidenceLevel.HIGH,
                evidence_status=EvidenceStatus.NOT_REQUIRED,
                reason="Tin tuyển dụng không nêu yêu cầu năng lực hoặc phẩm chất đặc thù",
                evidence=[],
            )
            return signal, []

        evaluations: List[RequirementEvaluation] = []
        all_evidences: List[EvidenceItem] = []
        total_score = 0.0

        for req in requirements:
            ev_res = self.evaluate_requirement(req, candidate)
            evaluations.append(ev_res)
            total_score += ev_res.score
            all_evidences.extend(ev_res.evidences)

        avg_score = total_score / len(requirements)
        supported_count = sum(1 for e in evaluations if e.status == EvidenceStatus.SUPPORTED)

        reason = (
            f"Đáp ứng {supported_count}/{len(requirements)} yêu cầu năng lực cốt lõi "
            f"với {len(all_evidences)} bằng chứng xác thực từ Projects và Coursework"
        )

        signal = MatchSignal(
            name="requirement_fit",
            score=round(avg_score, 4),
            weight=0.30,
            confidence=ConfidenceLevel.HIGH if supported_count > 0 else ConfidenceLevel.MEDIUM,
            evidence_status=EvidenceStatus.SUPPORTED if supported_count > 0 else EvidenceStatus.INSUFFICIENT_EVIDENCE,
            reason=reason,
            evidence=all_evidences[:6],  # Lưu tối đa 6 bằng chứng tiêu biểu
        )

        return signal, evaluations


requirement_matcher = RequirementMatcher()
