"""worker `--resume-id` 채점 경로 (T-037 AC-1).

DATABASE_URL 없으면 skip. DB의 마스킹 이력서(resume_id)를 읽어 채점·영속한다.
LLM은 fake 주입(무키, M2 패턴), 트랜잭션 rollback으로 멱등.
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
from worker.parse_resume import extract_skills_evidence

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL (T-020 적용 Postgres)",
)

# 마스킹본(직접 식별자 제거됨) — Skills 헤딩 + 경력 인용(extractive 검증 통과용).
_QUOTE = "React 18 프로젝트에서 3년간 프론트엔드 개발"
_MASKED_RESUME = (
    "이름: [MASKED_NAME]\n"
    "연락처: [MASKED_EMAIL]\n"
    "## Skills\n"
    "- React, TypeScript\n"
    "## 경력\n"
    f"- {_QUOTE}\n"
)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[tuple[Any, ...]]]:
    c = db.connect()
    try:
        yield c
        c.rollback()
    finally:
        c.close()


def _seed_jobs(cur: psycopg.Cursor[tuple[Any, ...]]) -> list[int]:
    rows = [
        ("toss", "Toss", "Frontend Engineer", "프론트엔드 채용 공고"),
        ("kakao", "Kakao", "Backend Engineer", "백엔드 채용 공고"),
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


def _structured_fake() -> Callable[..., Any]:
    evidence_resp = {
        "evidence": [
            {
                "evidence_id": "E1",
                "title": "Experience",
                "source_section": "Experience",
                "exact_quote": _QUOTE,
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


def test_AC_1_scores_db_resume_by_id_evidence_present(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """DB의 마스킹 이력서(resume_id)를 채점 → evidence>0 + ranking_runs(resume_id)/recommendations 영속."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO resumes (content, masked, source, upload_format) "
            "VALUES (%s, true, 'upload', 'txt') RETURNING id",
            (_MASKED_RESUME,),
        )
        rrow = cur.fetchone()
        assert rrow is not None
        rid = int(rrow[0])
        job_ids = _seed_jobs(cur)

    # 마스킹본에서 결정적 evidence 추출 > 0 (스택·경력 보존 — T-036 AC-2 정합)
    assert len(extract_skills_evidence(_MASKED_RESUME)) > 0

    run_id = run(
        conn,
        resume_id=rid,
        structured_call_fn=_structured_fake(),
        listwise_call_fn=_listwise_fake(job_ids),
        pairwise_call_fn=_pairwise_fake(),
    )

    with conn.cursor() as cur:
        # ranking_runs가 그 resume_id로 영속
        cur.execute(
            "SELECT count(*) FROM ranking_runs WHERE id = %s AND resume_id = %s",
            (run_id, rid),
        )
        rr = cur.fetchone()
        assert rr is not None and rr[0] == 1
        # recommendations 영속(채점 결과)
        cur.execute("SELECT count(*) FROM recommendations WHERE run_id = %s", (run_id,))
        rec = cur.fetchone()
        assert rec is not None and rec[0] >= 1
