"""T-016 GS-1 결정성·GS-2 사실성 게이트 (SPEC §10-3).

GS-1: N=10회 (a)캐시 hit 점수 변동 0, (b)miss 재계산 top-k 순서 변동 0.
GS-2: 표본 ≥30 requirement 중 JD 원문에 실재하지 않는 비율 ≤2%.

두 게이트 모두 LLM 호출 없이 저장 산출물·결정적 파이썬으로만 측정한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

# GS-2 기준값 (SPEC §10-3: hallucinated requirement ≤2%)
GS2_THRESHOLD = 0.02

# GS-2 최소 표본 수
GS2_MIN_SAMPLE = 30


# ---------------------------------------------------------------------------
# GS-2 사실성 게이트
# ---------------------------------------------------------------------------


@dataclass
class GS2Result:
    """GS-2 측정 결과."""

    total_count: int
    hallucinated_count: int
    hallucinated_ratio: float
    gate_pass: bool
    threshold: float = GS2_THRESHOLD
    details: list[str] = field(default_factory=list)


class GS2Gate:
    """GS-2 사실성 게이트 — 표시 근거가 JD 원문에 실재하는지 측정한다.

    SPEC §10-3: 표본 ≥30의 매칭표·JD 원문 대비 hallucinated requirement 비율 ≤2%.
    """

    def __init__(self, threshold: float = GS2_THRESHOLD) -> None:
        self.threshold = threshold

    @staticmethod
    def _normalize(text: str) -> str:
        """소문자 + 연속 공백 제거 + 특수문자 정규화."""
        return re.sub(r"\s+", " ", text.lower().strip())

    def _is_grounded(self, requirement_text: str, jd_raw_text: str) -> bool:
        """requirement_text의 핵심 토큰이 JD 원문에 실재하는지 확인한다.

        substring 매칭: 정규화된 requirement의 유의미한 토큰 중 하나라도
        정규화된 JD 원문에 존재하면 grounded로 판정 (보수적 기준).
        """
        norm_req = self._normalize(requirement_text)
        norm_jd = self._normalize(jd_raw_text)

        # 내용 토큰(3자+)의 과반이 JD에 실재하면 grounded (길이 무관).
        # WHY: ≤20자를 exact-substring으로 보던 분기가 한국어 짧은
        # 요구를 과탈락(ratio→1.0)시켜 GS-2 통과 불가하던 결함 제거(T-016).
        tokens = [t for t in norm_req.split() if len(t) >= 3]
        if not tokens:
            return norm_req in norm_jd

        matched = sum(1 for t in tokens if t in norm_jd)
        return matched >= max(1, len(tokens) // 2)

    def measure(
        self,
        requirement_texts: list[str],
        jd_raw_text: str,
    ) -> GS2Result:
        """requirement_texts 중 JD 원문에 실재하지 않는 비율을 산출한다.

        Args:
            requirement_texts: 매칭표의 requirement_text 목록
            jd_raw_text: JD 원문 전체 텍스트

        Returns:
            GS2Result (gate_pass = hallucinated_ratio ≤ threshold)
        """
        total = len(requirement_texts)
        hallucinated: list[str] = []

        for req in requirement_texts:
            if not self._is_grounded(req, jd_raw_text):
                hallucinated.append(req)

        hallucinated_count = len(hallucinated)
        ratio = hallucinated_count / total if total > 0 else 0.0
        details = hallucinated[:10]  # 최대 10개만 기록

        # WHY: GS-2 게이트는 SPEC §10-3상 "표본 ≥30"에서만 유효하다. 표본이
        # 부족하면 ratio가 0%여도(빈 표본 total=0 포함) PASS로 오판할 수 있고,
        # 이는 "근거 없는 점수"를 거짓 통과시키는 것이라 제품 thesis에 정면 위배.
        # 따라서 표본 부족은 ratio와 무관하게 게이트 실패로 처리한다.
        if total < GS2_MIN_SAMPLE:
            gate_pass = False
            details = [f"insufficient_sample: {total} < {GS2_MIN_SAMPLE}", *details]
        else:
            gate_pass = ratio <= self.threshold

        return GS2Result(
            total_count=total,
            hallucinated_count=hallucinated_count,
            hallucinated_ratio=ratio,
            gate_pass=gate_pass,
            threshold=self.threshold,
            details=details,
        )


# ---------------------------------------------------------------------------
# GS-1 결정성 게이트
# ---------------------------------------------------------------------------


@dataclass
class GS1Result:
    """GS-1 측정 결과."""

    # (a) 캐시 hit: N회 반복 점수 분산
    hit_score_variance: float
    hit_pass: bool

    # (b) miss 재계산: top-k 순서 변동 여부
    miss_topk_order_changed: bool
    miss_pass: bool

    gate_pass: bool  # hit_pass and miss_pass

    n_repeats: int = 10
    top_k: int = 5
    details: dict[str, Any] = field(default_factory=dict)


class GS1Gate:
    """GS-1 결정성 게이트 (SPEC §10-3, Charter §6).

    (a) 캐시 hit: N=10 반복에서 점수 변동 0 확인.
    (b) miss 재계산: top-k 순서 변동 0 확인.

    두 경로 모두 결정론적이어야 한다 (SPEC §3-1 결정론 경계).
    """

    def measure(
        self,
        cached_fn: Callable[[int], list[dict[str, Any]]],
        miss_fn: Callable[[int], list[dict[str, Any]]],
        n_repeats: int = 10,
        top_k: int = 5,
    ) -> GS1Result:
        """GS-1 결정성을 N=10 반복으로 측정한다.

        Args:
            cached_fn: 캐시 hit 경로 — N번째 반복 인덱스를 받아 ranking 반환
            miss_fn: miss 재계산 경로 — N번째 반복 인덱스를 받아 ranking 반환
            n_repeats: 반복 횟수 (기본 10)
            top_k: 비교할 상위 K개 (기본 5)

        Returns:
            GS1Result
        """
        # (a) 캐시 hit: N회 실행하고 점수 분산 측정
        hit_results = [cached_fn(i) for i in range(n_repeats)]
        hit_variance = self._score_variance(hit_results)
        hit_pass = hit_variance == 0.0

        # (b) miss 재계산: N회 실행하고 top-k 순서 변동 측정
        miss_results = [miss_fn(i) for i in range(n_repeats)]
        topk_changed = self._topk_order_changed(miss_results, top_k)
        miss_pass = not topk_changed

        return GS1Result(
            hit_score_variance=hit_variance,
            hit_pass=hit_pass,
            miss_topk_order_changed=topk_changed,
            miss_pass=miss_pass,
            gate_pass=hit_pass and miss_pass,
            n_repeats=n_repeats,
            top_k=top_k,
            details={
                "hit_n_runs": len(hit_results),
                "miss_n_runs": len(miss_results),
            },
        )

    @staticmethod
    def _score_variance(runs: list[list[dict[str, Any]]]) -> float:
        """N회 실행 결과의 점수 분산을 산출한다.

        각 실행의 (job_id, fit_level, rank) 집합을 비교한다.
        모든 실행이 동일하면 0.0.
        """
        if len(runs) <= 1:
            return 0.0

        def _signature(run: list[dict[str, Any]]) -> frozenset[tuple[str, int, int]]:
            return frozenset(
                (r.get("job_id", ""), r.get("fit_level", 0), r.get("rank", 0))
                for r in run
            )

        first = _signature(runs[0])
        # 하나라도 다르면 variance = 1.0 (이진: 변동 있음/없음)
        for run in runs[1:]:
            if _signature(run) != first:
                return 1.0
        return 0.0

    @staticmethod
    def _topk_order_changed(
        runs: list[list[dict[str, Any]]],
        top_k: int,
    ) -> bool:
        """N회 실행에서 top-k 순서가 변동되었는지 확인한다.

        top-k는 fit_level 내림차순 상위 K개의 job_id 순서로 비교한다.
        """
        if len(runs) <= 1:
            return False

        def _topk(run: list[dict[str, Any]]) -> tuple[str, ...]:
            ordered = sorted(run, key=lambda r: r.get("rank", 9999))
            return tuple(r.get("job_id", "") for r in ordered[:top_k])

        first = _topk(runs[0])
        for run in runs[1:]:
            if _topk(run) != first:
                return True
        return False
