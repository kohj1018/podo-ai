"""crawler/persistence.py — crawler DB 영속 (T-024, ARCH §3-2 규칙1).

crawler는 자기 소유(job_postings·crawl_runs)에만 write한다. fetch 결과를 job_postings에
멱등 upsert + 전일 대비 diff_status 설정, 수집 결과를 crawl_runs에 run별 1행 기록한다.
시간(run_at/fetched_at)은 호출자가 주입한다(결정성 — Date.now 직접 X, §8).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg

from crawler.selection import classify_role_family

RawJob = dict[str, str]


def upsert_jobs(
    conn: psycopg.Connection[tuple[Any, ...]],
    source: str,
    jobs: list[RawJob],
    *,
    now: datetime,
) -> dict[str, int]:
    """source 채널 fetch 결과를 job_postings에 멱등 upsert + diff_status 설정.

    url 미존재=신규, 기존=유지, DB에 있으나 금일 미수집=마감. crawler만 write(§3-2).
    반환: {"new", "kept", "closed"} 카운트.
    """
    today_urls = {j["url"] for j in jobs}
    new_count = 0
    kept_count = 0
    with conn.cursor() as cur:
        cur.execute("SELECT url FROM job_postings WHERE source = %s", (source,))
        existing = {r[0] for r in cur.fetchall()}

        for job in jobs:
            role_family = classify_role_family(job.get("title", ""))
            if job["url"] in existing:
                kept_count += 1
                cur.execute(
                    "UPDATE job_postings SET company = %s, title = %s, "
                    "raw_text = %s, role_family = %s, diff_status = %s, "
                    "fetched_at = %s WHERE url = %s",
                    (
                        job["company"],
                        job["title"],
                        job["raw_text"],
                        role_family,
                        "유지",
                        now,
                        job["url"],
                    ),
                )
            else:
                new_count += 1
                cur.execute(
                    "INSERT INTO job_postings "
                    "(source, company, title, url, raw_text, "
                    "role_family, diff_status, fetched_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        source,
                        job["company"],
                        job["title"],
                        job["url"],
                        job["raw_text"],
                        role_family,
                        "신규",
                        now,
                    ),
                )

        # 빈 fetch는 수집 실패 신호일 수 있어 전체 마감 오동작 방지(QA-M2-007).
        closed = existing - today_urls if jobs else set()
        if closed:
            cur.execute(
                "UPDATE job_postings SET diff_status = %s "
                "WHERE source = %s AND url = ANY(%s)",
                ("마감", source, list(closed)),
            )

    return {"new": new_count, "kept": kept_count, "closed": len(closed)}


def record_crawl_run(
    conn: psycopg.Connection[tuple[Any, ...]],
    channel: str,
    status: str,
    *,
    run_at: datetime,
    new_count: int = 0,
    closed_count: int = 0,
    error: str | None = None,
) -> int:
    """crawl_runs에 run별 1행 append하고 id 반환.

    채널별 last_success_at은 조회 시 `MAX(run_at WHERE status='success')`로 파생(F-006).
    """
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO crawl_runs "
            "(channel, run_at, status, new_count, closed_count, error) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (channel, run_at, status, new_count, closed_count, error),
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])
