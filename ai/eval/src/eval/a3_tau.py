"""T-017 A-3 τ 프록시 측정 (Charter §9 A-3 / SPEC §10-3 GS-3).

개발 JD 8~10개에 대한 창업자 수기 상대 랭킹 vs 모델 랭킹의
Kendall τ + 자명 페어 위반율을 산출하고 판정 라벨을 리포트로 남긴다.

판정 기준 (Charter §9):
  τ ≥ 0.7                       → PROCEED
  0.6 ≤ τ < 0.7                 → CONDITIONAL (재실험 권장)
  τ < 0.6 또는 violation_rate > 5% → NOGO (F5 제품화 범위 재검토)

LLM 호출 없음. 저장 산출물(모델 랭킹) + 수기 라벨만 사용.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 판정 상수 (Charter §9 A-3)
# ---------------------------------------------------------------------------

VERDICT_PROCEED = "PROCEED"
VERDICT_CONDITIONAL = "CONDITIONAL"
VERDICT_NOGO = "NOGO"

# 자명 페어 위반율 No-go 임계값 (Charter §9)
OBVIOUS_VIOLATION_NOGO_THRESHOLD = 0.05

# Kendall τ 판정 임계값
TAU_PROCEED = 0.7
TAU_CONDITIONAL = 0.6


# ---------------------------------------------------------------------------
# 데이터 구조
# ---------------------------------------------------------------------------


@dataclass
class TauReport:
    """A-3 τ 측정 결과 리포트."""

    tau: float
    n_pairs: int
    n_concordant: int
    n_discordant: int
    violation_rate: float  # 자명 페어 위반율 (인접 쌍 기준)
    n_obvious_pairs: int
    n_obvious_violations: int
    verdict: str  # PROCEED / CONDITIONAL / NOGO


# ---------------------------------------------------------------------------
# 핵심 계산 함수
# ---------------------------------------------------------------------------


def compute_tau(
    human_order: list[str],
    model_ranking: dict[str, int],
) -> tuple[float, int, int]:
    """Kendall τ를 계산한다.

    Args:
        human_order: 수기 선호도 순서 (인덱스 0 = 가장 선호)
        model_ranking: job_id → rank (1 = 최상위)

    Returns:
        (tau, n_concordant, n_discordant)
        모델 랭킹에 없는 JD는 graceful skip.

    WHY: scipy 불필요 — 단순 concordant/discordant 쌍 계산으로
         외부 의존성 없이 순수 파이썬 구현 (SPEC §3-1 결정론 경계).
    """
    # 모델 랭킹에 존재하는 JD만 필터링
    valid = [jid for jid in human_order if jid in model_ranking]

    n = len(valid)
    if n < 2:
        return 0.0, 0, 0

    concordant = 0
    discordant = 0

    for i in range(n):
        for j in range(i + 1, n):
            # 수기 순서: valid[i]가 valid[j]보다 선호됨 (i < j)
            # 모델 순서: rank가 낮을수록 상위
            model_i = model_ranking[valid[i]]
            model_j = model_ranking[valid[j]]

            if model_i < model_j:
                # 모델도 i > j 순서 → concordant
                concordant += 1
            elif model_i > model_j:
                # 모델이 역전 → discordant
                discordant += 1
            # tie는 무시 (Kendall τ-b의 tie 처리 단순화)

    total = concordant + discordant
    tau = (concordant - discordant) / total if total > 0 else 0.0
    return tau, concordant, discordant


def compute_obvious_violation_rate(
    human_order: list[str],
    model_ranking: dict[str, int],
) -> float:
    """인접 쌍 기준 자명 페어 위반율을 산출한다.

    자명 페어: 수기 랭킹에서 인접한 쌍 (rank k, rank k+1).
    위반: 모델이 이 인접 쌍의 순서를 역전한 경우.

    모델 랭킹에 없는 JD가 포함된 쌍은 건너뜀.
    """
    valid = [jid for jid in human_order if jid in model_ranking]
    if len(valid) < 2:
        return 0.0

    total_obvious = len(valid) - 1
    violations = 0

    for i in range(len(valid) - 1):
        a = valid[i]
        b = valid[i + 1]
        # 수기: a > b. 모델이 b를 a보다 위에 두면 위반
        if model_ranking[b] < model_ranking[a]:
            violations += 1

    return violations / total_obvious if total_obvious > 0 else 0.0


def _determine_verdict(tau: float, violation_rate: float) -> str:
    """Charter §9 A-3 판정 기준으로 verdict를 결정한다."""
    # 자명 페어 위반율 >5% → NOGO (τ와 무관)
    if violation_rate > OBVIOUS_VIOLATION_NOGO_THRESHOLD:
        return VERDICT_NOGO
    if tau >= TAU_PROCEED:
        return VERDICT_PROCEED
    if tau >= TAU_CONDITIONAL:
        return VERDICT_CONDITIONAL
    return VERDICT_NOGO


def run_a3(
    human_order: list[str],
    model_ranking: dict[str, int],
) -> TauReport:
    """A-3 τ 프록시를 1회 실행하고 TauReport를 반환한다.

    Args:
        human_order: 수기 선호도 순서 (인덱스 0 = 가장 선호)
        model_ranking: job_id → rank (1 = 최상위)

    Returns:
        TauReport (판정 라벨 포함)
    """
    tau, n_concordant, n_discordant = compute_tau(human_order, model_ranking)
    violation_rate = compute_obvious_violation_rate(human_order, model_ranking)

    valid = [jid for jid in human_order if jid in model_ranking]
    n = len(valid)
    n_pairs = n * (n - 1) // 2
    n_obvious_pairs = max(0, n - 1)
    n_obvious_violations = round(violation_rate * n_obvious_pairs)

    verdict = _determine_verdict(tau, violation_rate)

    return TauReport(
        tau=tau,
        n_pairs=n_pairs,
        n_concordant=n_concordant,
        n_discordant=n_discordant,
        violation_rate=violation_rate,
        n_obvious_pairs=n_obvious_pairs,
        n_obvious_violations=n_obvious_violations,
        verdict=verdict,
    )
