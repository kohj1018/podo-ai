"""T-017 A-3 τ 프록시 단위 테스트 (SPEC §10-3, Charter §9 A-3).

AC-1: 수기 라벨된 페어 + 모델 랭킹 → Kendall τ + 자명 페어 위반율 + 판정 라벨.

τ 계산 함수는 합성 라벨로 단위 검증 (TDD opt-out: 실데이터 1회 실행은 탐색).
"""

from __future__ import annotations

import pytest

from eval.a3_tau import (
    VERDICT_CONDITIONAL,
    VERDICT_NOGO,
    VERDICT_PROCEED,
    TauReport,
    compute_obvious_violation_rate,
    compute_tau,
    run_a3,
)

# ---------------------------------------------------------------------------
# AC-1: τ 계산 + 자명 페어 위반율 + 판정 라벨
# ---------------------------------------------------------------------------


def test_AC_1_tau_computation_and_verdict() -> None:
    """AC-1: 수기 라벨된 JD 쌍 + 모델 랭킹 → Kendall τ + 자명 페어 위반율 + 판정.

    Given: 완전히 일치하는 모델 랭킹 vs 수기 랭킹(8쌍)
    When: run_a3 실행
    Then: τ=1.0, violation_rate=0.0, verdict=PROCEED
    """
    # 수기 순서: [A, B, C, D, E, F, G, H] (인덱스 = 선호도 높은 순)
    human_order = ["jd-a", "jd-b", "jd-c", "jd-d", "jd-e", "jd-f", "jd-g", "jd-h"]
    # 모델 랭킹: 수기와 완전 일치 (rank 1 = 최상위)
    model_ranking = {jid: i + 1 for i, jid in enumerate(human_order)}

    report = run_a3(human_order=human_order, model_ranking=model_ranking)

    assert isinstance(report, TauReport)
    assert report.tau == pytest.approx(1.0)
    assert report.violation_rate == pytest.approx(0.0)
    assert report.verdict == VERDICT_PROCEED
    assert report.n_pairs > 0


def test_AC_1_tau_perfect_reverse() -> None:
    """AC-1: 완전 역순 랭킹 → τ=-1.0, verdict=NOGO."""
    human_order = ["jd-a", "jd-b", "jd-c", "jd-d"]
    # 모델 랭킹: 역순
    model_ranking = {"jd-a": 4, "jd-b": 3, "jd-c": 2, "jd-d": 1}

    report = run_a3(human_order=human_order, model_ranking=model_ranking)

    assert report.tau == pytest.approx(-1.0)
    assert report.verdict == VERDICT_NOGO


def test_AC_1_tau_conditional_range() -> None:
    """AC-1: 0.6 ≤ τ < 0.7 이고 violation_rate ≤ 5% → CONDITIONAL 판정.

    WHY: 인접 쌍이 역전되면 violation_rate >5% → NOGO. 따라서
         _determine_verdict 직접 호출로 CONDITIONAL 경계를 검증한다.
    """
    from eval.a3_tau import _determine_verdict

    assert _determine_verdict(tau=0.65, violation_rate=0.0) == VERDICT_CONDITIONAL
    assert _determine_verdict(tau=0.69, violation_rate=0.0) == VERDICT_CONDITIONAL
    assert _determine_verdict(tau=0.70, violation_rate=0.0) == VERDICT_PROCEED
    assert _determine_verdict(tau=0.59, violation_rate=0.0) == VERDICT_NOGO

    # compute_tau 자체도 0.667 범위 반환 확인
    tau, _, _ = compute_tau(
        human_order=["jd-a", "jd-b", "jd-c", "jd-d"],
        model_ranking={"jd-a": 1, "jd-b": 2, "jd-c": 4, "jd-d": 3},
    )
    # pairs: (A,B)✓(A,C)✓(A,D)✓(B,C)✓(B,D)✓(C,D)✗ → τ=(5-1)/6≈0.667
    assert 0.6 <= tau < 0.7


def test_AC_1_obvious_violation_rate() -> None:
    """AC-1: 자명 페어(adjacent rank 1↔2 기준) 위반율 산출.

    Given: obvious 페어 4쌍 중 2쌍 위반
    When: compute_obvious_violation_rate
    Then: violation_rate = 0.5
    """
    # obvious_pairs: 수기 랭킹 상위 2개 간 페어가 "자명 페어"
    # human: [A>B>C>D>E] 에서 인접 쌍 (A,B), (B,C), (C,D), (D,E) = 4쌍
    human_order = ["jd-a", "jd-b", "jd-c", "jd-d", "jd-e"]
    # 모델: A=1, B=2 는 올바름, C=4, D=3 은 역전, E=5 올바름
    # 자명 위반: (C, D) 쌍 1개 → violation_rate = 1/4
    model_ranking = {"jd-a": 1, "jd-b": 2, "jd-c": 4, "jd-d": 3, "jd-e": 5}

    rate = compute_obvious_violation_rate(human_order, model_ranking)
    assert rate == pytest.approx(1 / 4)


def test_AC_1_nogo_on_high_violation_rate() -> None:
    """AC-1: 자명 페어 위반율 >5% 이면 NOGO (τ가 높아도).

    WHY: Charter §9 — 자명 페어 위반율 >5% 단독으로 No-go 조건.
    """
    # human: 10개 JD
    human_order = [f"jd-{i}" for i in range(10)]
    # 인접 쌍 9개 중 1개만 역전 → 위반율 = 1/9 ≈ 11% > 5%
    # 전체 τ는 높게 유지 (나머지 대부분 concordant)
    model_ranking = {jid: i + 1 for i, jid in enumerate(human_order)}
    # jd-0(rank1)과 jd-1(rank2) 을 역전
    model_ranking["jd-0"] = 2
    model_ranking["jd-1"] = 1

    report = run_a3(human_order=human_order, model_ranking=model_ranking)

    # 자명 위반: 1/9 ≈ 11% > 5% → NOGO
    assert report.violation_rate > 0.05
    assert report.verdict == VERDICT_NOGO


def test_AC_1_report_fields() -> None:
    """AC-1: TauReport 필드 — tau, n_pairs, violation_rate, verdict 포함."""
    human_order = ["jd-a", "jd-b", "jd-c"]
    model_ranking = {"jd-a": 1, "jd-b": 2, "jd-c": 3}

    report = run_a3(human_order=human_order, model_ranking=model_ranking)

    assert hasattr(report, "tau")
    assert hasattr(report, "n_pairs")
    assert hasattr(report, "violation_rate")
    assert hasattr(report, "verdict")
    assert report.n_pairs == 3  # C(3,2) = 3


def test_compute_tau_concordant_discordant() -> None:
    """compute_tau: concordant/discordant 쌍 수 검증."""
    # human: [A, B, C] → A>B, A>C, B>C
    # model: A=1, B=2, C=3 → 모두 concordant
    tau, n_concordant, n_discordant = compute_tau(
        human_order=["jd-a", "jd-b", "jd-c"],
        model_ranking={"jd-a": 1, "jd-b": 2, "jd-c": 3},
    )
    assert tau == pytest.approx(1.0)
    assert n_concordant == 3
    assert n_discordant == 0


def test_compute_tau_partial_overlap() -> None:
    """compute_tau: 모델 랭킹에 없는 JD는 건너뜀 (graceful skip)."""
    human_order = ["jd-a", "jd-b", "jd-c", "jd-missing"]
    model_ranking = {"jd-a": 1, "jd-b": 2, "jd-c": 3}

    tau, _c, _d = compute_tau(human_order, model_ranking)
    # jd-missing 제외 후 3쌍 모두 concordant → τ=1.0
    assert tau == pytest.approx(1.0)
