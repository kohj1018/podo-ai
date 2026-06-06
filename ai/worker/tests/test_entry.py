"""worker 진입점 (T-023 AC-1/2) + seed 로드.

DATABASE_URL 없으면 skip. LLM은 fake 주입(§6-2), DB는 compose PG. 트랜잭션 rollback 멱등.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any, Callable

import psycopg
import pytest

from core import db
from worker.__main__ import run
from worker.config import load_seed_resume
from worker.pipeline import LLMCallError

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL (T-020 적용 Postgres)",
)

# seed 이력서 raw_text 안에 verbatim 존재하는 인용 (추출형 검증 통과용 — config 기본 seed와 정합)
_SEED_QUOTE = "React 18 프로젝트에서 3년간 프론트엔드 개발"


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[tuple[Any, ...]]]:
    c = db.connect()
    try:
        yield c
        c.rollback()
    finally:
        c.close()


def _seed_jobs(
    cur: psycopg.Cursor[tuple[Any, ...]], *, fail_be: bool = False
) -> list[int]:
    """Frontend + Backend job_postings 2건 삽입 → [job_id...]."""
    be_raw = "백엔드 __FAIL__ 채용 공고" if fail_be else "백엔드 채용 공고"
    rows = [
        ("toss", "Toss", "Frontend Engineer", "프론트엔드 채용 공고"),
        ("kakao", "Kakao", "Backend Engineer", be_raw),
    ]
    ids: list[int] = []
    for src, company, title, raw in rows:
        cur.execute(
            "INSERT INTO job_postings (source, company, title, url, raw_text) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (src, company, title, f"https://example.test/{title}", raw),
        )
        r = cur.fetchone()
        assert r is not None
        ids.append(int(r[0]))
    return ids


def _structured_fake(fail_marker: str | None = None) -> Callable[..., Any]:
    """단계 1·2·4·5 구조화 LLM fake (call_structured 인터페이스)."""
    evidence_resp = {
        "evidence": [
            {
                "evidence_id": "E1",
                "title": "Experience",
                "source_section": "Experience",
                "exact_quote": _SEED_QUOTE,
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
        raise AssertionError("fake에 매칭되는 응답 없음")

    return fn


def _listwise_fake(job_ids: list[int]) -> Callable[..., str]:
    ranking = [{"job_id": str(j), "reason": "r"} for j in job_ids]

    def _call(system: str, user: str, max_tokens: int, temperature: float) -> str:
        return json.dumps({"ranking": ranking, "uncertainty_notes": ""})

    return _call


def _pairwise_fake() -> Callable[..., str]:
    def _call(system: str, user: str, max_tokens: int, temperature: float) -> str:
        return json.dumps({"winner": "a", "confidence": "high", "reason": "t"})

    return _call


def test_seed_resume_loads() -> None:
    """load_seed_resume()가 합성 Resume(raw_text + domains)를 반환한다."""
    resume = load_seed_resume()
    assert _SEED_QUOTE in resume.raw_text
    assert resume.primary_domains == ["frontend"]


def test_AC_1_entry_runs_and_persists(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """진입점이 seed + DB jobs로 run_scoring 후 ranking_runs/recommendations 영속."""
    with conn.cursor() as cur:
        job_ids = _seed_jobs(cur)

    run_id = run(
        conn,
        structured_call_fn=_structured_fake(),
        listwise_call_fn=_listwise_fake(job_ids),
        pairwise_call_fn=_pairwise_fake(),
    )

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM ranking_runs WHERE id = %s", (run_id,))
        rr = cur.fetchone()
        assert rr is not None and rr[0] == 1
        cur.execute(
            "SELECT count(*) FROM recommendations WHERE run_id = %s AND status = 'scored'",
            (run_id,),
        )
        rec = cur.fetchone()
        assert rec is not None and rec[0] == 2  # 두 공고 모두 채점


def test_AC_2_held_does_not_abort_entry(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """일부 공고 LLM miss(보류) → 진입점 중단 없이 완주 + held 영속."""
    with conn.cursor() as cur:
        job_ids = _seed_jobs(cur, fail_be=True)  # Backend가 __FAIL__ → 보류

    run_id = run(
        conn,
        structured_call_fn=_structured_fake(fail_marker="__FAIL__"),
        listwise_call_fn=_listwise_fake(job_ids),
        pairwise_call_fn=_pairwise_fake(),
    )

    with conn.cursor() as cur:
        cur.execute(
            "SELECT job_posting_id, fit_level FROM recommendations "
            "WHERE run_id = %s AND status = 'held'",
            (run_id,),
        )
        held = cur.fetchall()
    assert len(held) == 1  # Backend 1건 보류
    assert (
        held[0][0] == job_ids[1] and held[0][1] is None
    )  # fit_level NULL(가짜 점수 X)
