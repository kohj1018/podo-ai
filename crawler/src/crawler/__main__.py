"""crawler 실행 진입점 — `python -m crawler` (T-025, 일일 수집 cron).

토스·당근 fetch → upsert_jobs(T-024) + record_crawl_run. crawl은 LLM 무관이라
OPENAI_API_KEY 불요(crawl/score 분리, F-008 FAC-4). run_at은 진입점에서 1회 생성·주입.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import httpx
import psycopg

from core import db
from crawler.fetch_jobs import fetch_daangn_jobs, fetch_toss_jobs
from crawler.persistence import RawJob, record_crawl_run, upsert_jobs

logger = logging.getLogger(__name__)

_CHANNELS: list[tuple[str, Callable[[Any], list[RawJob]]]] = [
    ("toss", fetch_toss_jobs),
    ("daangn", fetch_daangn_jobs),
]


def crawl(
    conn: psycopg.Connection[tuple[Any, ...]],
    client: Any,
    *,
    now: datetime,
) -> dict[str, dict[str, int]]:
    """채널별 fetch → upsert + crawl_run 기록. 채널 실패는 격리(전체 중단 X)."""
    summary: dict[str, dict[str, int]] = {}
    for channel, fetcher in _CHANNELS:
        try:
            jobs = fetcher(client)
            counts = upsert_jobs(conn, channel, jobs, now=now)
            record_crawl_run(
                conn,
                channel,
                "success",
                run_at=now,
                new_count=counts["new"],
                closed_count=counts["closed"],
            )
            summary[channel] = counts
            logger.info("crawl_ok channel=%s counts=%s", channel, counts)
        except Exception as exc:  # 시스템 경계 — 채널 fetch 실패 표면화(조용한 무시 X)
            record_crawl_run(conn, channel, "failed", run_at=now, error=str(exc))
            logger.error("crawl_failed channel=%s error=%s", channel, exc)
            summary[channel] = {"new": 0, "kept": 0, "closed": 0}
    return summary


def main() -> None:
    """`python -m crawler` — fetch→영속 완주, 커밋. crawl은 OPENAI_API_KEY 불요."""
    conn = db.connect()
    client = httpx.Client()
    now = datetime.now(timezone.utc)
    try:
        crawl(conn, client, now=now)
        conn.commit()
    finally:
        client.close()
        conn.close()


if __name__ == "__main__":
    main()
