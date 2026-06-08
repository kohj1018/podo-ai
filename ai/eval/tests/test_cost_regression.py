"""T-069 비용 회귀 테스트 (F-021 N→K 비용 절감 실증).

AC-1: K 후보 경로 LLM 토큰·호출 수가 N 전체 경로 대비 낮다 (ratio < 1.0).
AC-2: 비용 측정 전/후 출력 계약 shape이 M4 동결 계약과 동일하다.
"""

from __future__ import annotations

from typing import Any

import pytest

from eval.cost_regression import CostReport, measure_cost

# ---------------------------------------------------------------------------
# 헬퍼: mock 스코어링 함수
# ---------------------------------------------------------------------------


def _make_scoring_fn(
    token_per_job: int,
    calls_per_job: int,
    fit_level: int = 3,
) -> tuple[Any, dict[str, int]]:
    """mock LLM 카운터가 붙은 스코어링 함수와 카운터 dict를 반환한다.

    Returns:
        (scoring_fn, counter_dict)
        counter_dict에 "tokens"·"calls" 키가 축적된다.
    """
    counter: dict[str, int] = {"tokens": 0, "calls": 0}

    def scoring_fn(
        jobs: list[dict[str, Any]],
        token_counter: dict[str, int],
    ) -> list[dict[str, Any]]:
        for job in jobs:
            token_counter["tokens"] = token_counter.get("tokens", 0) + token_per_job
            token_counter["calls"] = token_counter.get("calls", 0) + calls_per_job
        return [
            {
                "job_id": j["job_id"],
                "fit_level": fit_level,
                "rank": i + 1,
                "evidence": [{"evidence_id": "E1", "title": "mock"}],
                "result": "scored",
            }
            for i, j in enumerate(jobs)
        ]

    return scoring_fn, counter


# ---------------------------------------------------------------------------
# AC-1: K 경로 비용 < N 경로 비용 (ratio < 1.0)
# ---------------------------------------------------------------------------


def test_AC_1_k_path_fewer_llm_calls_than_n() -> None:
    """AC-1: K 후보 경로 LLM 호출 수·토큰이 N 전체 경로 대비 낮다 (ratio < 1.0).

    Given: 동일 이력서 + JD 10개(N=10), K=4 후보
    When: measure_cost 실행
    Then: k_calls < n_calls, k_tokens < n_tokens, ratio < 1.0
    """
    resumes = [{"resume_id": "r1", "raw_text": "Python 3년 백엔드"}]
    jd_sets_n = [{"job_id": f"jd-{i}", "raw_text": f"JD {i}"} for i in range(10)]
    jd_sets_k = jd_sets_n[:4]  # K=4 후보만

    scoring_fn, _ = _make_scoring_fn(token_per_job=100, calls_per_job=1)

    report = measure_cost(
        scoring_fn=scoring_fn,
        resumes=resumes,
        jd_sets_n=jd_sets_n,
        jd_sets_k=jd_sets_k,
    )

    assert isinstance(report, CostReport)
    assert report.k_calls < report.n_calls, (
        f"K 경로 호출 수({report.k_calls})가 N 전체({report.n_calls})보다 적어야 함"
    )
    assert report.k_tokens < report.n_tokens, (
        f"K 경로 토큰({report.k_tokens})이 N 전체({report.n_tokens})보다 적어야 함"
    )
    assert report.ratio < 1.0, f"ratio({report.ratio:.3f})가 1.0 미만이어야 함"


def test_AC_1_cost_report_written_to_json(tmp_path: pytest.TempPathFactory) -> None:
    """AC-1: measure_cost 결과가 JSON으로 직렬화 가능한 필드를 포함한다."""
    resumes = [{"resume_id": "r1", "raw_text": "mock"}]
    jd_sets_n = [{"job_id": f"jd-{i}"} for i in range(6)]
    jd_sets_k = jd_sets_n[:3]

    scoring_fn, _ = _make_scoring_fn(token_per_job=50, calls_per_job=2)
    report = measure_cost(
        scoring_fn=scoring_fn,
        resumes=resumes,
        jd_sets_n=jd_sets_n,
        jd_sets_k=jd_sets_k,
    )

    import dataclasses
    import json

    data = dataclasses.asdict(report)
    dumped = json.dumps(data)
    loaded = json.loads(dumped)

    assert "n_tokens" in loaded
    assert "k_tokens" in loaded
    assert "n_calls" in loaded
    assert "k_calls" in loaded
    assert "ratio" in loaded


# ---------------------------------------------------------------------------
# AC-2: 출력 계약 shape 불변 (fit_level·evidence·result 필드 포함)
# ---------------------------------------------------------------------------


def test_AC_2_output_contract_unchanged() -> None:
    """AC-2: K 경로 스코어링 결과에 M4 동결 출력 계약 필드가 유지된다.

    Given: mock 스코어링 함수(fit_level·evidence·result 필드 반환)
    When: measure_cost에서 K 후보에 대한 스코어링 결과를 조회
    Then: fit_level·evidence·result shape이 M4 동결 계약과 동일하다.
    """
    resumes = [{"resume_id": "r1", "raw_text": "mock"}]
    jd_sets_n = [{"job_id": f"jd-{i}"} for i in range(5)]
    jd_sets_k = jd_sets_n[:3]

    scoring_fn, _ = _make_scoring_fn(token_per_job=80, calls_per_job=1, fit_level=4)
    report = measure_cost(
        scoring_fn=scoring_fn,
        resumes=resumes,
        jd_sets_n=jd_sets_n,
        jd_sets_k=jd_sets_k,
    )

    assert report.k_results is not None, "k_results가 None"
    for item in report.k_results:
        assert "fit_level" in item, f"fit_level 누락: {item.keys()}"
        assert "evidence" in item, f"evidence 누락: {item.keys()}"
        assert "result" in item, f"result 누락: {item.keys()}"
