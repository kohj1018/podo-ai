"""T-009 Acceptance Criteria tests — listwise 재랭킹 (rerank_listwise.py).

SPEC §7-3 알고리즘을 검증한다.
"""

from typing import Any

from core.models import MatchingTable, MatchRow
from worker.rerank_listwise import compress_table, listwise_rank

# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------

_DOM_CTX_STRONG = {"domain_alignment": "strong", "role_family": "frontend"}
_DOM_CTX_ADJACENT = {"domain_alignment": "adjacent", "role_family": "backend"}
_DOM_CTX_MISMATCH = {"domain_alignment": "mismatch", "role_family": "marketing"}


def _row(
    rid: str,
    req_type: str = "required",
    req_nature: str = "technical",
    prereq_status: str = "prerequisite",
    req_category: str = "other",
    match_level: str = "direct",
    confidence: str = "high",
    invalid_match: bool = False,
    risk_note: str = "",
    req_text: str = "some requirement",
) -> MatchRow:
    return MatchRow(
        requirement_id=rid,
        requirement_text=req_text,
        requirement_type=req_type,
        requirement_nature=req_nature,
        prerequisite_status=prereq_status,
        requirement_category=req_category,
        match_level=match_level,
        confidence=confidence,
        invalid_match=invalid_match,
        risk_note=risk_note,
    )


def _table(
    rows: list[MatchRow],
    job_id: str = "job-1",
    company: str = "Corp",
    title: str = "Dev",
) -> MatchingTable:
    return MatchingTable(job_id=job_id, company=company, title=title, rows=rows)


def _fake_llm(ranking: list[dict[str, str]]) -> Any:
    """LLM 응답을 fake 주입하는 _call_fn 팩토리."""

    def _call_fn(system: str, user: str, max_tokens: int, temperature: float) -> str:
        import json

        return json.dumps(
            {
                "ranking": ranking,
                "uncertainty_notes": "",
            }
        )

    return _call_fn


# ---------------------------------------------------------------------------
# AC-3: compress_table — 원문 없이 요약만
# ---------------------------------------------------------------------------


def test_AC_3_compress_no_raw_text():
    """AC-3: compress_table 결과에 JD/이력서 원문 텍스트가 포함되지 않는다.

    [Given] 매칭표 (각 행에 requirement_text 등 메타 포함)
    [When] compress_table 호출
    [Then] 반환값에 카운트·strong·gaps·invalid·risks 요약만 있고
           requirement_text 원문(raw text)은 포함되지 않는다.
    """
    rows = [
        _row(
            "r1",
            req_type="critical",
            req_nature="technical",
            match_level="direct",
            confidence="high",
            req_text="React 개발 경험 3년 이상",
        ),
        _row(
            "r2",
            req_type="required",
            req_nature="technical",
            match_level="missing",
            req_text="TypeScript 숙련",
        ),
        _row(
            "r3",
            req_type="preferred",
            req_nature="technical",
            prereq_status="prerequisite",
            match_level="missing",
            req_text="GraphQL 경험",
        ),
        _row(
            "r4",
            req_type="required",
            req_nature="behavioral",
            prereq_status="behavioral_preference",
            match_level="weak",
            req_text="주도적 문제 해결",
        ),
        _row(
            "r5",
            req_type="required",
            prereq_status="product_duty",
            match_level="missing",
            req_text="POS 시스템 구축",
        ),
        _row(
            "r6",
            req_type="required",
            match_level="direct",
            invalid_match=True,
            req_text="Redis 경험",
        ),
        _row(
            "r7",
            req_type="required",
            match_level="direct",
            risk_note="연차 미달 우려",
            req_text="서버 개발 경험",
        ),
    ]
    table = _table(rows, job_id="job-1")
    ctx = {"domain_alignment": "strong", "role_family": "frontend"}

    result = compress_table(table, ctx)

    # 압축 결과 타입 확인
    assert isinstance(result, dict)

    # 필수 요약 필드 존재
    assert "job_id" in result
    assert result["job_id"] == "job-1"

    # JD/이력서 원문 텍스트가 값에 포함되지 않아야 한다
    # (raw requirement_text 문자열이 그대로 노출되면 안 됨 — 카운트/요약만)
    result_str = str(result)
    assert "React 개발 경험 3년 이상" not in result_str
    assert "TypeScript 숙련" not in result_str
    assert "GraphQL 경험" not in result_str
    assert "주도적 문제 해결" not in result_str
    assert "POS 시스템 구축" not in result_str
    assert "Redis 경험" not in result_str

    # 카운트 기반 요약 키 존재
    assert "counts" in result  # type별 매칭 카운트
    assert "strong_count" in result
    assert "core_prerequisite_gaps" in result
    assert "preferred_technical_gaps" in result
    assert "behavioral_gaps" in result
    assert "product_duty_gaps_not_blocking" in result
    assert "invalid_matches" in result
    assert "risks" in result


# ---------------------------------------------------------------------------
# AC-1: listwise_rank — 중복/누락 보정 (재질의 후에도 누락 잔존 케이스)
# ---------------------------------------------------------------------------


def test_AC_1_no_omission_no_duplicate():
    """AC-1: LLM이 중복/누락 응답 후 재질의도 누락이면 결과는 모든 job_id를 정확히 1번 포함한다.

    [Given] LLM 1차 응답: job-1 중복, job-3 누락 / 재질의 응답도 job-3 누락
    [When] listwise_rank 호출
    [Then] 결과 ranking에 job-1, job-2, job-3이 정확히 한 번씩 포함되고
           warnings에 누락/중복 기록
    """
    job_ids = ["job-1", "job-2", "job-3"]

    # 1차: job-1 중복, job-3 누락
    # 재질의(2차): 여전히 job-3 누락
    call_count = {"n": 0}

    def _fake_call_fn(
        system: str, user: str, max_tokens: int, temperature: float
    ) -> str:
        import json

        call_count["n"] += 1
        if call_count["n"] == 1:
            # 1차: job-1 중복, job-3 누락
            return json.dumps(
                {
                    "ranking": [
                        {"job_id": "job-2", "reason": "good fit"},
                        {"job_id": "job-1", "reason": "decent fit"},
                        {"job_id": "job-1", "reason": "duplicate"},  # 중복
                    ],
                    "uncertainty_notes": "",
                }
            )
        else:
            # 재질의: 여전히 job-3 누락
            return json.dumps(
                {
                    "ranking": [
                        {"job_id": "job-2", "reason": "good fit"},
                        {"job_id": "job-1", "reason": "decent fit"},
                    ],
                    "uncertainty_notes": "",
                }
            )

    tables = {
        "job-1": _table([_row("r1")], job_id="job-1"),
        "job-2": _table([_row("r1")], job_id="job-2"),
        "job-3": _table([_row("r1")], job_id="job-3"),
    }
    fits = {
        "job-1": {"level": 3},
        "job-2": {"level": 4},
        "job-3": {"level": 2},
    }
    domain_ctx = {
        "job-1": {"domain_alignment": "adjacent", "role_family": "backend"},
        "job-2": {"domain_alignment": "strong", "role_family": "frontend"},
        "job-3": {"domain_alignment": "weak", "role_family": "data"},
    }

    ranking, warnings = listwise_rank(
        tables=tables,
        domain_ctx=domain_ctx,
        fits=fits,
        _call_fn=_fake_call_fn,
    )

    # 모든 job_id가 정확히 한 번씩 포함
    result_ids = [item["job_id"] for item in ranking]
    assert sorted(result_ids) == sorted(job_ids), f"누락/중복: {result_ids}"
    assert len(result_ids) == len(set(result_ids)), f"중복 job_id: {result_ids}"

    # warnings에 누락/중복 기록
    assert len(warnings) > 0
    # 중복 또는 누락 관련 경고 존재
    assert any("중복" in w or "duplicate" in w.lower() for w in warnings) or any(
        "누락" in w or "missing" in w.lower() for w in warnings
    )


# ---------------------------------------------------------------------------
# AC-2: 안전 배치 — (fit_level, DOM_RANK) 기준, 맨끝 blind append 아님
# ---------------------------------------------------------------------------


def test_AC_2_fit_aware_placement():
    """AC-2: 재질의 후에도 누락된 job_id는 (fit_level, DOM_RANK) 기준으로 적절 위치에 삽입된다.

    [Given] job-1(fit=5, strong), job-2(fit=3, adjacent), job-3(fit=4, strong) 중
            LLM이 job-3을 1차·재질의 모두 누락
    [When] 안전 배치
    [Then] job-3(fit=4, strong)은 job-2(fit=3)보다 앞에 위치한다(맨끝 blind append 아님)
    """

    # LLM은 항상 job-3 누락
    def _fake_call_fn(
        system: str, user: str, max_tokens: int, temperature: float
    ) -> str:
        import json

        return json.dumps(
            {
                "ranking": [
                    {"job_id": "job-1", "reason": "best fit"},
                    {"job_id": "job-2", "reason": "decent fit"},
                ],
                "uncertainty_notes": "",
            }
        )

    tables = {
        "job-1": _table([_row("r1")], job_id="job-1"),
        "job-2": _table([_row("r1")], job_id="job-2"),
        "job-3": _table([_row("r1")], job_id="job-3"),
    }
    fits = {
        "job-1": {"level": 5},
        "job-2": {"level": 3},
        "job-3": {"level": 4},  # job-3은 fit=4, strong — job-2보다 앞에 와야 함
    }
    domain_ctx = {
        "job-1": {"domain_alignment": "strong", "role_family": "frontend"},
        "job-2": {"domain_alignment": "adjacent", "role_family": "backend"},
        "job-3": {"domain_alignment": "strong", "role_family": "fullstack"},
    }

    ranking, warnings = listwise_rank(
        tables=tables,
        domain_ctx=domain_ctx,
        fits=fits,
        _call_fn=_fake_call_fn,
    )

    result_ids = [item["job_id"] for item in ranking]

    # 모든 job_id 포함
    assert sorted(result_ids) == ["job-1", "job-2", "job-3"]

    # job-3(fit=4, strong)이 job-2(fit=3, adjacent)보다 앞 위치
    idx_job3 = result_ids.index("job-3")
    idx_job2 = result_ids.index("job-2")
    assert idx_job3 < idx_job2, (
        f"job-3(fit=4, strong)은 job-2(fit=3, adjacent)보다 앞에 위치해야 함. "
        f"실제 순서: {result_ids}"
    )

    # 맨끝 blind append가 아님 확인 (job-3이 마지막이 아님)
    assert result_ids[-1] != "job-3", (
        f"job-3이 blind append됨(맨끝). 순서: {result_ids}"
    )
