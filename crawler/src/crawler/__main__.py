"""crawler 실행 진입점 — `python -m crawler` (T-025, 일일 수집 cron).

토스·당근 fetch → upsert_jobs(T-024) + record_crawl_run. crawl은 LLM 무관이라
OPENAI_API_KEY 불요(crawl/score 분리, F-008 FAC-4). run_at은 진입점에서 1회 생성·주입.

fixture 모드: `CRAWL_FIXTURE`(=== JOB === 파일 경로)가 있으면 라이브 fetch 대신 그
파일을 결정적 공고 집합으로 쓴다 — fresh-clone E2E 재현(graduation §5 #3)이 네트워크·
외부 API에 의존하지 않게 한다. fixture 공고의 company(toss/daangn)가 채널 그룹 키.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import psycopg

from core import db
from crawler.fetch_jobs import fetch_daangn_jobs, fetch_toss_jobs
from crawler.manual import parse_manual
from crawler.persistence import RawJob, record_crawl_run, upsert_jobs
from crawler.run_sources import record_source_crawl_status

logger = logging.getLogger(__name__)

_CHANNELS: list[tuple[str, Callable[[Any], list[RawJob]]]] = [
    ("toss", fetch_toss_jobs),
    ("daangn", fetch_daangn_jobs),
]


def load_fixture(path: str) -> dict[str, list[RawJob]]:
    """=== JOB === fixture 파일을 채널(company)별 공고 list로 그룹핑한다.

    파일은 parse_manual 형식(job_id/company/title/url 필드 + raw_text). company가
    채널 키(toss/daangn)여야 해당 채널로 수집된다 — 그 외 company는 _CHANNELS 루프에서
    무시된다(조용한 누락 방지를 위해 fixture는 toss/daangn만 사용).
    """
    grouped: dict[str, list[RawJob]] = {}
    for job in parse_manual(Path(path).read_text(encoding="utf-8")):
        grouped.setdefault(job["company"], []).append(job)
    return grouped


def crawl(
    conn: psycopg.Connection[tuple[Any, ...]],
    client: Any,
    *,
    now: datetime,
    fixture_jobs: dict[str, list[RawJob]] | None = None,
) -> dict[str, dict[str, int]]:
    """채널별 fetch → upsert + crawl_run 기록. 채널 실패는 격리(전체 중단 X).

    fixture_jobs가 주어지면 라이브 fetch 대신 채널별 fixture 공고를 쓴다(client 미사용).
    """
    summary: dict[str, dict[str, int]] = {}
    for channel, fetcher in _CHANNELS:
        try:
            jobs = (
                fixture_jobs.get(channel, [])
                if fixture_jobs is not None
                else fetcher(client)
            )
            counts = upsert_jobs(conn, channel, jobs, now=now)
            record_crawl_run(
                conn,
                channel,
                "success",
                run_at=now,
                new_count=counts["new"],
                closed_count=counts["closed"],
            )
            # T-063: 커버리지 패널이 읽는 소스별 현재 스냅샷도 갱신(active + 성공 시각).
            record_source_crawl_status(
                conn,
                channel,
                status="active",
                last_success_at=now,
                tier="tier1",
                method="custom",
            )
            summary[channel] = counts
            logger.info("crawl_ok channel=%s counts=%s", channel, counts)
        except Exception as exc:  # 시스템 경계 — 채널 fetch 실패 표면화(조용한 무시 X)
            record_crawl_run(conn, channel, "failed", run_at=now, error=str(exc))
            record_source_crawl_status(
                conn,
                channel,
                status="blocked",
                last_error=str(exc),
                tier="tier1",
                method="custom",
            )
            logger.error("crawl_failed channel=%s error=%s", channel, exc)
            summary[channel] = {"new": 0, "kept": 0, "closed": 0}
    return summary


def main() -> None:
    """`python -m crawler` — fetch→영속 완주, 커밋. crawl은 OPENAI_API_KEY 불요.

    CRAWL_FIXTURE 설정 시 라이브 fetch 대신 fixture 파일로 결정적 수집(E2E 재현).
    """
    conn = db.connect()
    now = datetime.now(timezone.utc)
    fixture_path = os.environ.get("CRAWL_FIXTURE")
    client = None if fixture_path else httpx.Client()
    try:
        fixture_jobs = load_fixture(fixture_path) if fixture_path else None
        crawl(conn, client, now=now, fixture_jobs=fixture_jobs)
        conn.commit()
    finally:
        if client is not None:
            client.close()
        conn.close()


if __name__ == "__main__":
    main()
