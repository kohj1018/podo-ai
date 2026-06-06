"""worker 실행 진입점 — `python -m worker` (T-023, M2 score 단계).

seed(합성) 이력서 + DB job_postings → run_scoring → persist_run(T-022).
seed 이력서는 config.load_seed_resume()로 주입(SPEC §9-4, 실 PII 비범위).
"""

from __future__ import annotations

from typing import Any, Callable

import psycopg

from core import db
from core.models import Resume
from worker import config, persistence
from worker.pipeline import run_scoring


def _ensure_seed_resume(
    conn: psycopg.Connection[tuple[Any, ...]], resume: Resume
) -> int:
    """seed 이력서를 resumes에 bootstrap insert(있으면 재사용)하고 id 반환.

    M2 seed 편의: resumes는 api 소유이나 M2엔 업로드 경로가 없어 진입점이 seed를
    1회 주입한다(content 동일 시 재사용 — 멱등).
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM resumes WHERE content = %s LIMIT 1", (resume.raw_text,)
        )
        row = cur.fetchone()
        if row is not None:
            return int(row[0])
        cur.execute(
            "INSERT INTO resumes (content) VALUES (%s) RETURNING id", (resume.raw_text,)
        )
        new = cur.fetchone()
        assert new is not None
        return int(new[0])


def run(
    conn: psycopg.Connection[tuple[Any, ...]],
    *,
    ranking_mode: str = persistence.DEFAULT_RANKING_MODE,
    structured_call_fn: Callable[..., Any] | None = None,
    listwise_call_fn: Callable[..., str] | None = None,
    pairwise_call_fn: Callable[..., str] | None = None,
) -> int:
    """seed 이력서 + DB jobs로 run_scoring 후 영속하고 run_id 반환(커밋은 호출자).

    call_fn이 None이면 run_scoring이 실 LLM(call_structured)을 쓴다. 테스트/무키 경로는
    fake를 주입한다(M2 §5: OPENAI_API_KEY 없으면 fixture/캐시 경로).
    """
    resume = config.load_seed_resume()
    resume_id = _ensure_seed_resume(conn, resume)
    jobs = persistence.load_jobs(conn)
    result = run_scoring(
        resume=resume,
        jobs=jobs,
        ranking_mode=ranking_mode,
        structured_call_fn=structured_call_fn,
        listwise_call_fn=listwise_call_fn,
        pairwise_call_fn=pairwise_call_fn,
    )
    return persistence.persist_run(
        conn, resume_id, jobs, result, ranking_mode=ranking_mode
    )


def main() -> None:
    """`python -m worker` — DB 연결 → run → commit → run_id 출력."""
    conn = db.connect()
    try:
        run_id = run(conn)
        conn.commit()
        print(f"ranking_run persisted: id={run_id}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
