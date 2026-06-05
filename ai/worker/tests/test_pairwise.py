"""T-010 Acceptance Criteria tests — pairwise 비교 (compare_pairwise.py).

SPEC §7-4 알고리즘을 검증한다.
"""

import json
from typing import Any

from core.models import MatchingTable, MatchRow, PairwiseResult
from worker.compare_pairwise import run_pairwise

# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------


def _row(rid: str = "r1", match_level: str = "direct") -> MatchRow:
    return MatchRow(
        requirement_id=rid,
        requirement_text="some requirement",
        requirement_type="required",
        requirement_nature="technical",
        prerequisite_status="prerequisite",
        requirement_category="other",
        match_level=match_level,
        confidence="high",
        invalid_match=False,
    )


def _table(job_id: str) -> MatchingTable:
    return MatchingTable(
        job_id=job_id,
        company="Corp",
        title="Dev",
        rows=[_row()],
    )


def _fake_llm_fixed(winner: str, confidence: str = "high") -> Any:
    """항상 동일한 winner를 반환하는 LLM fake."""

    def _call_fn(system: str, user: str, max_tokens: int, temperature: float) -> str:
        return json.dumps(
            {"winner": winner, "confidence": confidence, "reason": "test"}
        )

    return _call_fn


def _fake_llm_seq(responses: list[dict[str, str]]) -> Any:
    """호출 순서대로 각기 다른 응답을 반환하는 LLM fake."""
    call_count = {"n": 0}

    def _call_fn(system: str, user: str, max_tokens: int, temperature: float) -> str:
        idx = call_count["n"]
        call_count["n"] += 1
        resp = responses[idx % len(responses)]
        return json.dumps(resp)

    return _call_fn


# ---------------------------------------------------------------------------
# AC-1: 양방향 일치(agreed) → outcome=승자 job_id, agreed=True
# ---------------------------------------------------------------------------


def test_AC_1_agreed_outcome():
    """AC-1: A/B·B/A 모두 같은 후보 승이면 outcome=그 job_id, agreed=True.

    [Given] 두 후보 job-x, job-y
    [When] run_pairwise(["job-x","job-y"]) — A/B winner=a, B/A winner=b (둘 다 job-x 승)
    [Then] A/B와 B/A 두 비교가 수행되고 양방향 승자가 같으면
           outcome=그 승자 job_id(job-x), agreed=True, confidence=min 이 된다.
    """
    tables = {
        "job-x": _table("job-x"),
        "job-y": _table("job-y"),
    }
    domain_ctx = {
        "job-x": {"domain_alignment": "strong", "role_family": "frontend"},
        "job-y": {"domain_alignment": "adjacent", "role_family": "backend"},
    }

    # A/B 호출: winner=a (슬롯 a=job-x 승). B/A 호출: winner=b (B/A 프레임의 b=job-x 승).
    # → 양방향 모두 job-x 승 → agreed=True, outcome="job-x".
    responses = [
        {"winner": "a", "confidence": "high", "reason": "A/B: job-x wins"},
        {"winner": "b", "confidence": "medium", "reason": "B/A: job-x wins"},
    ]
    results = run_pairwise(
        tables=tables,
        candidate_ids=["job-x", "job-y"],
        domain_ctx=domain_ctx,
        _call_fn=_fake_llm_seq(responses),
    )

    assert len(results) == 1
    r = results[0]
    # §3 계약: PairwiseResult 조립 (소비자 bradley_terry 가 outcome==job_id 로 판별)
    assert isinstance(r, PairwiseResult)
    assert r.job_a == "job-x"
    assert r.job_b == "job-y"
    assert r.outcome == "job-x"  # 슬롯 라벨이 아닌 승자 job_id
    assert r.agreed is True
    # confidence = min(high, medium) = medium
    assert r.confidence == "medium"


# ---------------------------------------------------------------------------
# AC-2: A/B·B/A 불일치 → outcome=tie, confidence=low, agreed=False
# ---------------------------------------------------------------------------


def test_AC_2_disagreement_is_tie():
    """AC-2: A/B·B/A 방향 불일치이면 outcome="tie"·confidence="low"·agreed=False.

    [Given] A/B는 job-x 승, B/A는 job-y 승 — 불일치
    [When] run_pairwise 호출
    [Then] outcome="tie", confidence="low", agreed=False로 기록된다(순서 편향 차단).
    """
    tables = {
        "job-x": _table("job-x"),
        "job-y": _table("job-y"),
    }
    domain_ctx: dict[str, dict[str, str]] = {}

    # A/B: winner=a (job-x 승). B/A: winner=a (B/A 프레임의 a=job-y 승) → 불일치.
    responses = [
        {"winner": "a", "confidence": "high", "reason": "A/B: job-x wins"},
        {"winner": "a", "confidence": "high", "reason": "B/A: job-y wins"},
    ]
    results = run_pairwise(
        tables=tables,
        candidate_ids=["job-x", "job-y"],
        domain_ctx=domain_ctx,
        _call_fn=_fake_llm_seq(responses),
    )

    assert len(results) == 1
    r = results[0]
    assert r.outcome == "tie"
    assert r.confidence == "low"
    assert r.agreed is False


# ---------------------------------------------------------------------------
# AC-3: 후보 3개 → 모든 (i<j) 쌍에 대해 결과 생성(누락 없음)
# ---------------------------------------------------------------------------


def test_AC_3_all_pairs_covered():
    """AC-3: 후보 3개이면 C(3,2)=3 쌍 모두 결과가 생성된다.

    [Given] 후보 3개 (job-x, job-y, job-z)
    [When] run_pairwise 호출
    [Then] (job-x,job-y), (job-x,job-z), (job-y,job-z) 모든 쌍에 결과가 생성된다.
    """
    candidate_ids = ["job-x", "job-y", "job-z"]
    tables = {cid: _table(cid) for cid in candidate_ids}
    domain_ctx: dict[str, dict[str, str]] = {}

    results = run_pairwise(
        tables=tables,
        candidate_ids=candidate_ids,
        domain_ctx=domain_ctx,
        _call_fn=_fake_llm_fixed("tie", "low"),
    )

    # C(3,2) = 3 쌍
    assert len(results) == 3

    # 모든 (i<j) 쌍 커버
    expected_pairs = {("job-x", "job-y"), ("job-x", "job-z"), ("job-y", "job-z")}
    actual_pairs = {(r.job_a, r.job_b) for r in results}
    assert actual_pairs == expected_pairs
