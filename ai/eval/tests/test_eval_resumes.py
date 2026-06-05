"""T-015 멀티-페르소나 진단 테스트 — AC-1·AC-2·AC-3 (SPEC §10-2)."""

from __future__ import annotations

from eval.eval_resumes import (
    PERSONAS,
    RankingModeComparison,
    compare_ranking_modes,
    diagnose,
    load_persona,
)

# ---------------------------------------------------------------------------
# AC-1: backend_platform 페르소나 도메인 주입 → domain_alignment strong + 3 불변식 통과
# ---------------------------------------------------------------------------


def test_AC_1_persona_domain_injection() -> None:
    """AC-1: backend_platform 페르소나에 도메인 주입 후 진단 → domain_alignment strong,
    mismatch_priority·fit_scale·extractive 불변식 통과.
    """
    persona = load_persona("backend_platform")
    # backend 역할이 primary_domains에 있으므로 domain_alignment = strong
    assert "backend" in persona.primary_domains

    result = diagnose(persona)

    # domain_alignment가 backend 역할에 strong으로 산출됨
    assert result.domain_alignment == "strong", (
        f"backend_platform의 domain_alignment가 strong이어야 함: {result.domain_alignment}"
    )

    # 3 불변식(fail 수준)이 통과해야 함
    inv_map = {e.name: e for e in result.invariants}
    assert inv_map["mismatch_priority"].severity != "fail", (
        f"mismatch_priority 불변식 실패: {inv_map['mismatch_priority']}"
    )
    assert inv_map["fit_scale"].severity != "fail", (
        f"fit_scale 불변식 실패: {inv_map['fit_scale']}"
    )
    assert inv_map["extractive"].severity != "fail", (
        f"extractive 불변식 실패: {inv_map['extractive']}"
    )


# ---------------------------------------------------------------------------
# AC-2: 4 페르소나 모두 → 6 불변식 결과(severity: fail/warning/na)가 리포트됨
# ---------------------------------------------------------------------------


def test_AC_2_six_directional_invariants() -> None:
    """AC-2: 4 페르소나 각각에서 diagnose → 6 불변식 결과가 리포트되고,
    fail=0이면 pass.
    """
    expected_invariant_names = {
        "extractive",
        "fit_scale",
        "mismatch_priority",
        "expected_top_in_top3",
        "domain_order",
        "primary_domain_available",
    }
    expected_personas = {
        "backend_platform",
        "junior_frontend",
        "ai_ml_application",
        "devops_infra_security",
    }
    assert set(PERSONAS.keys()) == expected_personas, (
        f"4 페르소나가 정의돼야 함: {set(PERSONAS.keys())}"
    )

    for persona_name in PERSONAS:
        persona = load_persona(persona_name)
        result = diagnose(persona)

        inv_names = {e.name for e in result.invariants}
        assert expected_invariant_names == inv_names, (
            f"페르소나 {persona_name}: 6 불변식이어야 함, 실제={inv_names}"
        )

        # severity는 반드시 fail/warning/na 중 하나
        for entry in result.invariants:
            assert entry.severity in ("fail", "warning", "na", "pass"), (
                f"페르소나 {persona_name} 불변식 {entry.name}: "
                f"severity={entry.severity!r}가 유효하지 않음"
            )

        # fail=0이면 pass
        fail_count = sum(1 for e in result.invariants if e.severity == "fail")
        assert result.passed == (fail_count == 0), (
            f"페르소나 {persona_name}: fail={fail_count}, passed={result.passed} 불일치"
        )


# ---------------------------------------------------------------------------
# AC-3: --compare-ranking-modes → ranking_mode_comparison 산출
# ---------------------------------------------------------------------------


def test_AC_3_mode_comparison() -> None:
    """AC-3: compare_ranking_modes → ranking_mode_comparison에
    fit_rank_inversions·tier_inversions·mismatch_violation(=0이어야 함) 기록.
    """
    persona = load_persona("backend_platform")
    comparison = compare_ranking_modes(persona)

    assert isinstance(comparison, RankingModeComparison)

    # 3 모드가 모두 포함돼야 함
    assert len(comparison.modes) == 3, f"3 모드가 있어야 함: {comparison.modes}"
    assert set(comparison.modes) == {"bt_primary", "fit_primary", "domain_fit_bt"}

    # fit_rank_inversions, tier_inversions, mismatch_violation 필드 존재
    assert hasattr(comparison, "fit_rank_inversions")
    assert hasattr(comparison, "tier_inversions")
    assert hasattr(comparison, "mismatch_violation")

    # mismatch_violation은 0이어야 함 (SPEC §10-2: mismatch_violation=0이어야 함)
    assert comparison.mismatch_violation == 0, (
        f"mismatch_violation이 0이어야 함: {comparison.mismatch_violation}"
    )
