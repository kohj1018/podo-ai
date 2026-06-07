"""T-070 registry_seed 검증 — AC-1, AC-2, AC-3.

discovery spike 산출물(`registry_seed.SOURCE_SPECS`)의 *스키마·enum·완전성*을 검증한다.
실 회사 데이터 채움은 조사 후 1회(§6-2 TDD opt-out) — 본 테스트는 구조 불변식만 강제.
"""

from __future__ import annotations

from crawler.sources.registry_seed import (
    METHODS,
    SOURCE_SPECS,
    STATUSES,
    method_family,
)

# ---------------------------------------------------------------------------
# AC-1: Tier1~5 전 회사가 필수 필드로 기록 + Tier1 본사 전원 + Tier4/5 view_login 판정
# ---------------------------------------------------------------------------

_REQUIRED_STR_FIELDS = ("company", "careers_url", "method", "location_filter", "status")
# Tier1 본사(자체사이트 custom) — 전원 포함되어야 함
_TIER1_HQ = {"naver", "kakao", "line-plus", "woowahan"}


def test_AC_1_all_tiers_recorded_with_view_login() -> None:
    """AC-1: Tier1~5 모두 포함 + 각 spec 필수 필드 채워짐 + view_login 판정 기록."""
    tiers_present = {s.tier for s in SOURCE_SPECS}
    assert tiers_present == {1, 2, 3, 4, 5}, f"누락 tier: {tiers_present}"

    # Tier1 본사 전원 포함
    tier1_companies = {s.company for s in SOURCE_SPECS if s.tier == 1}
    assert _TIER1_HQ <= tier1_companies, (
        f"Tier1 본사 누락: {_TIER1_HQ - tier1_companies}"
    )

    # company 고유성(중복 등록 0)
    companies = [s.company for s in SOURCE_SPECS]
    assert len(companies) == len(set(companies)), "company 중복 존재"

    for s in SOURCE_SPECS:
        # 필수 문자열 필드 비어있지 않음
        for f in _REQUIRED_STR_FIELDS:
            assert getattr(s, f), f"{s.company}: {f} 비어있음"
        assert s.tier in {1, 2, 3, 4, 5}
        # view_login은 bool 판정으로 *반드시* 기록 (Tier4/5 핵심)
        assert isinstance(s.view_login, bool), f"{s.company}: view_login 미판정"

    # Tier4/5 view_login 판정 포함 확인(필드 존재 + bool)
    for s in SOURCE_SPECS:
        if s.tier in {4, 5}:
            assert isinstance(s.view_login, bool)


# ---------------------------------------------------------------------------
# AC-2: 모든 status가 enum + method가 ats(종류)/saas/custom으로 분류
# ---------------------------------------------------------------------------


def test_AC_2_status_and_method_enum_valid() -> None:
    """AC-2: status ∈ STATUSES, method ∈ METHODS, family ∈ {ats,saas,custom}."""
    for s in SOURCE_SPECS:
        assert s.status in STATUSES, f"{s.company}: 정의 외 status={s.status}"
        assert s.method in METHODS, f"{s.company}: 정의 외 method={s.method}"
        fam = method_family(s.method)
        assert fam in {"ats", "saas", "custom"}, f"{s.company}: family={fam}"
        # ATS/SaaS면 ats_slug 또는 careers_url로 식별 가능해야 함
        if fam in {"ats", "saas"}:
            assert s.ats_slug or s.careers_url, f"{s.company}: ATS/SaaS 식별자 없음"
    # login-required 소스는 view_login=True여야 정합
    for s in SOURCE_SPECS:
        if s.status == "login-required":
            assert s.view_login is True, (
                f"{s.company}: login-required인데 view_login=False"
            )


# ---------------------------------------------------------------------------
# AC-3: Tier2 외국계는 location_filter 기록 또는 status=no-korea-jobs
# ---------------------------------------------------------------------------


def test_AC_3_foreign_location_filter_or_status() -> None:
    """AC-3: 모든 Tier2 소스가 location_filter 비어있지 않거나 status=no-korea-jobs."""
    tier2 = [s for s in SOURCE_SPECS if s.tier == 2]
    assert tier2, "Tier2 소스가 없음"
    for s in tier2:
        has_filter = bool(s.location_filter)
        flagged = s.status == "no-korea-jobs"
        assert has_filter or flagged, (
            f"{s.company}: location_filter 없음 + no-korea-jobs 아님(조용한 누락)"
        )


def test_source_spec_is_frozen() -> None:
    """SourceSpec은 master data(불변) — frozen dataclass."""
    s = SOURCE_SPECS[0]
    try:
        s.company = "mutated"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("SourceSpec이 frozen이 아님(master data 불변 위반)")
