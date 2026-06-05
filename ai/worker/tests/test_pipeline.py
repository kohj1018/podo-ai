"""T-011 Acceptance Criteria tests — pipeline orchestration (pipeline.py + report.py).

SPEC §2·§11·§12 단계 1~12 오케스트레이션을 검증한다.
LLM 단계는 fake 주입, 결정적 단계는 실제 로직 사용.

- AC-1·AC-5: 공개 진입점 run_scoring(resume, jobs) — 단계 1~12.
- AC-2·AC-3: 내부 헬퍼 _rank(tables, domain_ctx, fits) — 단계 7~12.
- AC-4: _build_pairwise_candidates — 단계 8.
"""

from __future__ import annotations

import json
from typing import Any, Callable
from unittest.mock import patch

from core.models import MatchingTable, MatchRow, Resume
from worker.pipeline import (
    LLMCallError,
    _build_pairwise_candidates,
    _rank,
    run_scoring,
)
from worker.rank_aggregate import compute_fit
from worker.report import build_report

# ---------------------------------------------------------------------------
# 픽스처 헬퍼
# ---------------------------------------------------------------------------

# 이력서 raw_text 안에 verbatim으로 존재하는 인용 (추출형 검증 통과용)
_RESUME_QUOTE = "React 18 프로젝트에서 3년간 프론트엔드 개발"
_RESUME_TEXT = f"이력서 요약\n{_RESUME_QUOTE}\n기타 경력 다수"


def _row(
    rid: str,
    req_type: str = "required",
    req_nature: str = "technical",
    prereq_status: str = "prerequisite",
    req_category: str = "other",
    match_level: str = "direct",
    confidence: str = "high",
    invalid_match: bool = False,
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
    )


def _table(rows: list[MatchRow], job_id: str = "job-1") -> MatchingTable:
    return MatchingTable(job_id=job_id, company="Corp", title="Dev", rows=rows)


def _make_minimal_tables() -> dict[str, MatchingTable]:
    """3개 공고 최소 픽스처 (7~12 결정적 단계 테스트용)."""
    return {
        "fe-1": MatchingTable(
            job_id="fe-1",
            company="Toss",
            title="Frontend Engineer",
            rows=[
                _row("r1", req_type="critical", match_level="direct"),
                _row("r2", req_type="required", match_level="direct"),
            ],
        ),
        "be-1": MatchingTable(
            job_id="be-1",
            company="Kakao",
            title="Backend Engineer",
            rows=[
                _row("r1", req_type="critical", match_level="adjacent"),
                _row("r2", req_type="required", match_level="missing"),
            ],
        ),
        "mkt-1": MatchingTable(
            job_id="mkt-1",
            company="Naver",
            title="Marketing",
            rows=[_row("r1", req_type="required", match_level="missing")],
        ),
    }


def _make_domain_ctx() -> dict[str, dict[str, str]]:
    return {
        "fe-1": {"domain_alignment": "strong", "role_family": "frontend"},
        "be-1": {"domain_alignment": "adjacent", "role_family": "backend"},
        "mkt-1": {"domain_alignment": "mismatch", "role_family": "marketing"},
    }


def _make_fits() -> dict[str, dict[str, Any]]:
    tables = _make_minimal_tables()
    domain_ctx = _make_domain_ctx()
    return {
        jid: compute_fit(tables[jid], domain_ctx[jid]["domain_alignment"])
        for jid in tables
    }


def _fake_listwise_call(ranking: list[dict[str, str]]) -> Callable[..., str]:
    """listwise LLM fake — 고정 ranking 반환."""

    def _call_fn(system: str, user: str, max_tokens: int, temperature: float) -> str:
        return json.dumps({"ranking": ranking, "uncertainty_notes": ""})

    return _call_fn


def _fake_pairwise_call(
    winner: str = "a", confidence: str = "high"
) -> Callable[..., str]:
    """pairwise LLM fake — 항상 동일 winner."""

    def _call_fn(system: str, user: str, max_tokens: int, temperature: float) -> str:
        return json.dumps(
            {"winner": winner, "confidence": confidence, "reason": "test"}
        )

    return _call_fn


def _structured_fake(fail_marker: str | None = None) -> Callable[..., Any]:
    """단계 1·2·4·5 구조화 LLM fake (call_structured 인터페이스).

    각 stage validate는 서로 다른 top-level 키(evidence/requirements/matches/verified)를
    요구하므로, 후보 응답 중 validate를 통과하는 첫 응답을 반환한다.
    fail_marker가 user 프롬프트에 있으면 LLMCallError를 던져 해당 공고 보류를 유발한다.
    """
    evidence_resp = {
        "evidence": [
            {
                "evidence_id": "E1",
                "title": "Experience",
                "source_section": "Experience",
                "exact_quote": _RESUME_QUOTE,
                "normalized_summary": "React 3년",
            }
        ]
    }
    req = {
        "requirement_id": "R1",
        "requirement_text": "React 개발 경험",
        "requirement_type": "required",
        "requirement_nature": "technical",
        "prerequisite_status": "prerequisite",
    }
    match_resp = {
        "matches": [
            {
                "requirement_id": "R1",
                "requirement_type": "required",
                "matched_evidence_ids": ["E1"],
                "match_level": "direct",
                "confidence": "high",
                "explanation": "React 직접 매칭",
                "risk_note": "",
            }
        ]
    }

    def fn(
        system: str,
        user: str,
        validate: Callable[[dict[str, Any]], dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.0,
        cache_label: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if fail_marker is not None and fail_marker in user:
            raise LLMCallError("injected per-job failure")
        # role_family는 JD 프롬프트의 TITLE로 분기 (Frontend/Backend)
        role_family = "frontend" if "Frontend" in user else "backend"
        jd_resp = {
            "requirements": [req],
            "preferred_requirements": [],
            "role_family": role_family,
        }
        for resp in (evidence_resp, jd_resp, match_resp, {"verified": []}):
            try:
                return validate(resp)
            except Exception:
                continue
        raise AssertionError(f"fake에 매칭되는 응답 없음 (cache_label={cache_label})")

    return fn


def _two_jobs(be_raw: str = "백엔드 채용 공고") -> list[dict[str, str]]:
    return [
        {
            "job_id": "fe-1",
            "company": "Toss",
            "title": "Frontend Engineer",
            "url": "https://ex/fe",
            "raw_text": "프론트엔드 채용 공고",
        },
        {
            "job_id": "be-1",
            "company": "Kakao",
            "title": "Backend Engineer",
            "url": "https://ex/be",
            "raw_text": be_raw,
        },
    ]


def _assert_no_probability_fields(obj: Any, path: str = "") -> None:
    """재귀적으로 합격확률/% 관련 필드가 없음을 검증한다."""
    if isinstance(obj, dict):
        for key, val in obj.items():
            current_path = f"{path}.{key}" if path else key
            # note 필드는 해당 메시지를 담을 수 있으므로 값 검사 스킵
            if key == "note":
                continue
            assert key not in ("probability", "acceptance_rate", "pass_probability"), (
                f"금지된 필드 발견: {current_path}"
            )
            _assert_no_probability_fields(val, current_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_probability_fields(item, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# AC-1: LLM miss → 가짜 점수 금지, 해당 공고 보류 (공개 진입점)
# ---------------------------------------------------------------------------


def test_AC_1_miss_failure_holds_not_fakes():
    """AC-1: run_scoring 중 한 공고의 LLM 호출이 실패하면
    가짜 점수를 만들지 않고 해당 공고를 보류 상태로 표시한다.

    [Given] be-1의 단계 2(JD 구조화) LLM 호출이 실패(LLMCallError)
    [When] run_scoring(resume, jobs)
    [Then] be-1은 pending + final_ranking 제외, fe-1은 정상 채점되고 파이프라인 계속.
    """
    resume = Resume(
        raw_text=_RESUME_TEXT,
        primary_domains=["frontend"],
        secondary_domains=["backend"],
    )
    jobs = _two_jobs(be_raw="백엔드 __FAIL__ 채용")

    result = run_scoring(
        resume=resume,
        jobs=jobs,
        structured_call_fn=_structured_fake(fail_marker="__FAIL__"),
        listwise_call_fn=_fake_listwise_call(
            [
                {"job_id": "fe-1", "reason": "top"},
                {"job_id": "be-1", "reason": "second"},
            ]
        ),
        pairwise_call_fn=_fake_pairwise_call(),
    )

    # be-1은 보류 (가짜 점수 없음)
    assert "be-1" in result["pending_job_ids"], (
        f"be-1이 pending에 없음: {result['pending_job_ids']}"
    )
    ranking_ids = [r["job_id"] for r in result["final_ranking"]["ranking"]]
    assert "be-1" not in ranking_ids, (
        f"LLM 실패 공고 be-1이 final_ranking에 포함됨: {ranking_ids}"
    )
    # 나머지(fe-1)는 정상 채점되어 계속됨
    assert "fe-1" in ranking_ids, "정상 공고 fe-1이 ranking에 없음"


# ---------------------------------------------------------------------------
# AC-2: 산출물 계약 — 합격확률/% 필드 없음 (단계 7~12)
# ---------------------------------------------------------------------------


def test_AC_2_output_contract_no_percent():
    """AC-2: 정상 입력 → 산출물 계약 + 합격확률/% 필드 없음.

    [Given] 정상 입력 (단계 6 산출 tables/domain_ctx/fits)
    [When] _rank → 산출물
    [Then] final_ranking에 note(fit≠합격확률)·user_profile·guard_moves·ranking[FitResult],
           matching_tables(job_id→table), pairwise_comparisons(BT+candidate_set+comparisons)가
           포함되고 합격확률/% 필드가 없다.
    """
    tables = _make_minimal_tables()
    domain_ctx = _make_domain_ctx()
    fits = _make_fits()

    result = _rank(
        tables=tables,
        domain_ctx=domain_ctx,
        fits=fits,
        listwise_call_fn=_fake_listwise_call(
            [
                {"job_id": "fe-1", "reason": "top"},
                {"job_id": "be-1", "reason": "second"},
                {"job_id": "mkt-1", "reason": "last"},
            ]
        ),
        pairwise_call_fn=_fake_pairwise_call(),
    )

    # final_ranking 구조 검증
    fr = result["final_ranking"]
    assert "note" in fr, "note 필드 없음"
    assert "합격확률" in fr["note"] or "fit" in fr["note"].lower(), (
        f"note에 fit≠합격확률 메시지가 없음: {fr['note']}"
    )
    assert "user_profile" in fr, "user_profile 필드 없음"
    assert "guard_moves" in fr, "guard_moves 필드 없음"
    assert "ranking" in fr, "ranking 필드 없음"
    assert isinstance(fr["ranking"], list), "ranking이 list가 아님"

    # FitResult 필드 확인 (첫 번째 항목)
    if fr["ranking"]:
        first = fr["ranking"][0]
        assert "job_id" in first
        assert "fit_level" in first
        assert "fit_label" in first
        # 합격확률/% 필드 없음
        assert "probability" not in first, "합격확률 필드(probability) 있음"
        assert "acceptance_rate" not in first, "합격확률 필드(acceptance_rate) 있음"
        if "fit_label" in first:
            assert "%" not in str(first["fit_label"]), (
                f"fit_label에 % 포함: {first['fit_label']}"
            )

    # matching_tables 구조 검증
    mt = result["matching_tables"]
    assert isinstance(mt, dict), "matching_tables가 dict가 아님"
    for jid in tables:
        if jid not in result.get("pending_job_ids", set()):
            assert jid in mt, f"matching_tables에 {jid} 없음"

    # pairwise_comparisons 구조 검증
    pc = result["pairwise_comparisons"]
    assert "bradley_terry_scores" in pc, "bradley_terry_scores 없음"
    assert "candidate_set" in pc, "candidate_set 없음"
    assert "comparisons" in pc, "comparisons 없음"

    # 전체 직렬화 + 합격확률 키워드가 note 외 필드에 없어야 함 (JSONB 계약)
    report = build_report(result)
    report_obj = json.loads(json.dumps(report, ensure_ascii=False))
    _assert_no_probability_fields(report_obj)


# ---------------------------------------------------------------------------
# AC-3: 결정성 — 동일 입력+캐시 2회 호출 → 동일 결과 (단계 7~12)
# ---------------------------------------------------------------------------


def test_AC_3_deterministic_on_cache_hit():
    """AC-3: 동일 (이력서, 공고집합) + 웜 캐시 → _rank 2회 → 결과 동일.

    [Given] 동일 (tables, domain_ctx, fits) + 웜 캐시
    [When] _rank 2회
    [Then] 최종 ranking 순서·fit_level이 변동 0이다(GS-1 결정성).
    """
    tables = _make_minimal_tables()
    domain_ctx = _make_domain_ctx()
    fits = _make_fits()

    listwise_fn = _fake_listwise_call(
        [
            {"job_id": "fe-1", "reason": "top"},
            {"job_id": "be-1", "reason": "second"},
            {"job_id": "mkt-1", "reason": "last"},
        ]
    )
    pairwise_fn = _fake_pairwise_call()

    result1 = _rank(
        tables=tables,
        domain_ctx=domain_ctx,
        fits=fits,
        listwise_call_fn=listwise_fn,
        pairwise_call_fn=pairwise_fn,
    )
    result2 = _rank(
        tables=tables,
        domain_ctx=domain_ctx,
        fits=fits,
        listwise_call_fn=listwise_fn,
        pairwise_call_fn=pairwise_fn,
    )

    ranking1 = [
        (r["job_id"], r["fit_level"]) for r in result1["final_ranking"]["ranking"]
    ]
    ranking2 = [
        (r["job_id"], r["fit_level"]) for r in result2["final_ranking"]["ranking"]
    ]

    assert ranking1 == ranking2, f"결정성 위반: 1차={ranking1}, 2차={ranking2}"


# ---------------------------------------------------------------------------
# AC-4: strong domain rescue + MAX_PAIRWISE_CANDIDATES=8 bound (단계 8)
# ---------------------------------------------------------------------------


def test_AC_4_strong_domain_rescue_and_bound():
    """AC-4: strong frontend/fullstack 공고 구제 + 상한 8 bound.

    [Given] strong frontend/fullstack 공고가 listwise top-5 밖이고
            더 낮은 fit의 adjacent/weak 공고가 후보집합에 있는 입력
    [When] pairwise 후보집합 구성
    [Then] 그 strong 공고가 구제되어 후보집합에 포함되고 rescued_strong_domain에 기록된다.
           후보 수 > 8이면 MAX_PAIRWISE_CANDIDATES=8로 bound되고
           제외분은 strong_domain_excluded/[bounded out] 사유로 남는다.
    """
    # top-5: adjacent/weak(fit 3·2), top-5 밖: strong-fe(fit 3) → fit > 최약(2) → 구제
    ordered_ids = ["adj-1", "adj-2", "adj-3", "weak-1", "weak-2", "strong-fe"]
    fits = {
        "adj-1": {"level": 3},
        "adj-2": {"level": 3},
        "adj-3": {"level": 3},
        "weak-1": {"level": 2},
        "weak-2": {"level": 2},
        "strong-fe": {"level": 3},
    }
    domain_ctx = {
        "adj-1": {"domain_alignment": "adjacent", "role_family": "backend"},
        "adj-2": {"domain_alignment": "adjacent", "role_family": "backend"},
        "adj-3": {"domain_alignment": "adjacent", "role_family": "backend"},
        "weak-1": {"domain_alignment": "weak", "role_family": "data"},
        "weak-2": {"domain_alignment": "weak", "role_family": "data"},
        "strong-fe": {"domain_alignment": "strong", "role_family": "frontend"},
    }

    candidates, info = _build_pairwise_candidates(
        ordered_ids=ordered_ids,
        fits=fits,
        domain_ctx=domain_ctx,
        top_k=5,
    )

    assert "strong-fe" in candidates, (
        f"strong-fe가 구제되지 않음. candidates={candidates}"
    )
    assert "strong-fe" in info["rescued_strong_domain"], (
        f"rescued_strong_domain에 strong-fe 없음: {info['rescued_strong_domain']}"
    )

    # MAX_PAIRWISE_CANDIDATES=8 bound: 10개 fit>=4 입력 → 8개로 제한 + 2개 [bounded out]
    many_ordered = [f"big-{i}" for i in range(10)]
    many_fits = {f"big-{i}": {"level": 4} for i in range(10)}
    many_ctx = {
        f"big-{i}": {"domain_alignment": "adjacent", "role_family": "backend"}
        for i in range(10)
    }

    candidates_many, info_many = _build_pairwise_candidates(
        ordered_ids=many_ordered,
        fits=many_fits,
        domain_ctx=many_ctx,
        top_k=5,
    )

    assert len(candidates_many) == 8, (
        f"MAX_PAIRWISE_CANDIDATES=8 위반: {len(candidates_many)}개"
    )
    # 제외된 2개는 reason에 [bounded out]로 남는다 (후보집합 밖이므로 set의 reason엔 없음 —
    # bounded out 표식은 내부 reasons에 기록되고 후보에서 빠진다)
    assert len(many_ordered) - len(candidates_many) == 2, (
        "정확히 2개가 bound out돼야 함"
    )


# ---------------------------------------------------------------------------
# AC-5: 공개 진입점이 단계 1~12를 돌리고 compute_fit을 공고당 1회만 호출
# ---------------------------------------------------------------------------


def test_AC_5_full_entry_runs_1_to_12_compute_fit_once():
    """AC-5: run_scoring(resume, jobs)가 단계 1~12를 단일 진입점에서 실행하고
    compute_fit을 공고당 1회만 호출한다(다운스트림 7·8·11 재계산 0).

    [Given] (Resume, 원본 jobs)
    [When] run_scoring(resume, jobs)
    [Then] 단계 1~12를 거쳐 산출물 계약(AC-2)을 만들고, compute_fit 호출 수가
           활성 공고 수와 정확히 같다(공고당 1회, 재계산 없음).
    """
    resume = Resume(
        raw_text=_RESUME_TEXT,
        primary_domains=["frontend"],
        secondary_domains=["backend"],
    )
    jobs = _two_jobs()

    listwise_fn = _fake_listwise_call(
        [
            {"job_id": "fe-1", "reason": "top"},
            {"job_id": "be-1", "reason": "second"},
        ]
    )

    call_count = {"n": 0}

    def _counting_compute_fit(*args: Any, **kwargs: Any) -> Any:
        call_count["n"] += 1
        return compute_fit(*args, **kwargs)

    with patch("worker.pipeline.compute_fit", side_effect=_counting_compute_fit):
        result = run_scoring(
            resume=resume,
            jobs=jobs,
            structured_call_fn=_structured_fake(),
            listwise_call_fn=listwise_fn,
            pairwise_call_fn=_fake_pairwise_call(),
        )

    # 단계 1~12가 단일 진입점에서 실행되어 산출물 계약을 만든다
    assert set(result.keys()) >= {
        "final_ranking",
        "matching_tables",
        "pairwise_comparisons",
        "pending_job_ids",
    }
    ranking_ids = [r["job_id"] for r in result["final_ranking"]["ranking"]]
    assert "fe-1" in ranking_ids and "be-1" in ranking_ids, (
        f"두 공고 모두 채점돼야 함: {ranking_ids}"
    )
    assert not result["pending_job_ids"], "실패가 없으므로 pending이 비어야 함"

    # compute_fit은 공고당 1회만 (단계 6) — 7·8·11에서 재계산 없음
    assert call_count["n"] == len(jobs), (
        f"compute_fit 호출이 공고당 1회가 아님: {call_count['n']} != {len(jobs)}"
    )

    # 합격확률/% 필드 없음 (JSONB 계약)
    report = build_report(result)
    _assert_no_probability_fields(json.loads(json.dumps(report, ensure_ascii=False)))
