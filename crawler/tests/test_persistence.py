"""crawler DB 영속 (T-024 AC-1/2).

DATABASE_URL 없으면 skip. DB는 compose PG(트랜잭션 rollback 멱등), fetch는 fake client.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import httpx
import psycopg
import pytest

from core import db
from crawler.fetch_jobs import fetch_toss_jobs
from crawler.persistence import RawJob, record_crawl_run, upsert_jobs

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL (T-020 적용 Postgres)",
)

_NOW = datetime(2026, 6, 6, 12, 0, 0)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[tuple[Any, ...]]]:
    c = db.connect()
    try:
        yield c
        c.rollback()
    finally:
        c.close()


def _job(jid: str, url: str) -> RawJob:
    return {
        "job_id": jid,
        "company": "toss",
        "title": "Frontend Engineer",
        "url": url,
        "raw_text": "JD 본문",
    }


def test_AC_1_upsert_jobs_idempotent_diff(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """job_postings 멱등 upsert + 신규/유지/마감 diff_status."""
    day1 = [
        _job("toss-1", "https://toss.test/1"),
        _job("toss-2", "https://toss.test/2"),
    ]
    c1 = upsert_jobs(conn, "toss", day1, now=_NOW)
    assert c1 == {"new": 2, "kept": 0, "closed": 0}

    # 멱등: 동일 입력 재실행 → 신규 0, 유지 2, 행 수 그대로
    c2 = upsert_jobs(conn, "toss", day1, now=_NOW)
    assert c2 == {"new": 0, "kept": 2, "closed": 0}
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM job_postings WHERE source = 'toss'")
        cnt = cur.fetchone()
        assert cnt is not None and cnt[0] == 2

    # day2: url 2 마감, url 3 신규
    day2 = [
        _job("toss-1", "https://toss.test/1"),
        _job("toss-3", "https://toss.test/3"),
    ]
    c3 = upsert_jobs(conn, "toss", day2, now=_NOW)
    assert c3 == {"new": 1, "kept": 1, "closed": 1}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT diff_status FROM job_postings WHERE url = 'https://toss.test/2'"
        )
        r = cur.fetchone()
        assert r is not None and r[0] == "마감"
        cur.execute(
            "SELECT diff_status FROM job_postings WHERE url = 'https://toss.test/3'"
        )
        r = cur.fetchone()
        assert r is not None and r[0] == "신규"


class _FakeResp:
    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self._payload = payload
        self._status = status

    def raise_for_status(self) -> None:
        if self._status >= 400:
            req = httpx.Request("GET", "https://toss.test")
            raise httpx.HTTPStatusError(
                f"{self._status}",
                request=req,
                response=httpx.Response(self._status, request=req),
            )

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    """토스 목록 2건 중 1건 상세가 502 → 단건 skip 검증용."""

    def get(self, url: str, headers: Any = None, timeout: Any = None) -> _FakeResp:
        if url.endswith("/jobs"):
            return _FakeResp(
                {
                    "success": [
                        {
                            "id": 111,
                            "title": "Frontend Engineer",
                            "absolute_url": "https://toss.test/111",
                        },
                        {
                            "id": 222,
                            "title": "Backend Engineer",
                            "absolute_url": "https://toss.test/222",
                        },
                    ]
                }
            )
        if url.endswith("/jobs/111"):
            return _FakeResp({}, status=502)  # 단건 502
        if url.endswith("/jobs/222"):
            return _FakeResp({"success": {"content": "<p>Backend</p>"}})
        raise AssertionError(f"unexpected url {url}")


def test_AC_2_crawl_run_row_and_single_failure_skip(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """crawl_runs run별 1행(last_success_at 파생) + 단건 502 skip 후 루프 계속."""
    # run별 1행 append
    record_crawl_run(conn, "toss", "success", run_at=_NOW, new_count=5)
    record_crawl_run(
        conn,
        "toss",
        "partial",
        run_at=datetime(2026, 6, 6, 13, 0, 0),
        error="1 detail 502",
    )
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM crawl_runs WHERE channel = 'toss'")
        cnt = cur.fetchone()
        assert cnt is not None and cnt[0] == 2  # run별 1행
        cur.execute(
            "SELECT max(run_at) FROM crawl_runs WHERE channel = 'toss' AND status = 'success'"
        )
        last = cur.fetchone()
        assert last is not None and last[0] == _NOW  # last_success_at 파생

    # 단건 502 skip — 실패 공고는 건너뛰고 정상 공고는 수집(루프 계속)
    jobs = fetch_toss_jobs(_FakeClient())
    assert len(jobs) == 1  # 111(502) skip, 222 수집
    assert jobs[0]["job_id"] == "toss-222"
