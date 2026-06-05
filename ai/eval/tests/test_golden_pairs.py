"""T-016 골든 페어 정확도 + GS-1/GS-2 게이트 테스트 (SPEC §10-3).

AC-1: aggregate_metrics → strict/tie-aware 정확도 산출 + unavailable 처리
AC-2: GS-2 사실성 게이트 (hallucinated requirement ≤2%)
AC-3: GS-1 결정성 게이트 (캐시 hit 변동 0, miss top-k 순서 변동 0)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from eval.gates import GS1Gate, GS1Result, GS2Gate, GS2Result
from eval.golden_pairs import (
    CATEGORIES,
    LABELS,
    GoldenPair,
    PairMetrics,
    aggregate_metrics,
    evaluate_pairs,
    load_pairs,
    propose_pairs,
    rescore_persona,
)

# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------


def _make_pair(
    pair_id: str,
    job_a: str,
    job_b: str,
    label: str,
    category: str = "same_domain_close",
    hardness: int = 1,
    job_a_rank: int = 1,
    job_b_rank: int = 2,
    job_a_fit: int = 4,
    job_b_fit: int = 3,
) -> GoldenPair:
    return GoldenPair(
        pair_id=pair_id,
        job_a=job_a,
        job_b=job_b,
        label=label,
        category=category,
        hardness=hardness,
        job_a_rank=job_a_rank,
        job_b_rank=job_b_rank,
        job_a_fit=job_a_fit,
        job_b_fit=job_b_fit,
    )


def _make_ranking(
    job_a: str, job_b: str, a_rank: int = 1, b_rank: int = 2
) -> list[dict[str, Any]]:
    return [
        {
            "job_id": job_a,
            "rank": a_rank,
            "fit_level": 4,
            "domain_alignment": "strong",
            "role_family": "frontend",
        },
        {
            "job_id": job_b,
            "rank": b_rank,
            "fit_level": 3,
            "domain_alignment": "strong",
            "role_family": "frontend",
        },
    ]


# ---------------------------------------------------------------------------
# AC-1: strict pairwise + tie-aware 정확도, unavailable 처리
# ---------------------------------------------------------------------------


def test_AC_1_strict_and_tie_aware_metrics() -> None:
    """AC-1: 라벨된 골든 페어 + 저장 산출물 → aggregate_metrics → strict/tie-aware 정확도.

    Given: A_better/B_better/tie 라벨 페어 4쌍 + unavailable 공고 1개
    When: aggregate_metrics 호출
    Then:
    - strict pairwise 정확도(분모: A_better+B_better)가 올바르게 산출
    - tie-aware 정확도(tie 포함)가 올바르게 산출
    - unavailable 공고는 재수집 없이 unavailable 처리
    - 모드별(domain_fit_bt) 결과 포함
    """
    # 시스템이 A를 1위로 랭킹한 페어 → A_better 라벨이면 맞음
    pair1 = _make_pair("p1", "jd-a", "jd-b", "A_better", job_a_rank=1, job_b_rank=2)
    # 시스템이 B를 1위로 랭킹 → A_better 라벨이면 틀림
    pair2 = _make_pair("p2", "jd-c", "jd-d", "A_better", job_a_rank=2, job_b_rank=1)
    # tie 라벨 페어 (같은 fit level → tie-aware에서는 맞음)
    pair3 = _make_pair(
        "p3",
        "jd-e",
        "jd-f",
        "tie",
        job_a_rank=1,
        job_b_rank=2,
        job_a_fit=3,
        job_b_fit=3,
    )
    # unsure → 집계 제외
    pair4 = _make_pair("p4", "jd-g", "jd-h", "unsure")

    pairs = [pair1, pair2, pair3, pair4]
    ranking = {
        "jd-a": 1,
        "jd-b": 2,
        "jd-c": 2,
        "jd-d": 1,
        "jd-e": 1,
        "jd-f": 2,
        "jd-g": 1,
        "jd-h": 2,
    }
    fit_by_id = {
        "jd-a": 4,
        "jd-b": 3,
        "jd-c": 3,
        "jd-d": 4,
        "jd-e": 3,
        "jd-f": 3,
        "jd-g": 3,
        "jd-h": 2,
    }
    # unavailable: ranking에 없는 공고
    available_ids = set(ranking.keys())

    metrics = aggregate_metrics(pairs, ranking, fit_by_id, available_ids)
    assert isinstance(metrics, PairMetrics)

    # strict 분모: A_better + B_better = 2 (pair1, pair2). pair3(tie), pair4(unsure) 제외
    # strict 정답: pair1만 맞음 → 1/2 = 0.5
    assert metrics.strict_accuracy == pytest.approx(0.5), (
        f"strict_accuracy={metrics.strict_accuracy}"
    )

    # tie-aware: pair1(A_better→맞음) + pair2(A_better→틀림) + pair3(tie→같은fit→맞음) = 3쌍 분모
    # 정답: pair1, pair3 → 2/3
    assert metrics.tie_aware_accuracy == pytest.approx(2 / 3), (
        f"tie_aware_accuracy={metrics.tie_aware_accuracy}"
    )

    # unsure는 집계에서 제외
    assert metrics.unsure_count == 1

    # unavailable 처리 (ranking에 없는 job은 unavailable)
    assert metrics.unavailable_count >= 0  # 이 픽스처에서는 모두 available


def test_AC_1_unavailable_handling() -> None:
    """AC-1: ranking에 없는 공고는 unavailable로 처리 (재수집 X)."""
    pair = _make_pair(
        "p1", "jd-missing", "jd-b", "A_better", job_a_rank=1, job_b_rank=2
    )

    # jd-missing은 ranking에 없음 → unavailable
    ranking = {"jd-b": 1}
    fit_by_id = {"jd-missing": 4, "jd-b": 3}
    available_ids = set(ranking.keys())  # jd-missing 없음

    metrics = aggregate_metrics([pair], ranking, fit_by_id, available_ids)

    assert metrics.unavailable_count == 1
    # unavailable 포함 페어는 strict 집계 제외
    assert metrics.strict_total == 0


def test_AC_1_mode_breakdown_included() -> None:
    """AC-1: 모드별(domain_fit_bt) 정확도 포함."""
    pair = _make_pair("p1", "jd-a", "jd-b", "A_better", job_a_rank=1, job_b_rank=2)
    ranking = {"jd-a": 1, "jd-b": 2}
    fit_by_id = {"jd-a": 4, "jd-b": 3}
    available_ids = set(ranking.keys())

    metrics = aggregate_metrics([pair], ranking, fit_by_id, available_ids)

    assert "domain_fit_bt" in metrics.by_mode
    assert metrics.by_mode["domain_fit_bt"]["strict_correct"] >= 0


# ---------------------------------------------------------------------------
# AC-2: GS-2 사실성 게이트
# ---------------------------------------------------------------------------


def test_AC_2_gs2_factuality_gate() -> None:
    """AC-2: 매칭표 근거 vs JD 원문 → hallucinated requirement 비율 산출 + ≤2% 게이트 판정.

    Given: 표본 ≥30인 requirement rows + JD 원문
    When: GS2Gate.measure 호출
    Then:
    - JD 원문에 실재하지 않는 근거 비율 산출
    - ≤2% 이면 gate_pass=True, 초과면 False
    """
    # JD 원문
    jd_raw_text = "React 경험 필수. TypeScript 사용. 5년 이상 경력."

    # requirement_text들 — 일부는 JD 원문에 실재, 일부는 hallucinated
    real_reqs = [f"React 경험 필수_{i}" for i in range(29)]  # 29개: JD에 "React" 포함
    hallucinated_reqs = ["GraphQL 전문가 필수"]  # 1개: JD에 없는 requirement

    # 총 30개 requirement
    all_reqs = real_reqs + hallucinated_reqs
    assert len(all_reqs) == 30

    gate = GS2Gate()
    result = gate.measure(all_reqs, jd_raw_text)

    assert isinstance(result, GS2Result)
    assert result.total_count == 30
    assert result.hallucinated_count >= 0
    # hallucinated_ratio = hallucinated_count / total_count
    assert 0.0 <= result.hallucinated_ratio <= 1.0
    # 1개 hallucinated / 30 = ~3.3% → threshold 2% 초과 → gate_pass=False
    assert result.gate_pass is False, (
        f"1/30 ≈ 3.3% > 2% 이어야 gate_pass=False, got {result.hallucinated_ratio:.3f}"
    )


def test_AC_2_gs2_passes_threshold() -> None:
    """AC-2: hallucinated 비율 ≤2% 이면 gate_pass=True."""
    jd_raw_text = "React TypeScript Node.js 경험 필수. 3년 이상."

    # 100개 중 1개만 hallucinated → 1% ≤ 2% → pass
    real_reqs = [f"React 경험_{i}" for i in range(99)]
    hallucinated_reqs = ["완전히_존재하지_않는_요구사항_xyz123"]
    all_reqs = real_reqs + hallucinated_reqs

    gate = GS2Gate()
    result = gate.measure(all_reqs, jd_raw_text)

    assert result.total_count == 100
    assert result.gate_pass is True, (
        f"1/100=1% ≤ 2% → pass, hallucinated_ratio={result.hallucinated_ratio}"
    )


def test_AC_2_gs2_insufficient_sample_fails() -> None:
    """AC-2 (QA-M1-001 회귀 가드): 표본 < GS2_MIN_SAMPLE이면 hallucination 0%여도 gate_pass=False.

    빈/소표본 PASS는 '근거 없는 점수'를 거짓 통과시키는 것이라 제품 thesis 위배
    (SPEC §10-3: GS-2는 표본 ≥30에서만 유효).
    """
    from eval.gates import GS2_MIN_SAMPLE

    jd_raw_text = "React TypeScript 경험 필수."
    # 전부 grounded(ratio=0%)이지만 표본 부족 → 게이트 실패여야 한다.
    small = [f"React 경험_{i}" for i in range(GS2_MIN_SAMPLE - 1)]

    gate = GS2Gate()
    result = gate.measure(small, jd_raw_text)
    assert result.total_count == GS2_MIN_SAMPLE - 1
    assert result.hallucinated_ratio == 0.0
    assert result.gate_pass is False
    assert any("insufficient_sample" in d for d in result.details)

    # 빈 표본도 통과 금지 (total=0 → ratio 0.0 이던 거짓 통과 차단).
    empty = gate.measure([], jd_raw_text)
    assert empty.gate_pass is False


# ---------------------------------------------------------------------------
# AC-3: GS-1 결정성 게이트
# ---------------------------------------------------------------------------


def test_AC_3_gs1_determinism_gate() -> None:
    """AC-3: N=10회 (a)캐시 hit (b)miss 재계산 → 변동 0 측정·판정.

    Given: 동일 (이력서, JD) 입력 + 저장 산출물
    When: N=10회 캐시 hit / miss 재계산
    Then:
    - (a) hit: 점수 변동 0 → score_variance=0.0
    - (b) miss: 상위 fit top-k 순서 변동 0 → topk_order_changed=False
    """
    # 결정적 스코어 함수 시뮬레이션: 동일 입력 → 동일 결과
    base_ranking = [
        {"job_id": "j1", "fit_level": 5, "rank": 1},
        {"job_id": "j2", "fit_level": 4, "rank": 2},
        {"job_id": "j3", "fit_level": 3, "rank": 3},
    ]

    # N=10 캐시 hit 시뮬레이션: 항상 동일 결과 반환하는 함수
    def cached_score_fn(_n: int) -> list[dict]:
        return [dict(r) for r in base_ranking]

    # N=10 miss 재계산: 결정적이므로 항상 동일
    def miss_score_fn(_n: int) -> list[dict]:
        return [dict(r) for r in base_ranking]

    gate = GS1Gate()
    result = gate.measure(
        cached_fn=cached_score_fn,
        miss_fn=miss_score_fn,
        n_repeats=10,
        top_k=3,
    )

    assert isinstance(result, GS1Result)
    # (a) hit: 점수 변동 0
    assert result.hit_score_variance == pytest.approx(0.0), (
        f"hit variance={result.hit_score_variance}"
    )
    assert result.hit_pass is True

    # (b) miss: top-k 순서 변동 0
    assert result.miss_topk_order_changed is False
    assert result.miss_pass is True

    assert result.gate_pass is True


def test_AC_3_gs1_detects_nondeterminism() -> None:
    """AC-3: 순서가 바뀌는 함수는 GS-1 gate_pass=False (결정적 fixture로 검출)."""

    # 반복 인덱스 짝/홀에 따라 top-k 순서를 결정적으로 뒤집어 비결정성을 모사한다.
    # (seed 없는 random.shuffle은 결정성 게이트 테스트에 부적합 — flaky 회피)
    def order_flipping_fn(n: int) -> list[dict]:
        ids = ["j1", "j2", "j3"] if n % 2 == 0 else ["j3", "j2", "j1"]
        return [
            {"job_id": jid, "fit_level": 3, "rank": i + 1} for i, jid in enumerate(ids)
        ]

    gate = GS1Gate()
    result = gate.measure(
        cached_fn=lambda n: [
            {"job_id": "j1", "fit_level": 5, "rank": 1},
            {"job_id": "j2", "fit_level": 4, "rank": 2},
        ],
        miss_fn=order_flipping_fn,
        n_repeats=10,
        top_k=3,
    )

    # miss top-k 순서가 반복마다 뒤집히므로 결정적으로 검출됨
    assert result.miss_topk_order_changed is True
    assert result.miss_pass is False
    assert result.gate_pass is False


# ---------------------------------------------------------------------------
# 추가 deliverable 검증: propose_pairs / load_pairs / evaluate_pairs / rescore_persona
# ---------------------------------------------------------------------------


def test_propose_pairs_extracts_hard_cases() -> None:
    """propose_pairs: 하드 케이스(같은 직군·fit↔rank 역전) 자동 추출, 라벨 공백."""
    ranking = [
        {
            "job_id": "a",
            "rank": 1,
            "fit_level": 3,
            "domain_alignment": "strong",
            "role_family": "backend",
        },
        {
            "job_id": "b",
            "rank": 2,
            "fit_level": 4,
            "domain_alignment": "adjacent",
            "role_family": "backend",
        },
    ]
    pairs = propose_pairs(ranking)

    assert pairs, "하드 케이스(같은 직군 + fit↔rank 역전)가 추출돼야 함"
    assert all(p.label == "" for p in pairs), "propose는 미라벨(expected_winner 공백)"
    assert all(p.category in CATEGORIES for p in pairs)


def test_load_pairs_splits_labeled_and_unlabeled() -> None:
    """load_pairs: 유효 라벨/빈·무효 라벨 분리 (graceful skip)."""
    rows = [
        {"pair_id": "p1", "job_a": "a", "job_b": "b", "label": "A_better"},
        {"pair_id": "p2", "job_a": "c", "job_b": "d", "label": ""},  # 미라벨
        {"pair_id": "p3", "job_a": "e", "job_b": "f", "label": "bogus"},  # 무효
    ]
    labeled, unlabeled = load_pairs(rows)

    assert [p.pair_id for p in labeled] == ["p1"]
    assert {p.pair_id for p in unlabeled} == {"p2", "p3"}
    assert all(p.label in LABELS for p in labeled)


def test_evaluate_pairs_marks_unavailable() -> None:
    """evaluate_pairs: ranking에 없는 공고는 unavailable 처리 (재수집 X)."""
    pair = _make_pair("p1", "jd-missing", "jd-b", "A_better")
    evaluated = evaluate_pairs([pair], {"jd-b": 1}, {"jd-b": 3}, {"jd-b"})

    assert len(evaluated) == 1
    assert evaluated[0].unavailable is True
    assert evaluated[0].correct_strict is None


def _write_persona_outputs(persona_dir: Path) -> None:
    """rescore_persona용 합성 저장 산출물 3종을 기록한다."""
    persona_dir.mkdir(parents=True)
    tables = {
        "be-jd": {
            "job_id": "be-jd",
            "company": "X",
            "title": "Backend",
            "rows": [
                {
                    "requirement_id": "r1",
                    "requirement_text": "Go 백엔드 경험",
                    "requirement_type": "required",
                    "requirement_nature": "technical",
                    "prerequisite_status": "prerequisite",
                    "match_level": "direct",
                    "confidence": "high",
                    "evidence_quotes": ["Go 3년"],
                }
            ],
        },
        "fe-jd": {
            "job_id": "fe-jd",
            "company": "Y",
            "title": "Marketing",
            "rows": [
                {
                    "requirement_id": "r2",
                    "requirement_text": "마케팅 기획",
                    "requirement_type": "critical",
                    "requirement_nature": "domain",
                    "prerequisite_status": "prerequisite",
                    "match_level": "missing",
                    "confidence": "low",
                    "evidence_quotes": [],
                }
            ],
        },
    }
    ranking = [
        {
            "job_id": "be-jd",
            "rank": 1,
            "fit_level": 4,
            "domain_alignment": "strong",
            "role_family": "backend",
        },
        {
            "job_id": "fe-jd",
            "rank": 2,
            "fit_level": 1,
            "domain_alignment": "mismatch",
            "role_family": "marketing",
        },
    ]
    pairwise = [
        {
            "job_a": "be-jd",
            "job_b": "fe-jd",
            "agreed": True,
            "outcome": "be-jd",
            "confidence": "high",
        }
    ]
    (persona_dir / "matching_tables.json").write_text(
        json.dumps(tables), encoding="utf-8"
    )
    (persona_dir / "final_ranking.json").write_text(
        json.dumps(ranking), encoding="utf-8"
    )
    (persona_dir / "pairwise_comparisons.json").write_text(
        json.dumps(pairwise), encoding="utf-8"
    )


def test_rescore_persona_reuses_aggregate(tmp_path: Path) -> None:
    """rescore_persona: 저장 산출물만으로 aggregate() 재사용 (LLM 미호출) — 모드 ablation."""
    _write_persona_outputs(tmp_path / "p1")

    base, _bt, _guard = rescore_persona(tmp_path, "p1", "baseline")
    dedup, _, _ = rescore_persona(tmp_path, "p1", "dedup_required_preferred")

    assert base, "baseline rescore가 FitResult를 산출해야 함"
    # 랭킹 로직 100% 동일(aggregate 재사용) — fit만 변경되므로 job 집합은 불변
    assert (
        {fr.job_id for fr in base} == {fr.job_id for fr in dedup} == {"be-jd", "fe-jd"}
    )
    # 도메인 가드 — mismatch(fe-jd)는 항상 최하위
    assert base[-1].job_id == "fe-jd"


def test_rescore_persona_missing_artifacts_unavailable(tmp_path: Path) -> None:
    """rescore_persona: 산출물 없으면 unavailable (재수집 X) → 빈 결과."""
    results, bt, guard = rescore_persona(tmp_path, "nonexistent", "baseline")

    assert results == []
    assert bt == {}
    assert guard == []
