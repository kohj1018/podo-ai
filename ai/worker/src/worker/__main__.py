"""worker 실행 진입점 — `python -m worker` (T-023, M2 score 단계).

seed(합성) 이력서 + DB job_postings → run_scoring → persist_run(T-022).
seed 이력서는 config.load_seed_resume()로 주입(SPEC §9-4, 실 PII 비범위).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Callable

import psycopg

from core import db
from core.models import Resume
from worker import config, persistence
from worker.embed_batch import embed_new_jobs
from worker.scoring_runner import run_full_scoring

logger = logging.getLogger(__name__)

# in-process 재시도 한도 — 초과 시 status=failed (무한 재시도 종료, T-045 AC-4).
MAX_RETRIES = 3


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
    resume_id: int | None = None,
    ranking_mode: str = persistence.DEFAULT_RANKING_MODE,
    structured_call_fn: Callable[..., Any] | None = None,
    listwise_call_fn: Callable[..., str] | None = None,
    pairwise_call_fn: Callable[..., str] | None = None,
) -> int:
    """이력서 + DB jobs로 run_scoring 후 영속하고 run_id 반환(커밋은 호출자).

    resume_id가 주어지면 DB의 (업로드·마스킹) 이력서를 채점한다(M3 업로드 경로).
    None이면 기존 seed 경로(M2 무키 E2E `python -m worker` 보존).
    call_fn이 None이면 run_scoring이 실 LLM(call_structured)을 쓴다. 테스트/무키 경로는
    fake를 주입한다(M2 §5: OPENAI_API_KEY 없으면 fixture/캐시 경로).
    """
    if resume_id is not None:
        resume = persistence.load_resume(conn, resume_id)
        rid = resume_id
    else:
        resume = config.load_seed_resume()
        rid = _ensure_seed_resume(conn, resume)
    jobs = persistence.load_jobs(conn)
    # T-064: 신규 JD 임베딩 적재(무키/실패 시 skip — prefilter는 N-path 폴백).
    try:
        embed_new_jobs(conn)
    except Exception as exc:  # 시스템 경계(OpenAI/DB) — 무키/실패 시 임베딩 없이 진행
        logger.warning("embed_new_jobs_skip error=%s", exc)
    # T-065: N→K 후보 선별 — 임베딩 있으면 K개만 deep(절감), 없으면 N-path 폴백.
    result = run_full_scoring(
        conn,
        resume,
        rid,
        jobs,
        ranking_mode=ranking_mode,
        structured_call_fn=structured_call_fn,
        listwise_call_fn=listwise_call_fn,
        pairwise_call_fn=pairwise_call_fn,
    )
    return persistence.persist_run(conn, rid, jobs, result, ranking_mode=ranking_mode)


def _parse_resume_id() -> int | None:
    """`--resume-id N` argv 또는 `RESUME_ID` env에서 채점 대상 이력서 id를 읽는다."""
    argv = sys.argv[1:]
    if "--resume-id" in argv:
        i = argv.index("--resume-id")
        if i + 1 < len(argv):
            return int(argv[i + 1])
    env = os.environ.get("RESUME_ID")
    return int(env) if env else None


# ---------------------------------------------------------------------------
# SQS consumer (ADR-106) — subprocess 일회성 실행을 큐 소비 상시 서비스로 전환 (T-045)
# ---------------------------------------------------------------------------


def _emit_status(
    sqs: Any, status_queue_url: str | None, job_id: str, status: str
) -> None:
    """worker→api 작업 상태 이벤트(running/done/failed)를 상태 큐에 전송한다.

    scoring_jobs는 api 단일 writer(ARCH §3-2)라 worker는 직접 write하지 않고
    큐로 신호만 보낸다. status_queue_url이 없으면 no-op(상태 신호 비활성 — 로컬 디버그).
    """
    if not status_queue_url:
        return
    sqs.send_message(
        QueueUrl=status_queue_url,
        MessageBody=json.dumps({"job_id": job_id, "status": status}),
    )


def process_message(
    conn: psycopg.Connection[tuple[Any, ...]],
    payload: dict[str, Any],
    sqs: Any,
    status_queue_url: str | None,
    *,
    max_retries: int = MAX_RETRIES,
    structured_call_fn: Callable[..., Any] | None = None,
    listwise_call_fn: Callable[..., str] | None = None,
    pairwise_call_fn: Callable[..., str] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> str:
    """메시지 1건 처리: running 신호 → run_scoring+persist → done 신호.

    예외 시 rollback 후 backoff 재시도. 한도(max_retries) 초과 시 failed 신호 + 종료.
    결정론·캐시 키·held는 run()/persist_run 불변(SPEC SSOT). 반환: 최종 status.
    """
    resume_id = int(payload["resume_id"])
    job_id = str(payload["job_id"])
    _emit_status(sqs, status_queue_url, job_id, "running")

    attempt = 0
    while True:
        try:
            run(
                conn,
                resume_id=resume_id,
                structured_call_fn=structured_call_fn,
                listwise_call_fn=listwise_call_fn,
                pairwise_call_fn=pairwise_call_fn,
            )
            conn.commit()
            _emit_status(sqs, status_queue_url, job_id, "done")
            return "done"
        except Exception as exc:
            # 채점 실패 원인을 삼키지 않고 기록(3회 무성 재시도 관측 불가 결함 제거).
            logger.warning(
                "scoring_attempt_failed job_id=%s attempt=%s error=%r",
                job_id,
                attempt + 1,
                exc,
            )
            conn.rollback()
            attempt += 1
            if attempt >= max_retries:
                _emit_status(sqs, status_queue_url, job_id, "failed")
                return "failed"
            sleep_fn(min(2.0**attempt, 10.0))  # 지수 backoff(상한 10s)


def consume_once(
    conn: psycopg.Connection[tuple[Any, ...]],
    sqs: Any,
    queue_url: str,
    status_queue_url: str | None,
    *,
    wait_seconds: int = 20,
    process_kwargs: dict[str, Any] | None = None,
) -> int:
    """큐 메시지 수신(long-poll)→처리→삭제. 처리한 메시지 수 반환(루프/테스트)."""
    resp = sqs.receive_message(
        QueueUrl=queue_url, WaitTimeSeconds=wait_seconds, MaxNumberOfMessages=1
    )
    msgs = resp.get("Messages", [])
    for msg in msgs:
        payload = json.loads(msg["Body"])  # { resume_id, job_id }
        process_message(conn, payload, sqs, status_queue_url, **(process_kwargs or {}))
        # 멱등 처리 후 삭제(중복 수신해도 복합 unique upsert로 1행, GS-1-through-queue).
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
    return len(msgs)


def _make_sqs_client() -> Any:
    import boto3

    endpoint = os.environ.get("SQS_ENDPOINT_URL")
    return boto3.client(
        "sqs",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        **({"endpoint_url": endpoint} if endpoint else {}),
    )


def consume_loop() -> None:  # pragma: no cover (상시 루프 — E2E가 실증)
    """SQS long-poll 상시 consumer 루프 — `python -m worker`(인자 없음)의 기본 동작."""
    queue_url = os.environ["SQS_QUEUE_URL"]
    status_queue_url = os.environ.get("SQS_STATUS_QUEUE_URL")
    sqs = _make_sqs_client()
    conn = db.connect()
    try:
        while True:
            consume_once(conn, sqs, queue_url, status_queue_url)
    finally:
        conn.close()


def main() -> None:
    """`python -m worker` — SQS consumer 상시 루프(ADR-106).

    전환기 호환: `--resume-id N`이 명시되면 1회 실행(seed/디버그 경로)으로 동작한다.
    """
    resume_id = _parse_resume_id()
    if resume_id is not None:
        conn = db.connect()
        try:
            run_id = run(conn, resume_id=resume_id)
            conn.commit()
            print(f"ranking_run persisted: id={run_id}")
        finally:
            conn.close()
        return
    consume_loop()


if __name__ == "__main__":
    main()
