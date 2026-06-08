"""eval/cost_regression.py — F-021 N→K 비용 회귀 측정 (T-069).

measure_cost(): 동일 이력서·JD 집합을 N 전체 vs K 후보 경로로 각각 스코어링하며 LLM
토큰·호출 수를 계측해 절감(ratio<1.0)을 실증한다. 계측은 scoring_fn에 주입한 counter
콜백으로만 — 파이프라인 본체 변경 없음(ADR-108 D4). LLM 실호출은 mock(결정적).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# scoring_fn 시그니처: (jobs, counter) → results. counter에 tokens·calls 축적.
ScoringFn = Callable[[list[dict[str, Any]], dict[str, int]], list[dict[str, Any]]]


@dataclass
class CostReport:
    """N 전체 vs K 후보 경로 LLM 비용 비교(직렬화 → m5_cost_and_a3.json)."""

    n_tokens: int
    k_tokens: int
    n_calls: int
    k_calls: int
    ratio: float  # k_tokens / n_tokens (<1.0 = 절감)
    k_results: list[dict[str, Any]] = field(default_factory=list)


def measure_cost(
    scoring_fn: ScoringFn,
    resumes: list[dict[str, Any]],
    jd_sets_n: list[dict[str, Any]],
    jd_sets_k: list[dict[str, Any]],
) -> CostReport:
    """N 전체(jd_sets_n) vs K 후보(jd_sets_k) 비용을 계측한다.

    각 경로를 resume마다 scoring_fn으로 실행하며 counter에 tokens·calls를 누적한다.
    K 경로 결과(k_results)는 출력 계약 불변 확인(AC-2)에 사용한다.
    """
    counter_n: dict[str, int] = {"tokens": 0, "calls": 0}
    counter_k: dict[str, int] = {"tokens": 0, "calls": 0}

    for _resume in resumes:
        scoring_fn(jd_sets_n, counter_n)

    k_results: list[dict[str, Any]] = []
    for _resume in resumes:
        k_results = scoring_fn(jd_sets_k, counter_k)

    n_tokens = counter_n["tokens"]
    k_tokens = counter_k["tokens"]
    ratio = (k_tokens / n_tokens) if n_tokens else 0.0

    return CostReport(
        n_tokens=n_tokens,
        k_tokens=k_tokens,
        n_calls=counter_n["calls"],
        k_calls=counter_k["calls"],
        ratio=ratio,
        k_results=k_results,
    )
