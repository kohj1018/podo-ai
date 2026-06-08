"""crawler 종료 코드 (T-085 AC-3) — 수집 실패 시 non-zero exit.

WHY: cron(GHA)이 조용히 green이면 수집 실패가 묻힌다(Fail #3 조용한 실패 금지).
exit_code_from_summary는 DB 불요 pure 함수라 항상 실행되고, crawl() 채널 실패 표면화는
DATABASE_URL 게이트(record_crawl_run이 실 conn 필요).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx
import pytest

from core import db
from crawler.__main__ import crawl, exit_code_from_summary

_NOW = datetime(2026, 6, 6, 12, 0, 0)


def test_AC_3_exit_code_nonzero_when_channel_failed() -> None:
    """채널 하나라도 실패하면 exit code 1 (GHA job fail 전파)."""
    summary = {
        "toss": {"new": 1, "kept": 0, "closed": 0, "status": "success"},
        "daangn": {"new": 0, "kept": 0, "closed": 0, "status": "failed"},
    }
    assert exit_code_from_summary(summary) == 1


def test_exit_code_zero_when_all_success() -> None:
    """전 채널 성공 시 exit code 0."""
    summary = {
        "toss": {"new": 1, "kept": 0, "closed": 0, "status": "success"},
        "daangn": {"new": 2, "kept": 1, "closed": 0, "status": "success"},
    }
    assert exit_code_from_summary(summary) == 0


def test_exit_code_nonzero_when_no_channels() -> None:
    """수집 채널이 0개(전면 실패)면 비정상 → non-zero."""
    assert exit_code_from_summary({}) == 1


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL (T-020 적용 Postgres)",
)
def test_AC_3_crawl_marks_failed_channel_and_exit_nonzero() -> None:
    """fetch 네트워크 오류 시 채널 status=failed + exit code 1 (통합)."""

    class _FailClient:
        def get(self, *args: Any, **kwargs: Any) -> Any:
            raise httpx.ConnectError("simulated network down")

    conn = db.connect()
    try:
        summary = crawl(conn, _FailClient(), now=_NOW)
        assert summary["toss"]["status"] == "failed"
        assert summary["daangn"]["status"] == "failed"
        assert exit_code_from_summary(summary) == 1
    finally:
        conn.rollback()
        conn.close()
