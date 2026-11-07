"""Skills Intelligence tab aggregates."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from itertools import combinations
from typing import Dict, List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.filters import (
    JobFact,
    MarketFilters,
    SkillLink,
    load_job_facts,
    load_skill_links,
    resolve_range,
)
from app.services.analytics.stats import market_meta, share, status_for

SKILL_CATEGORY_LABELS: Dict[str, str] = {
    "LANGUAGE": "Ngôn ngữ lập trình",
    "FRAMEWORK": "Framework / Thư viện",
    "DATABASE": "Cơ sở dữ liệu",
    "CLOUD": "Cloud",
    "TOOL": "Công cụ",
    "CONCEPT": "Khái niệm",
    "OTHER": "Khác",
}

SKILL_CATEGORY_ORDER = list(SKILL_CATEGORY_LABELS.keys())


def _skill_items(
    skill_counts: Counter,
    skill_categories: Dict[str, str],
    jobs_with_skills: int,
    *,
    limit: Optional[int] = None,
    skill_category: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    search_lower = search.lower() if search else None
    for skill, count in skill_counts.most_common():
        category = skill_categories.get(skill, "OTHER")
        if skill_category and category != skill_category:
            continue
        if search_lower and search_lower not in skill.lower():
            continue
        items.append(
            {
                "skill": skill,
                "category": category,
                "jobs": int(count),
                "share": share(count, jobs_with_skills),
                "rank": len(items) + 1,
            }
        )
        if limit is not None and len(items) >= limit:
            break
    return items


def _cooccurrence(
    links: Sequence[SkillLink],
    top_skills: Sequence[str],
    jobs_with_skills: int,
    skill_counts: Counter,
) -> List[Dict[str, object]]:
    if jobs_with_skills < 10 or len(top_skills) < 2:
        return []
    allowed = set(top_skills)
    job_skills: Dict[object, set] = defaultdict(set)
    for link in links:
        if link.skill in allowed:
            job_skills[link.job_id].add(link.skill)
    pair_counts: Counter = Counter()
    for skills in job_skills.values():
        if len(skills) < 2:
            continue
        for first, second in combinations(sorted(skills), 2):
            pair_counts[(first, second)] += 1

    items: List[Dict[str, object]] = []
    for (first, second), count in pair_counts.most_common(10):
        denominator = skill_counts[first] * skill_counts[second]
        lift = (count * jobs_with_skills / denominator) if denominator else 0.0
        items.append(
            {
                "a": first,
                "b": second,
                "jobs": int(count),
                "lift": round(lift, 2),
            }
        )
    return items


def _by_level(
    links: Sequence[SkillLink],
    facts: Sequence[JobFact],
    top_skills: Sequence[str],
) -> List[Dict[str, object]]:
    job_levels = {fact.id: fact.level for fact in facts}
    items: List[Dict[str, object]] = []
    for skill in top_skills:
        levels: Counter = Counter()
        for link in links:
            if link.skill == skill:
                levels[job_levels.get(link.job_id, "UNKNOWN")] += 1
        items.append(
            {
                "skill": skill,
                "total": sum(levels.values()),
                "levels": {key: int(value) for key, value in levels.items()},
            }
        )
    return items


def _emerging(
    links: Sequence[SkillLink],
    facts: Sequence[JobFact],
    filters: MarketFilters,
) -> Dict[str, object]:
    start, end = resolve_range(facts, filters)
    if start is None or end is None:
        return {
            "available": False,
            "reason": "Không có đủ dữ liệu posted_at để so sánh hai nửa thời gian.",
            "items": [],
        }
    span_days = (end - start).days + 1
    if span_days < 21:
        return {
            "available": False,
            "reason": "Cần khoảng thời gian ít nhất 21 ngày để so sánh nửa đầu và nửa cuối.",
            "items": [],
        }
    midpoint = start + timedelta(days=span_days // 2)
    earlier_ids = {
        fact.id for fact in facts if fact.posted_date and fact.posted_date < midpoint
    }
    recent_ids = {
        fact.id for fact in facts if fact.posted_date and fact.posted_date >= midpoint
    }
    earlier_counts: Counter = Counter()
    recent_counts: Counter = Counter()
    earlier_jobs = set()
    recent_jobs = set()
    for link in links:
        if link.job_id in earlier_ids:
            earlier_counts[link.skill] += 1
            earlier_jobs.add(link.job_id)
        elif link.job_id in recent_ids:
            recent_counts[link.skill] += 1
            recent_jobs.add(link.job_id)

    earlier_denom = len(earlier_jobs)
    recent_denom = len(recent_jobs)
    if earlier_denom == 0 or recent_denom == 0:
        return {
            "available": False,
            "reason": "Một trong hai nửa thời gian không có tin nào kèm kỹ năng.",
            "items": [],
        }

    items: List[Dict[str, object]] = []
    for skill, recent_count in recent_counts.items():
        if recent_count < 5:
            continue
        earlier_count = earlier_counts.get(skill, 0)
        recent_share = recent_count / recent_denom
        earlier_share = earlier_count / earlier_denom
        delta = recent_share - earlier_share
        if delta <= 0:
            continue
        items.append(
            {
                "skill": skill,
                "recent_jobs": int(recent_count),
                "earlier_jobs": int(earlier_count),
                "recent_share": round(recent_share, 4),
                "earlier_share": round(earlier_share, 4),
                "delta": round(delta, 4),
            }
        )
    items.sort(key=lambda item: item["delta"], reverse=True)
    return {
        "available": True,
        "reason": None,
        "midpoint": midpoint.isoformat(),
        "items": items[:8],
    }


def summarize_skills(
    facts: Sequence[JobFact],
    links: Sequence[SkillLink],
    filters: MarketFilters,
    *,
    limit: int = 25,
    skill_category: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, object]:
    total = len(facts)
    jobs_with_skills = len({link.job_id for link in links})
    skill_counts: Counter = Counter(link.skill for link in links)
    skill_categories: Dict[str, str] = {
        link.skill: link.category for link in links
    }

    items = _skill_items(
        skill_counts,
        skill_categories,
        jobs_with_skills,
        limit=limit,
        skill_category=skill_category,
        search=search,
    )
    all_items = _skill_items(
        skill_counts,
        skill_categories,
        jobs_with_skills,
        skill_category=skill_category,
        search=search,
    )

    by_category: List[Dict[str, object]] = []
    for category in SKILL_CATEGORY_ORDER:
        category_links = [link for link in links if link.category == category]
        if not category_links:
            continue
        category_jobs = len({link.job_id for link in category_links})
        category_items = _skill_items(
            Counter(link.skill for link in category_links),
            skill_categories,
            jobs_with_skills,
            limit=10,
            search=search,
        )
        if category_items:
            by_category.append(
                {
                    "category": category,
                    "label": SKILL_CATEGORY_LABELS.get(category, category),
                    "jobs": category_jobs,
                    "skills": category_items,
                }
            )

    top_names = [str(item["skill"]) for item in all_items[:15]]
    cooccurrence = _cooccurrence(links, top_names, jobs_with_skills, skill_counts)
    by_level = _by_level(links, facts, top_names[:10])
    emerging = _emerging(links, facts, filters)

    coverage = share(jobs_with_skills, total)
    notes: List[str] = []
    if total - jobs_with_skills > 0:
        notes.append(
            f"{total - jobs_with_skills}/{total} tin không có kỹ năng đã chuẩn hóa; "
            "tỷ lệ kỹ năng được tính trên số tin có ít nhất một kỹ năng."
        )
    if filters.skill:
        notes.append(
            f"Đang lọc theo kỹ năng '{filters.skill}'; bảng xếp hạng phản ánh các kỹ năng "
            "đồng xuất hiện trong nhóm tin này."
        )
    if not emerging["available"]:
        notes.append(str(emerging["reason"]))
    if jobs_with_skills < 10:
        notes.append(
            f"Mẫu kỹ năng nhỏ (N={jobs_with_skills}); không nên suy rộng."
        )

    meta = market_meta(
        filters.as_dict(),
        total_jobs=total,
        sample_size=jobs_with_skills,
        coverage=coverage,
        status=status_for(
            jobs_with_skills, coverage, min_sample=10, min_coverage=0.5
        ),
        notes=notes,
    )

    return {
        "meta": meta,
        "jobs_with_skills": jobs_with_skills,
        "unique_skills": len(skill_counts),
        "top_skills": items,
        "by_category": by_category,
        "cooccurrence": cooccurrence,
        "by_level": by_level,
        "emerging": emerging,
    }


async def get_skills_intelligence(
    db: AsyncSession,
    filters: MarketFilters,
    *,
    limit: int = 25,
    skill_category: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, object]:
    facts = await load_job_facts(db, filters)
    links = await load_skill_links(db, facts)
    return summarize_skills(
        facts,
        links,
        filters,
        limit=limit,
        skill_category=skill_category,
        search=search,
    )
