"""core.db raw SQL 라운드트립 smoke (T-021 AC-1).

DATABASE_URL 없으면 skip(로컬 `pnpm validate` 게이트 보호) — CI(schema-contract.yml)가 주입.
"""

from __future__ import annotations

import os

import pytest

from core import db

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL (T-020 적용 Postgres)",
)


def test_AC_1_raw_sql_roundtrip_5_tables() -> None:
    """5테이블 insert→select 라운드트립 + crawl_runs run별 1행 append. 끝에 rollback(멱등)."""
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO resumes (content) VALUES (%s) RETURNING id", ("smoke",)
            )
            row = cur.fetchone()
            assert row is not None
            resume_id = row[0]

            cur.execute(
                "INSERT INTO job_postings (source, company, title, url, raw_text) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                ("toss", "Toss", "FE Engineer", "https://example.test/jd1", "JD 본문"),
            )
            row = cur.fetchone()
            assert row is not None
            job_id = row[0]

            cur.execute(
                "INSERT INTO ranking_runs (resume_id, job_set_hash, model, prompt_version, "
                "scoring_mode, ranking_mode, cache_key_version, result) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb) RETURNING id",
                (
                    resume_id,
                    "hash1",
                    "gpt-x",
                    "v1",
                    "pairwise",
                    "dom",
                    "v1",
                    '{"k": "v"}',
                ),
            )
            row = cur.fetchone()
            assert row is not None
            run_id = row[0]

            cur.execute(
                "INSERT INTO recommendations (run_id, job_posting_id, rank_position, fit_level, status) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (run_id, job_id, 1, 5, "scored"),
            )
            row = cur.fetchone()
            assert row is not None
            rec_id = row[0]

            # crawl_runs run별 1행 append (2 runs → 2 rows)
            cur.execute(
                "INSERT INTO crawl_runs (channel, status) VALUES (%s, %s)",
                ("toss", "ok"),
            )
            cur.execute(
                "INSERT INTO crawl_runs (channel, status) VALUES (%s, %s)",
                ("toss", "ok"),
            )

            # select back — 라운드트립
            cur.execute("SELECT content FROM resumes WHERE id = %s", (resume_id,))
            got = cur.fetchone()
            assert got is not None and got[0] == "smoke"

            cur.execute(
                "SELECT rank_position, fit_level, status FROM recommendations WHERE id = %s",
                (rec_id,),
            )
            got = cur.fetchone()
            assert got is not None and got == (1, 5, "scored")

            cur.execute("SELECT count(*) FROM crawl_runs WHERE channel = %s", ("toss",))
            got = cur.fetchone()
            assert got is not None and got[0] == 2  # run별 1행 append
        conn.rollback()  # 테스트 데이터 폐기 — 멱등(반복 실행 가능)
    finally:
        conn.close()


def test_fetch_all_read_smoke() -> None:
    """fetch_all 헬퍼 read smoke (read-only — DB 미오염)."""
    rows = db.fetch_all(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = %s",
        ("public",),
    )
    assert rows and rows[0][0] >= 5
