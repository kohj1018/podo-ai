"""worker DB 영속 라운드트립 (T-022 AC-1/2/3).

DATABASE_URL 없으면 skip(로컬 게이트 보호). 각 테스트는 트랜잭션을 rollback해 멱등.
run_scoring 산출은 fixture(§6-2) — LLM 호출 없음.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest

from core import db
from worker.persistence import load_jobs, persist_run

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL (T-020 적용 Postgres)",
)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[tuple[Any, ...]]]:
    c = db.connect()
    try:
        yield c
        c.rollback()  # 테스트 데이터 폐기 — 멱등
    finally:
        c.close()


def _seed(cur: psycopg.Cursor[tuple[Any, ...]]) -> tuple[int, list[int]]:
    """resume 1 + job_postings 3 삽입 → (resume_id, [job_id...])."""
    cur.execute(
        "INSERT INTO resumes (content) VALUES (%s) RETURNING id", ("seed resume",)
    )
    row = cur.fetchone()
    assert row is not None
    resume_id = int(row[0])
    job_ids: list[int] = []
    for i in range(3):
        cur.execute(
            "INSERT INTO job_postings (source, company, title, url, raw_text) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            ("toss", "Co", "Role", f"https://example.test/{resume_id}-{i}", "JD"),
        )
        r = cur.fetchone()
        assert r is not None
        job_ids.append(int(r[0]))
    return resume_id, job_ids


def _fixture_result(scored: list[int], held: list[int]) -> dict[str, Any]:
    """run_scoring 산출 shape의 fixture — scored ranking + held pending(set)."""
    return {
        "final_ranking": {
            "note": "fit은 보수적 레벨",
            "user_profile": {},
            "guard_moves": [],
            "ranking": [
                {"job_id": str(j), "fit_level": 5 - k, "domain_alignment": "aligned"}
                for k, j in enumerate(scored)
            ],
        },
        "matching_tables": {},
        "pairwise_comparisons": {
            "bradley_terry_scores": {},
            "candidate_set": [],
            "comparisons": [],
        },
        "pending_job_ids": {str(j) for j in held},
    }


def test_AC_1_upsert_ranking_and_recommendations(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """복합키 upsert(재실행 1행) + recommendations scored 순서 + held 뒤 fit_level NULL."""
    with conn.cursor() as cur:
        resume_id, job_ids = _seed(cur)
        result = _fixture_result(scored=job_ids[:2], held=job_ids[2:])
        jobs = load_jobs(conn)

        run_id = persist_run(conn, resume_id, jobs, result)
        run_id2 = persist_run(conn, resume_id, jobs, result)  # 재upsert
        assert run_id == run_id2  # 복합키 동일 → 같은 행

        cur.execute(
            "SELECT count(*) FROM ranking_runs WHERE resume_id = %s", (resume_id,)
        )
        rr = cur.fetchone()
        assert rr is not None and rr[0] == 1  # 재upsert에도 1행

        cur.execute(
            "SELECT job_posting_id, rank_position, fit_level, status "
            "FROM recommendations WHERE run_id = %s ORDER BY rank_position",
            (run_id,),
        )
        recs = cur.fetchall()
        assert len(recs) == 3  # scored 2 + held 1
        # scored: rank 0,1, fit_level 채워짐, status scored
        assert recs[0] == (job_ids[0], 0, 5, "scored")
        assert recs[1] == (job_ids[1], 1, 4, "scored")
        # held: scored 뒤(rank 2), fit_level NULL, status held
        assert recs[2] == (job_ids[2], 2, None, "held")


def test_AC_2_gs1_through_db_byte_identical(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """동일 입력 2회 persist → result JSONB·recommendations 순서 동일(GS-1-through-DB)."""
    with conn.cursor() as cur:
        resume_id, job_ids = _seed(cur)
        result = _fixture_result(scored=job_ids[:2], held=job_ids[2:])
        jobs = load_jobs(conn)

        run_id = persist_run(conn, resume_id, jobs, result)
        cur.execute("SELECT result::text FROM ranking_runs WHERE id = %s", (run_id,))
        r1 = cur.fetchone()
        assert r1 is not None
        cur.execute(
            "SELECT job_posting_id, rank_position, status FROM recommendations "
            "WHERE run_id = %s ORDER BY rank_position",
            (run_id,),
        )
        recs1 = cur.fetchall()

        persist_run(conn, resume_id, jobs, result)  # 재실행
        cur.execute("SELECT result::text FROM ranking_runs WHERE id = %s", (run_id,))
        r2 = cur.fetchone()
        assert r2 is not None
        cur.execute(
            "SELECT job_posting_id, rank_position, status FROM recommendations "
            "WHERE run_id = %s ORDER BY rank_position",
            (run_id,),
        )
        recs2 = cur.fetchall()

        assert r1[0] == r2[0]  # result JSONB 바이트(정규화 text) 동일
        assert recs1 == recs2  # recommendations 순서 동일


def test_AC_3_held_status_preserved(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """LLM miss 보류 → status='held'·fit_level NULL + result.pending_job_ids 보존, 가짜 점수 없음."""
    with conn.cursor() as cur:
        resume_id, job_ids = _seed(cur)
        result = _fixture_result(
            scored=job_ids[:1], held=job_ids[1:]
        )  # 1 scored, 2 held
        jobs = load_jobs(conn)

        run_id = persist_run(conn, resume_id, jobs, result)

        cur.execute(
            "SELECT fit_level, status FROM recommendations "
            "WHERE run_id = %s AND status = 'held'",
            (run_id,),
        )
        held = cur.fetchall()
        assert len(held) == 2
        assert all(
            h[0] is None and h[1] == "held" for h in held
        )  # fit_level NULL, 가짜 점수 X

        # result.pending_job_ids에 보류 공고 보존
        cur.execute(
            "SELECT result -> 'pending_job_ids' FROM ranking_runs WHERE id = %s",
            (run_id,),
        )
        pj = cur.fetchone()
        assert pj is not None
        preserved = {int(x) for x in pj[0]}
        assert preserved == set(job_ids[1:])
