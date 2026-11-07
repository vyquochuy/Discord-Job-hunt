"""
Deterministic insight engine.

Every statement below is a rule applied to aggregates computed from the shared
job tables. There is no LLM in this path and no forecast: the engine only
describes what the current dataset contains, with the sample size and coverage
attached to each observation.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.employer_intelligence import summarize_employers
from app.services.analytics.filters import (
    JobFact,
    MarketFilters,
    SkillLink,
    load_job_facts,
    load_skill_links,
)
from app.services.analytics.geography_intelligence import summarize_geography
from app.services.analytics.overview import summarize_overview
from app.services.analytics.role_intelligence import summarize_roles
from app.services.analytics.salary_intelligence import summarize_salary
from app.services.analytics.skills_intelligence import summarize_skills
from app.services.analytics.stats import market_meta, status_for
from app.services.analytics.taxonomy import level_label

DISCLAIMER = (
    "Các nhận định dưới đây được sinh bằng quy tắc tất định từ dữ liệu hiện có. "
    "Đây là quan sát về dữ liệu, không phải dự báo tương lai. Số liệu có thể thay đổi "
    "khi pipeline thu thập thêm tin mới. Mẫu thu thập không bảo đảm đại diện thị trường IT Việt Nam."
)

METHODOLOGY = [
    "Nguồn: bảng jobs, job_skills, skills và raw_jobs trong PostgreSQL; loại bỏ tin MERGED.",
    "Danh mục nghề, vùng địa lý và role family được suy ra từ normalized_title / normalized_location.",
    "Lương dùng midpoint min–max; một đầu mút là proxy giới hạn. USD quy đổi VND estimated. Chưa có chu kỳ tháng/năm/giờ hoặc gross/net nên không bảo đảm so sánh được.",
    "Tin thiếu posted_at không tham gia phân tích xu hướng; tin thiếu lương không tham gia thống kê lương.",
    "Insights không dùng LLM và không tạo ra số liệu mới ngoài aggregate đã tính.",
]


def _insight(
    insight_id: str,
    title: str,
    detail: str,
    *,
    severity: str,
    category: str,
    confidence: str,
    evidence: Dict[str, object],
) -> Dict[str, object]:
    return {
        "id": insight_id,
        "title": title,
        "detail": detail,
        "severity": severity,
        "category": category,
        "confidence": confidence,
        "evidence": evidence,
    }


def summarize_insights(
    facts: Sequence[JobFact],
    links: Sequence[SkillLink],
    filters: MarketFilters,
) -> Dict[str, object]:
    overview = summarize_overview(facts, links, filters)
    salary = summarize_salary(facts, filters)
    skills = summarize_skills(facts, links, filters)
    roles = summarize_roles(facts, filters)
    geography = summarize_geography(facts, filters)
    employers = summarize_employers(facts, filters)

    total = len(facts)
    insights: List[Dict[str, object]] = []

    # 1. Scope
    date_range = overview["data_quality"]["date_range"]
    insights.append(
        _insight(
            "data_scope",
            "Phạm vi dữ liệu",
            (
                f"Phân tích dựa trên {total} tin trong khoảng "
                f"{date_range['min'] or '—'} → {date_range['max'] or '—'} "
                f"({date_range['days']} ngày dữ liệu)."
            ),
            severity="info",
            category="data",
            confidence="high",
            evidence={"total_jobs": total, "date_range": date_range},
        )
    )

    # 2. Salary coverage
    salary_coverage = salary["coverage"]
    coverage_ratio = float(salary_coverage["ratio"])
    if total:
        insights.append(
            _insight(
                "salary_coverage",
                "Độ phủ dữ liệu lương",
                (
                    f"{salary_coverage['with_salary']}/{total} tin "
                    f"({coverage_ratio * 100:.1f}%) có lương hợp lệ; "
                    f"{salary_coverage['negotiable']} tin ghi thỏa thuận. "
                    "Các chỉ số chỉ mô tả tin có lương hợp lệ, không bảo đảm đại diện cho thị trường."
                ),
                severity="warning" if coverage_ratio < 0.25 else "info",
                category="salary",
                confidence="high",
                evidence=salary_coverage,
            )
        )

    # 3. Top skill
    top_skills = skills.get("top_skills", [])
    if top_skills:
        top_skill = top_skills[0]
        insights.append(
            _insight(
                "top_skill",
                "Kỹ năng được nhắc nhiều nhất",
                (
                    f"{top_skill['skill']} xuất hiện trong {top_skill['jobs']} tin "
                    f"({float(top_skill['share']) * 100:.1f}% nhóm tin có kỹ năng)."
                ),
                severity="info",
                category="skills",
                confidence="high",
                evidence=top_skill,
            )
        )

    # 4. Leading category
    categories = overview["distributions"]["categories"]
    if categories:
        leader = max(categories, key=lambda item: item["jobs"])
        insights.append(
            _insight(
                "category_leader",
                "Nhóm nghề dẫn đầu",
                (
                    f"{leader['label']} có {leader['jobs']} tin "
                    f"({float(leader['share']) * 100:.1f}% tổng mẫu)."
                ),
                severity="info",
                category="roles",
                confidence="medium",
                evidence=leader,
            )
        )

    # 5. Geographic concentration
    regions = geography.get("regions", [])
    if regions:
        top_region = max(regions, key=lambda item: item["jobs"])
        insights.append(
            _insight(
                "location_concentration",
                "Mức tập trung địa lý",
                (
                    f"{top_region['label']} chiếm {top_region['jobs']} tin "
                    f"({float(top_region['share']) * 100:.1f}% tổng mẫu); "
                    f"{len(regions)} vùng có dữ liệu."
                ),
                severity="warning" if float(top_region["share"]) >= 0.5 else "info",
                category="geography",
                confidence="medium",
                evidence=top_region,
            )
        )

    # 6. Employer concentration
    concentration = employers["concentration"]
    if total:
        insights.append(
            _insight(
                "employer_concentration",
                "Mức tập trung nhà tuyển dụng",
                (
                    f"Top 10 nhà tuyển dụng chiếm {float(concentration['top10_share']) * 100:.1f}% tin có công ty xác định; "
                    f"HHI = {concentration['hhi']} trên {concentration['total_companies']} công ty. "
                    f"{concentration['repeat_hirers']} công ty tuyển từ 3 vị trí trở lên."
                ),
                severity="info",
                category="employers",
                confidence="high",
                evidence=concentration,
            )
        )

    # 7. Unknown seniority
    missing_level = int(overview["data_quality"]["missing_level"])
    if total and missing_level / total >= 0.4:
        insights.append(
            _insight(
                "level_unknown",
                "Cấp bậc chưa được xác định",
                (
                    f"{missing_level}/{total} tin ({missing_level / total * 100:.1f}%) "
                    "chưa suy ra được cấp bậc từ tiêu đề/mô tả. Các thống kê theo cấp bậc "
                    "cần được đọc cùng tỷ lệ này."
                ),
                severity="warning",
                category="data",
                confidence="high",
                evidence={
                    "missing_level": missing_level,
                    "total": total,
                    "label": level_label("UNKNOWN"),
                },
            )
        )

    # 8. Remote / hybrid share
    remote_share = geography["remote_share"]
    insights.append(
        _insight(
            "remote_share",
            "Tỷ lệ làm việc linh hoạt",
            (
                f"Remote: {remote_share['remote']} tin "
                f"({float(remote_share['remote_ratio']) * 100:.1f}%); "
                f"hybrid: {remote_share['hybrid']} tin. "
                f"Tổng remote + hybrid chiếm {float(remote_share['flexible_ratio']) * 100:.1f}%."
            ),
            severity="info",
            category="geography",
            confidence="high",
            evidence=remote_share,
        )
    )

    # 9. Bulk backfill spike
    spikes = overview["data_quality"]["bulk_spikes"]
    if spikes:
        first = spikes[0]
        insights.append(
            _insight(
                "bulk_spike",
                "Spike dữ liệu có thể liên quan nhập hàng loạt",
                (
                    f"Ngày {first['date']} có {first['jobs']} tin, gấp {first['ratio']} lần "
                    f"trung vị ngày thường ({first['median_jobs']} tin). Có thể liên quan "
                    "backfill/initial scan; chưa xác định nguyên nhân và không thể kết luận "
                    "nhu cầu tuyển dụng tăng đột biến."
                ),
                severity="warning",
                category="data",
                confidence="high",
                evidence={"spikes": spikes},
            )
        )

    # 10. Salary leader (only when there is enough data)
    salary_categories = salary.get("by_category", [])
    if salary_categories and salary["meta"]["status"] != "empty":
        leader = salary_categories[0]
        insights.append(
            _insight(
                "salary_leader",
                "Nhóm có median lương cao nhất",
                (
                    f"{leader['label']} có median {leader['median']:,.0f} VND "
                    f"(N={leader['salary_sample']}, "
                    f"p25–p75 = {leader['p25']:,.0f}–{leader['p75']:,.0f} VND). "
                    "Chỉ so sánh trong nhóm tin có công bố lương."
                ),
                severity="info" if leader["status"] == "ok" else "warning",
                category="salary",
                confidence="medium" if leader["status"] == "ok" else "low",
                evidence=leader,
            )
        )

    # 11. Emerging skill
    emerging_skills = skills.get("emerging", {})
    if emerging_skills.get("available") and emerging_skills.get("items"):
        item = emerging_skills["items"][0]
        insights.append(
            _insight(
                "emerging_skill",
                "Kỹ năng tăng tỷ trọng gần đây",
                (
                    f"{item['skill']} tăng từ {float(item['earlier_share']) * 100:.1f}% "
                    f"lên {float(item['recent_share']) * 100:.1f}% giữa hai nửa thời gian "
                    f"(+{float(item['delta']) * 100:.1f} điểm %). Đây là so sánh nội bộ "
                    "trong dữ liệu, không phải dự báo."
                ),
                severity="info",
                category="skills",
                confidence="low",
                evidence=item,
            )
        )

    # 12. Emerging role
    emerging_roles = roles.get("emerging", {})
    if emerging_roles.get("available") and emerging_roles.get("items"):
        item = emerging_roles["items"][0]
        insights.append(
            _insight(
                "emerging_role",
                "Vị trí tăng tỷ trọng gần đây",
                (
                    f"{item['title']} tăng từ {float(item['earlier_share']) * 100:.1f}% "
                    f"lên {float(item['recent_share']) * 100:.1f}% giữa hai nửa thời gian."
                ),
                severity="info",
                category="roles",
                confidence="low",
                evidence=item,
            )
        )

    notes: List[str] = []
    if total < 30:
        notes.append(f"Mẫu tổng nhỏ (N={total}); mọi nhận định chỉ mang tính mô tả.")
    if not skills.get("emerging", {}).get("available"):
        notes.append(str(skills.get("emerging", {}).get("reason") or ""))

    meta = market_meta(
        filters.as_dict(),
        total_jobs=total,
        sample_size=total,
        coverage=1.0,
        status=status_for(total),
        notes=[note for note in notes if note],
    )

    return {
        "meta": meta,
        "disclaimer": DISCLAIMER,
        "insights": insights,
        "methodology": METHODOLOGY,
        "data_quality": overview["data_quality"],
    }


async def get_insights(
    db: AsyncSession, filters: MarketFilters
) -> Dict[str, object]:
    facts = await load_job_facts(db, filters)
    links = await load_skill_links(db, facts)
    return summarize_insights(facts, links, filters)
