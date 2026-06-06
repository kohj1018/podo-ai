"""crawler 진입점 (T-025 AC-1/2).

DATABASE_URL 없으면 skip. fetch는 fake client, DB는 compose PG(rollback 멱등).
"""

from __future__ import annotations

import ast
import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest

from core import db
from crawler.__main__ import crawl

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


class _FakeResp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    """토스 1건(목록+상세) + 당근 1건(목록 content 포함)."""

    def get(self, url: str, headers: Any = None, timeout: Any = None) -> _FakeResp:
        if "greenhouse" in url:  # 당근 목록
            return _FakeResp(
                {
                    "jobs": [
                        {
                            "id": 2,
                            "title": "Backend Engineer",
                            "absolute_url": "https://daangn.test/c2",
                            "content": "<p>Backend</p>",
                        }
                    ]
                }
            )
        if "/jobs/" in url:  # 토스 상세
            return _FakeResp({"success": {"content": "<p>Frontend</p>"}})
        if url.endswith("/jobs"):  # 토스 목록
            return _FakeResp(
                {
                    "success": [
                        {
                            "id": 1,
                            "title": "Frontend Engineer",
                            "absolute_url": "https://toss.test/c1",
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected url {url}")


def test_AC_1_entry_crawls_and_persists(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """crawl()이 토스·당근 수집분을 job_postings에 upsert + crawl_runs 채널별 1행 기록."""
    crawl(conn, _FakeClient(), now=_NOW)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM job_postings")
        jp = cur.fetchone()
        assert jp is not None and jp[0] == 2  # toss 1 + daangn 1
        cur.execute("SELECT channel, status FROM crawl_runs ORDER BY channel")
        runs = cur.fetchall()
        assert runs == [("daangn", "success"), ("toss", "success")]


def test_AC_2_crawl_runs_without_openai_key(
    conn: psycopg.Connection[tuple[Any, ...]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OPENAI_API_KEY 미설정에도 crawl 완주(LLM 분리) + crawler 패키지 openai import 0."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    summary = crawl(conn, _FakeClient(), now=_NOW)
    assert (
        summary["toss"]["new"] == 1 and summary["daangn"]["new"] == 1
    )  # OpenAI 없이 완주

    # crawler 패키지 소스에 openai import가 0건 (crawl/score 분리 — F-008 FAC-4)
    import crawler

    src = Path(crawler.__file__).parent
    offenders: list[str] = []
    for py in src.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders += [a.name for a in node.names if "openai" in a.name]
            elif isinstance(node, ast.ImportFrom) and "openai" in (node.module or ""):
                offenders.append(node.module or "")
    assert not offenders, f"crawler가 openai import: {offenders}"
