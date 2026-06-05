"""T-013 selection.py 테스트 — AC-1·AC-2·AC-3."""

from __future__ import annotations

from crawler.selection import (
    SelectionReport,
    build_pool,
    classify_role_family,
    role_tier,
    select_balanced,
)

# ---------------------------------------------------------------------------
# AC-1: 제목 기반 role_family 분류
# ---------------------------------------------------------------------------


def test_AC_1_role_family_classification() -> None:
    """AC-1: 제목 키워드 → role_family 분류 (순서 우선, 미매칭→'other')."""
    assert classify_role_family("Frontend Developer") == "frontend"
    assert classify_role_family("콘텐츠 마케터") == "marketing"
    assert classify_role_family("Android Engineer") == "android"
    assert classify_role_family("DevOps SRE") == "devops_infra"
    assert classify_role_family("알 수 없는 직군 XYZ") == "other"


# ---------------------------------------------------------------------------
# AC-2: select_balanced — quota + priority backfill
# ---------------------------------------------------------------------------


def _make_pool(tiers: list[str]) -> list[dict]:
    """tier 문자열 리스트 → pool entry 리스트 생성 헬퍼."""
    return [
        {"job_id": str(i), "company": f"co{i}", "title": "Engineer", "tier": t}
        for i, t in enumerate(tiers)
    ]


def test_AC_2_select_balanced_quota() -> None:
    """AC-2: pool=50(tier 혼합), limit=10 → primary 5 + adjacent 3 + contrast 2."""
    # 50개 pool: primary 20 + adjacent 15 + weak 10 + mismatch 5
    tiers = ["primary"] * 20 + ["adjacent"] * 15 + ["weak"] * 10 + ["mismatch"] * 5
    pool = _make_pool(tiers)
    selected = select_balanced(pool, limit=10)

    assert len(selected) == 10
    counts = {t: 0 for t in ("primary", "adjacent", "weak", "mismatch")}
    for item in selected:
        counts[item["tier"]] += 1

    assert counts["primary"] == 5
    assert counts["adjacent"] == 3
    assert counts["weak"] + counts["mismatch"] == 2  # contrast = weak + mismatch


def test_AC_2_select_balanced_backfill() -> None:
    """AC-2 backfill: primary 부족 시 adjacent→weak→mismatch 순 채움."""
    # primary 2개만 존재 → 나머지를 adjacent로 채워야 함
    tiers = ["primary"] * 2 + ["adjacent"] * 20
    pool = _make_pool(tiers)
    selected = select_balanced(pool, limit=10)

    counts = {t: 0 for t in ("primary", "adjacent")}
    for item in selected:
        counts[item["tier"]] += 1

    assert counts["primary"] == 2
    assert len(selected) == min(10, len(pool))


def test_AC_2_select_balanced_small_pool() -> None:
    """AC-2: selected_count == min(limit, pool_size)."""
    pool = _make_pool(["primary"] * 3)
    selected = select_balanced(pool, limit=10)
    assert len(selected) == 3


# ---------------------------------------------------------------------------
# AC-3: 선택 리포트
# ---------------------------------------------------------------------------


def test_AC_3_selection_report() -> None:
    """AC-3: 선택 내역 리포트 — selected/skipped tier·role_family 분포 기록."""
    tiers = ["primary"] * 20 + ["adjacent"] * 15 + ["weak"] * 10 + ["mismatch"] * 5
    pool = [
        {
            "job_id": str(i),
            "company": f"co{i % 5}",
            "title": "Engineer",
            "tier": t,
            "role_family": "frontend" if i % 3 == 0 else "backend",
        }
        for i, t in enumerate(tiers)
    ]

    selected = select_balanced(pool, limit=10)
    report = SelectionReport.from_run(pool=pool, selected=selected)

    # 기본 집계 필드 존재
    assert report.selected_count == 10
    assert report.skipped_count == 40

    # tier 분포 기록
    assert "primary" in report.selected_tier_dist
    assert isinstance(report.selected_tier_dist, dict)
    assert isinstance(report.skipped_tier_dist, dict)

    # role_family 분포 기록
    assert isinstance(report.selected_role_family_dist, dict)
    assert isinstance(report.skipped_role_family_dist, dict)


def test_AC_3_selection_report_zero_primary() -> None:
    """AC-3: 주력 도메인(primary) 0건이면 명시."""
    pool = _make_pool(["adjacent"] * 5 + ["weak"] * 3)
    for item in pool:
        item["role_family"] = "backend"
    selected = select_balanced(pool, limit=5)
    report = SelectionReport.from_run(pool=pool, selected=selected)

    assert report.selected_tier_dist.get("primary", 0) == 0
    assert report.zero_primary_warning is True


# ---------------------------------------------------------------------------
# role_tier / build_pool — §3 구현 항목 커버리지
# ---------------------------------------------------------------------------


def test_role_tier_maps_alignment_to_tier() -> None:
    """role_tier: 사용자 도메인 기준 role_family → tier 매핑."""
    assert role_tier("frontend") == "primary"
    assert role_tier("backend") == "adjacent"
    assert role_tier("marketing") == "mismatch"


def test_build_pool_enriches_and_truncates() -> None:
    """build_pool: role_family·tier 채움 + pool_size 절단."""
    jobs = [
        {"job_id": "1", "company": "toss", "title": "Frontend Engineer"},
        {"job_id": "2", "company": "toss", "title": "Backend Engineer"},
        {"job_id": "3", "company": "daangn", "title": "콘텐츠 마케터"},
        {"job_id": "4", "company": "daangn", "title": "Android Engineer"},
    ]
    pool = build_pool(jobs, pool_size=10)

    # 모든 항목에 role_family·tier 채움
    assert all("role_family" in j and "tier" in j for j in pool)
    assert len(pool) == 4
    by_id = {j["job_id"]: j for j in pool}
    assert by_id["1"]["role_family"] == "frontend"
    assert by_id["1"]["tier"] == "primary"
    assert by_id["3"]["role_family"] == "marketing"
    assert by_id["3"]["tier"] == "mismatch"

    # pool_size 절단
    assert len(build_pool(jobs, pool_size=2)) == 2
