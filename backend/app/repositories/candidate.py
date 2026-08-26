import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import (
    Candidate,
    CandidateSkill,
    CandidateExperience,
    CandidateProject,
    CandidateCertification,
)
from app.schemas.candidate import CandidateCreate, CandidateUpdate


class CandidateRepository:
    """
    Repository phụ trách mọi tương tác Database liên quan đến Hồ sơ Ứng viên (Candidate Profile).
    """

    @staticmethod
    async def get_profile(session: AsyncSession) -> Optional[Candidate]:
        """
        Lấy thông tin hồ sơ ứng viên chính kèm theo tất cả các quan hệ liên kết
        (skills, experiences, projects, certifications) thông qua eager loading.
        """
        stmt = (
            select(Candidate)
            .options(
                selectinload(Candidate.skills),
                selectinload(Candidate.experiences),
                selectinload(Candidate.projects),
                selectinload(Candidate.certifications),
            )
            .order_by(Candidate.created_at.asc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_by_id(session: AsyncSession, candidate_id: uuid.UUID) -> Optional[Candidate]:
        """Lấy thông tin ứng viên theo ID cụ thể."""
        stmt = (
            select(Candidate)
            .options(
                selectinload(Candidate.skills),
                selectinload(Candidate.experiences),
                selectinload(Candidate.projects),
                selectinload(Candidate.certifications),
            )
            .where(Candidate.id == candidate_id)
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @classmethod
    async def sync_from_parsed_context(
        cls, session: AsyncSession, parsed: Dict[str, Any]
    ) -> Candidate:
        """
        Đồng bộ toàn bộ dữ liệu hồ sơ từ context files (YAML, LaTeX, Markdown) vào Database.
        Nếu ứng viên chưa tồn tại, tạo mới. Nếu đã tồn tại, cập nhật và làm mới các bảng quan hệ.
        """
        candidate = await cls.get_profile(session)

        cand_data = parsed.get("candidate", {})
        full_name = cand_data.get("name") or "Vy Quoc Huy"
        headline = cand_data.get("headline")
        email = cand_data.get("email")
        phone = cand_data.get("phone")
        location = cand_data.get("location")
        github_url = cand_data.get("github")
        linkedin_url = cand_data.get("linkedin")
        portfolio_url = cand_data.get("portfolio")
        summary = cand_data.get("summary")

        education = parsed.get("education", [])
        target_roles = parsed.get("target_roles", [])
        target_locations = parsed.get("target_locations", [])
        preferences = parsed.get("preferences", {})
        raw_master_resume_md = parsed.get("raw_master_resume_md")
        raw_master_resume_tex = parsed.get("raw_master_resume_tex")

        # Chuẩn bị danh sách quan hệ con
        new_skills: List[CandidateSkill] = []
        skills_dict = parsed.get("skills", {})
        for cat, items in skills_dict.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, str) and item.strip():
                        new_skills.append(
                            CandidateSkill(
                                category=cat,
                                name=item.strip(),
                                proficiency=None,
                            )
                        )
                    elif isinstance(item, dict):
                        sk_name = item.get("name") or item.get("language")
                        if sk_name and isinstance(sk_name, str):
                            new_skills.append(
                                CandidateSkill(
                                    category=cat,
                                    name=sk_name.strip(),
                                    proficiency=item.get("level"),
                                )
                            )

        new_projects: List[CandidateProject] = []
        projects_list = parsed.get("projects", [])
        for idx, p in enumerate(projects_list):
            if isinstance(p, dict) and p.get("name"):
                period_val = p.get("period")
                if isinstance(period_val, dict):
                    start = period_val.get("start", "")
                    end = period_val.get("end") or "Present"
                    period_str = f"{start} -- {end}" if (start and end) else (start or None)
                else:
                    period_str = str(period_val) if period_val else None

                # Chuẩn hóa evidence_points: hỗ trợ schema mới (core + supporting_evidence) và schema cũ (evidence / evidence_points)
                ev_points: List[dict[str, Any]] = []
                if p.get("core") and isinstance(p["core"], dict):
                    core_obj = p["core"]
                    ev_points.append({
                        "title": core_obj.get("title", "Core"),
                        "detail": core_obj.get("description", "") or core_obj.get("detail", ""),
                        "is_core": True,
                        "technology_refs": core_obj.get("technology_refs", []),
                    })
                    for sup in p.get("supporting_evidence", []):
                        if isinstance(sup, dict):
                            ev_points.append({
                                "title": sup.get("title", ""),
                                "detail": sup.get("detail", "") or sup.get("description", ""),
                                "is_core": False,
                                "technologies": sup.get("technologies", []),
                            })
                elif p.get("evidence"):
                    raw_ev = p["evidence"]
                    for b_idx, item in enumerate(raw_ev):
                        if isinstance(item, dict):
                            ev_dict = dict(item)
                            if "is_core" not in ev_dict and b_idx == 0:
                                ev_dict["is_core"] = True
                            ev_points.append(ev_dict)
                        else:
                            ev_points.append({"title": "", "detail": str(item), "is_core": (b_idx == 0)})
                elif p.get("evidence_points"):
                    raw_ev = p["evidence_points"]
                    for b_idx, item in enumerate(raw_ev):
                        if isinstance(item, dict):
                            ev_dict = dict(item)
                            if "is_core" not in ev_dict and b_idx == 0:
                                ev_dict["is_core"] = True
                            ev_points.append(ev_dict)
                        else:
                            ev_points.append({"title": "", "detail": str(item), "is_core": (b_idx == 0)})

                new_projects.append(
                    CandidateProject(
                        name=p["name"],
                        role=p.get("role"),
                        summary=p.get("summary"),
                        period=period_str,
                        repository_url=p.get("repository_url"),
                        demo_url=p.get("demo_url"),
                        technologies=p.get("technologies", []),
                        evidence_points=ev_points,
                        order=idx,
                    )
                )

        new_experiences: List[CandidateExperience] = []
        exp_list = parsed.get("experience", [])
        for idx, e in enumerate(exp_list):
            if isinstance(e, dict) and e.get("company") and e.get("role"):
                new_experiences.append(
                    CandidateExperience(
                        company=e["company"],
                        role=e["role"],
                        period=e.get("period"),
                        location=e.get("location"),
                        description=e.get("description"),
                        achievements=e.get("achievements", []),
                        order=idx,
                    )
                )

        new_certifications: List[CandidateCertification] = []
        cert_list = parsed.get("certifications", [])
        for c in cert_list:
            if isinstance(c, dict) and c.get("name"):
                new_certifications.append(
                    CandidateCertification(
                        name=c["name"],
                        issuer=c.get("issuer"),
                        issue_year=c.get("year"),
                        credential_url=c.get("credential_url"),
                    )
                )

        if not candidate:
            candidate = Candidate(
                full_name=full_name,
                headline=headline,
                email=email,
                phone=phone,
                location=location,
                github_url=github_url,
                linkedin_url=linkedin_url,
                portfolio_url=portfolio_url,
                summary=summary,
                education=education,
                target_roles=target_roles,
                target_locations=target_locations,
                preferences=preferences,
                raw_master_resume_md=raw_master_resume_md,
                raw_master_resume_tex=raw_master_resume_tex,
                skills=new_skills,
                projects=new_projects,
                experiences=new_experiences,
                certifications=new_certifications,
            )
            session.add(candidate)
        else:
            candidate.full_name = full_name
            if headline:
                candidate.headline = headline
            if email:
                candidate.email = email
            if phone:
                candidate.phone = phone
            if location:
                candidate.location = location
            if github_url:
                candidate.github_url = github_url
            if linkedin_url:
                candidate.linkedin_url = linkedin_url
            if portfolio_url:
                candidate.portfolio_url = portfolio_url
            if summary:
                candidate.summary = summary
            candidate.education = education
            candidate.target_roles = target_roles
            candidate.target_locations = target_locations
            candidate.preferences = preferences
            if raw_master_resume_md:
                candidate.raw_master_resume_md = raw_master_resume_md
            if raw_master_resume_tex:
                candidate.raw_master_resume_tex = raw_master_resume_tex

            # Gán lại quan hệ
            candidate.skills = new_skills
            candidate.projects = new_projects
            candidate.experiences = new_experiences
            candidate.certifications = new_certifications

        await session.commit()
        return await cls.get_by_id(session, candidate.id)

    @classmethod
    async def update_profile_fields(
        cls, session: AsyncSession, candidate_id: uuid.UUID, update_data: CandidateUpdate
    ) -> Optional[Candidate]:
        """Cập nhật các trường thông tin của ứng viên."""
        candidate = await cls.get_by_id(session, candidate_id)
        if not candidate:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(candidate, key, value)

        await session.commit()
        return await cls.get_by_id(session, candidate.id)
