"""T-002 Acceptance Criteria tests — core data contract (models.py)."""

from core.models import (
    EvidenceItem,
    JobPosting,
    Requirement,
    domain_alignment,
)

# ---------------------------------------------------------------------------
# AC-1: round-trip — valid dict input → model_dump() preserves all fields
# ---------------------------------------------------------------------------


def test_AC_1_roundtrip() -> None:
    """AC-1: 유효한 dict → 모델 파싱 → model_dump() round-trip 보존."""
    evidence_dict = {
        "evidence_id": "E1",
        "title": "NAVER 인턴",
        "source_section": "Experience",
        "exact_quote": "React로 대시보드 개발",
        "normalized_summary": "React 기반 대시보드 개발 경험",
        "skills": ["React"],
        "domain": ["frontend"],
        "evidence_type": "work_experience",
        "strength": "strong",
        "recency": "2024",
    }
    item = EvidenceItem.model_validate(evidence_dict)
    dumped = item.model_dump()
    assert dumped["evidence_id"] == "E1"
    assert dumped["title"] == "NAVER 인턴"
    assert dumped["skills"] == ["React"]
    assert dumped["evidence_type"] == "work_experience"
    assert dumped["strength"] == "strong"

    req_dict = {
        "requirement_id": "R1",
        "requirement_text": "React 개발 경험",
        "requirement_type": "required",
        "requirement_nature": "technical",
        "requirement_origin": "explicit_requirement",
        "prerequisite_status": "prerequisite",
        "alternatives": [],
        "requirement_category": "framework",
        "alternative_match_policy": "exact_or_same_category",
    }
    req = Requirement.model_validate(req_dict)
    req_dumped = req.model_dump()
    assert req_dumped["requirement_id"] == "R1"
    assert req_dumped["requirement_type"] == "required"
    assert req_dumped["prerequisite_status"] == "prerequisite"

    jp_dict = {
        "job_id": "job-1",
        "company": "TechCorp",
        "title": "Frontend Engineer",
        "url": "https://example.com/jobs/1",
        "role_family": "frontend",
        "requirements": [req_dict],
        "preferred_requirements": [],
        "responsibilities": ["서비스 개발"],
        "hard_constraints": [],
        "tech_stack": ["React"],
        "raw_text": "Frontend 개발자 모집",
    }
    jp = JobPosting.model_validate(jp_dict)
    jp_dumped = jp.model_dump()
    assert jp_dumped["job_id"] == "job-1"
    assert jp_dumped["role_family"] == "frontend"
    assert len(jp_dumped["requirements"]) == 1


# ---------------------------------------------------------------------------
# AC-2: enum clamp + list coercion
# ---------------------------------------------------------------------------


def test_AC_2_enum_clamp_and_list_coercion() -> None:
    """AC-2: 허용값 밖 enum → default 클램프, 콤마 문자열 → list[str]."""
    # bogus requirement_type → default "required"
    req = Requirement(
        requirement_id="R2",
        requirement_text="테스트 경험",
        requirement_type="bogus",  # type: ignore[arg-type]
    )
    assert req.requirement_type == "required"

    # bogus strength → default "medium"
    ev = EvidenceItem(
        evidence_id="E2",
        title="Test",
        source_section="Skills",
        exact_quote="Python",
        normalized_summary="Python 경험",
        skills="Python,JavaScript",  # type: ignore[arg-type]  # comma string → list
        domain=[],
        evidence_type="skills",
        strength="bogus_strength",  # type: ignore[arg-type]
        recency=None,
    )
    assert ev.strength == "medium"
    assert ev.skills == ["Python", "JavaScript"]

    # bogus evidence_type → default "other"
    ev2 = EvidenceItem(
        evidence_id="E3",
        title="Test",
        source_section="Other",
        exact_quote="Some text",
        normalized_summary="Summary",
        skills=[],
        domain=[],
        evidence_type="invalid_type",  # type: ignore[arg-type]
        strength="strong",
        recency=None,
    )
    assert ev2.evidence_type == "other"


# ---------------------------------------------------------------------------
# AC-3: JobPosting.all_requirements() = requirements + preferred (순서 보존)
# ---------------------------------------------------------------------------


def test_AC_3_all_requirements() -> None:
    """AC-3: requirements=[R1] + preferred=[P1] → all_requirements()=[R1, P1]."""
    r1 = {
        "requirement_id": "R1",
        "requirement_text": "React",
        "requirement_type": "required",
    }
    p1 = {
        "requirement_id": "P1",
        "requirement_text": "TypeScript",
        "requirement_type": "preferred",
    }
    jp = JobPosting(
        job_id="job-2",
        company="Corp",
        title="FE Dev",
        url="https://example.com",
        requirements=[Requirement.model_validate(r1)],
        preferred_requirements=[Requirement.model_validate(p1)],
        raw_text="",
    )
    all_reqs = jp.all_requirements()
    assert len(all_reqs) == 2
    assert all_reqs[0].requirement_id == "R1"
    assert all_reqs[1].requirement_id == "P1"


# ---------------------------------------------------------------------------
# AC-4: domain_alignment
# ---------------------------------------------------------------------------


def test_AC_4_domain_alignment() -> None:
    """AC-4: domain_alignment(rf, primary, secondary) — 정해진 tier 반환."""
    primary = {"frontend", "web"}
    secondary = {"backend"}

    result_fe, _ = domain_alignment("frontend", primary, secondary)
    assert result_fe == "strong"

    result_be, _ = domain_alignment("backend", primary, secondary)
    assert result_be == "adjacent"

    result_mkt, _ = domain_alignment("marketing", primary, secondary)
    assert result_mkt == "mismatch"

    result_data, _ = domain_alignment("data", primary, secondary)
    assert result_data == "weak"
