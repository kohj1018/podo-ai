"""T-003 Acceptance Criteria tests — compute_fit (rank_aggregate.py).

테스트 픽스처는 SPEC §4 알고리즘을 직접 검증한다.
"""

from core.models import MatchingTable, MatchRow
from worker.rank_aggregate import compute_fit

# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------


def _row(
    rid: str,
    req_type: str = "required",
    req_nature: str = "technical",
    prereq_status: str = "prerequisite",
    req_category: str = "other",
    match_level: str = "direct",
    confidence: str = "high",
    invalid_match: bool = False,
    risk_note: str = "",
    req_text: str = "some requirement",
) -> MatchRow:
    """MatchRow 생성 헬퍼 — 기본값으로 직접/high 매칭."""
    return MatchRow(
        requirement_id=rid,
        requirement_text=req_text,
        requirement_type=req_type,
        requirement_nature=req_nature,
        prerequisite_status=prereq_status,
        requirement_category=req_category,
        match_level=match_level,
        confidence=confidence,
        invalid_match=invalid_match,
        risk_note=risk_note,
    )


def _table(rows: list[MatchRow], job_id: str = "job-1") -> MatchingTable:
    return MatchingTable(job_id=job_id, company="Corp", title="Dev", rows=rows)


# ---------------------------------------------------------------------------
# AC-1: role-defining critical 미충족 2건 → level<=2, cap_reason에 기록
# ---------------------------------------------------------------------------


def test_AC_1_role_defining_critical_cap() -> None:
    """AC-1: role-defining critical prerequisite 미충족 2건 → level<=2, cap_reason 포함."""
    rows = [
        # role-defining critical 미충족 2건 (prerequisite, technical, 비마이너 category)
        _row(
            "R1",
            req_type="critical",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="missing",
            req_text="React 심화 경험",
        ),
        _row(
            "R2",
            req_type="critical",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="missing",
            req_text="TypeScript 심화",
        ),
        # 일반 충족 행 (비율을 높게 만들어 cap이 binding 되도록)
        _row(
            "R3",
            req_type="required",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="direct",
            confidence="high",
        ),
        _row(
            "R4",
            req_type="required",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="direct",
            confidence="high",
        ),
        _row(
            "R5",
            req_type="preferred",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="direct",
            confidence="high",
        ),
    ]
    table = _table(rows)
    result = compute_fit(table, "strong")

    assert result["level"] <= 2, (
        f"level={result['level']} should be <=2 (role-defining critical gap cap)"
    )
    cap_reason = result["coverage"]["cap_reason"]
    assert "role-defining critical gaps x2" in cap_reason, (
        f"cap_reason='{cap_reason}' should contain 'role-defining critical gaps x2'"
    )


# ---------------------------------------------------------------------------
# AC-2: alignment="mismatch" + role_evidence 유무에 따른 동적 cap
# ---------------------------------------------------------------------------


def test_AC_2_mismatch_dynamic_cap() -> None:
    """AC-2a: mismatch + core direct 매칭 0 → level==1."""
    # core direct 매칭 없는 표 (모두 missing/weak, 또는 non-core)
    rows = [
        _row(
            "R1",
            req_type="critical",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="missing",
            req_text="Python",
        ),
        _row(
            "R2",
            req_type="required",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="missing",
            req_text="Django",
        ),
        _row(
            "R3",
            req_type="required",
            req_nature="behavioral",
            prereq_status="prerequisite",
            req_category="other",
            match_level="direct",
            confidence="high",
            req_text="협업",
        ),
    ]
    table = _table(rows)
    result = compute_fit(table, "mismatch")

    # role_evidence=0 이면 mismatch → cap 1
    assert result["coverage"]["role_evidence_matches"] == 0
    assert result["level"] == 1, (
        f"level={result['level']} should be 1 (mismatch, no role_evidence)"
    )


def test_AC_2_mismatch_with_one_core_direct() -> None:
    """AC-2b: mismatch + core prerequisite direct 매칭 1건 → level==2 (cap2)."""
    rows = [
        # core direct 1건 (CORE_NATURES: technical, domain, experience_level, language)
        _row(
            "R1",
            req_type="critical",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="direct",
            confidence="high",
            req_text="React",
        ),
        _row(
            "R2",
            req_type="required",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="missing",
            req_text="TypeScript",
        ),
    ]
    table = _table(rows)
    result = compute_fit(table, "mismatch")

    assert result["coverage"]["role_evidence_matches"] >= 1
    # mismatch + role_evidence>0 → cap 2
    assert result["level"] == 2, (
        f"level={result['level']} should be 2 (mismatch, role_evidence>0 → cap2)"
    )


# ---------------------------------------------------------------------------
# AC-3: dedup_required_preferred 플래그 — False=baseline, True=cap에서 제외
# ---------------------------------------------------------------------------


def test_AC_3_dedup_flag_vs_baseline() -> None:
    """AC-3: dedup=False는 baseline과 동일, True는 level>=baseline이고 dedup_audit에 기록."""
    # required 행과 그 preferred 트윈이 동일 역량으로 중복
    rows = [
        # role-defining critical 미충족 1건 → 단독이면 cap3 정도
        _row(
            "R1",
            req_type="critical",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="missing",
            req_text="React 개발 경험",
        ),
        # required 미충족 행 (cap을 driving하는 행)
        _row(
            "R2",
            req_type="required",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="missing",
            req_text="React 개발 경험",
        ),
        # preferred 트윈 — 동일 역량 (containment: req_text가 pref_text에 포함)
        _row(
            "R3",
            req_type="preferred",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="missing",
            req_text="React 개발 경험 (선호)",
        ),
        # 일반 직접 매칭 행
        _row(
            "R4",
            req_type="required",
            req_nature="technical",
            prereq_status="prerequisite",
            req_category="other",
            match_level="direct",
            confidence="high",
        ),
    ]
    table = _table(rows)

    result_off = compute_fit(table, "weak", dedup_required_preferred=False)
    result_on = compute_fit(table, "weak", dedup_required_preferred=True)

    # False(baseline)와 True의 level 비교: True >= False (dedup이 cap을 완화)
    assert result_on["level"] >= result_off["level"], (
        f"dedup=True level={result_on['level']} should be >= dedup=False level={result_off['level']}"
    )
    # dedup=True일 때 dedup_audit에 기록이 있어야 한다
    assert len(result_on["dedup_audit"]) > 0, (
        "dedup_audit should be non-empty when dedup=True detects duplicates"
    )

    # dedup=False는 dedup_audit 비어 있음 (플래그 미사용)
    assert len(result_off["dedup_audit"]) == 0, (
        "dedup_audit should be empty when dedup=False"
    )
