"""worker SQS consumer (T-045) — 큐 소비 → run_scoring/persist → 상태 신호.

AC-1/2/3은 DB(podo_test) 필요(skipIf). AC-4(재시도 한도→failed)는 fake conn으로 DB 없이.
LLM은 fake 주입(무키, M2/M3 패턴). SQS는 FakeSQS로 주입(LocalStack 불요 — 단위).
실 LocalStack 왕복은 E2E(T-052)가 실증.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any, Callable

import psycopg
import pytest

from core import db
from worker.__main__ import consume_once, process_message

_QUOTE = "React 18 프로젝트에서 3년간 프론트엔드 개발"
_MASKED_RESUME = (
    f"이름: [MASKED_NAME]\n## Skills\n- React, TypeScript\n## 경력\n- {_QUOTE}\n"
)


# --- FakeSQS: receive/send/delete 캡처 (LocalStack 없이 consumer 로직 단위검증) ---
class FakeSQS:
    def __init__(self, messages: list[dict[str, str]]) -> None:
        self._messages = list(messages)
        self.sent: list[dict[str, str]] = []  # 상태 이벤트 캡처
        self.deleted: list[str] = []

    def receive_message(self, **_kw: Any) -> dict[str, Any]:
        if self._messages:
            return {"Messages": [self._messages.pop(0)]}
        return {}

    def send_message(self, QueueUrl: str, MessageBody: str) -> None:  # noqa: N803
        self.sent.append(json.loads(MessageBody))

    def delete_message(self, QueueUrl: str, ReceiptHandle: str) -> None:  # noqa: N803
        self.deleted.append(ReceiptHandle)


# --- LLM fakes (test_entry.py와 동형) ---
def _structured_fake(fail_marker: str | None = None) -> Callable[..., Any]:
    evidence_resp = {
        "evidence": [
            {
                "evidence_id": "E1",
                "title": "Experience",
                "source_section": "Experience",
                "exact_quote": _QUOTE,
                "normalized_summary": "React 3년",
            }
        ]
    }
    req = {
        "requirement_id": "R1",
        "requirement_text": "React 개발 경험",
        "requirement_type": "required",
        "requirement_nature": "technical",
        "prerequisite_status": "prerequisite",
    }
    match_resp = {
        "matches": [
            {
                "requirement_id": "R1",
                "requirement_type": "required",
                "matched_evidence_ids": ["E1"],
                "match_level": "direct",
                "confidence": "high",
                "explanation": "React 직접 매칭",
                "risk_note": "",
            }
        ]
    }

    def fn(
        system: str,
        user: str,
        validate: Callable[[dict[str, Any]], dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.0,
        cache_label: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        from worker.pipeline import LLMCallError

        if fail_marker is not None and fail_marker in user:
            raise LLMCallError("injected per-job failure")
        role_family = "frontend" if "Frontend" in user else "backend"
        jd_resp = {
            "requirements": [req],
            "preferred_requirements": [],
            "role_family": role_family,
        }
        for resp in (evidence_resp, jd_resp, match_resp, {"verified": []}):
            try:
                return validate(resp)
            except Exception:
                continue
        raise AssertionError("fake에 매칭되는 응답 없음")

    return fn


def _listwise_fake(job_ids: list[int]) -> Callable[..., str]:
    ranking = [{"job_id": str(j), "reason": "r"} for j in job_ids]

    def _call(system: str, user: str, max_tokens: int, temperature: float) -> str:
        return json.dumps({"ranking": ranking, "uncertainty_notes": ""})

    return _call


def _pairwise_fake() -> Callable[..., str]:
    def _call(system: str, user: str, max_tokens: int, temperature: float) -> str:
        return json.dumps({"winner": "a", "confidence": "high", "reason": "t"})

    return _call


def _seed(
    conn: psycopg.Connection[tuple[Any, ...]], *, fail_be: bool = False
) -> tuple[int, list[int]]:
    """masked resume 1건 + Frontend/Backend job 2건 삽입(commit) → (resume_id, [job_ids])."""
    be_raw = "백엔드 __FAIL__ 채용 공고" if fail_be else "백엔드 채용 공고"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO resumes (content, masked, source, upload_format) "
            "VALUES (%s, true, 'upload', 'txt') RETURNING id",
            (_MASKED_RESUME,),
        )
        rrow = cur.fetchone()
        assert rrow is not None
        rid = int(rrow[0])
        ids: list[int] = []
        for src, company, title, raw in (
            ("toss", "Toss", "Frontend Engineer", "프론트엔드 채용 공고"),
            ("kakao", "Kakao", "Backend Engineer", be_raw),
        ):
            cur.execute(
                "INSERT INTO job_postings (source, company, title, url, raw_text) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (src, company, title, f"https://t045.test/{title}", raw),
            )
            r = cur.fetchone()
            assert r is not None
            ids.append(int(r[0]))
    conn.commit()
    return rid, ids


def _cleanup(
    conn: psycopg.Connection[tuple[Any, ...]], resume_id: int, job_ids: list[int]
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM recommendations WHERE run_id IN "
            "(SELECT id FROM ranking_runs WHERE resume_id = %s)",
            (resume_id,),
        )
        cur.execute("DELETE FROM ranking_runs WHERE resume_id = %s", (resume_id,))
        cur.execute("DELETE FROM job_postings WHERE id = ANY(%s)", (job_ids,))
        cur.execute("DELETE FROM resumes WHERE id = %s", (resume_id,))
    conn.commit()


_HAS_DB = bool(os.environ.get("DATABASE_URL"))


@pytest.fixture
def conn() -> Iterator[psycopg.Connection[tuple[Any, ...]]]:
    c = db.connect()
    try:
        yield c
    finally:
        c.close()


def _kwargs(job_ids: list[int], fail_marker: str | None = None) -> dict[str, Any]:
    return {
        "structured_call_fn": _structured_fake(fail_marker),
        "listwise_call_fn": _listwise_fake(job_ids),
        "pairwise_call_fn": _pairwise_fake(),
        "sleep_fn": lambda _s: None,
    }


@pytest.mark.skipif(not _HAS_DB, reason="requires migrated DATABASE_URL (podo_test)")
def test_AC_1_consume_message_creates_ranking_run_and_job_done(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """큐 메시지 소비 → ranking_run+recommendations 생성 + 'done' 상태 신호 전송."""
    rid, job_ids = _seed(conn)
    try:
        sqs = FakeSQS(
            [
                {
                    "Body": json.dumps({"resume_id": rid, "job_id": "job-1"}),
                    "ReceiptHandle": "rh1",
                }
            ]
        )
        n = consume_once(
            conn, sqs, "q", "statusq", wait_seconds=0, process_kwargs=_kwargs(job_ids)
        )
        assert n == 1
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM ranking_runs WHERE resume_id = %s", (rid,)
            )
            rr = cur.fetchone()
            assert rr is not None and rr[0] == 1
            cur.execute(
                "SELECT count(*) FROM recommendations WHERE run_id IN "
                "(SELECT id FROM ranking_runs WHERE resume_id = %s)",
                (rid,),
            )
            rec = cur.fetchone()
            assert rec is not None and rec[0] >= 1
        # 상태 신호: running → done. 작업은 done(api가 이 신호로 scoring_jobs.status 갱신)
        statuses = [s["status"] for s in sqs.sent if s["job_id"] == "job-1"]
        assert statuses == ["running", "done"]
        assert sqs.deleted == ["rh1"]  # 처리 후 메시지 삭제
    finally:
        _cleanup(conn, rid, job_ids)


@pytest.mark.skipif(not _HAS_DB, reason="requires migrated DATABASE_URL (podo_test)")
def test_AC_2_idempotent_two_consumes_one_row_gs1_through_queue(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """동일 (resume, jobs) 2회 소비 → ranking_runs 1행(복합 unique upsert) + result 동일."""
    rid, job_ids = _seed(conn)
    try:
        for rh in ("rh1", "rh2"):
            sqs = FakeSQS(
                [
                    {
                        "Body": json.dumps({"resume_id": rid, "job_id": "job-1"}),
                        "ReceiptHandle": rh,
                    }
                ]
            )
            consume_once(
                conn,
                sqs,
                "q",
                "statusq",
                wait_seconds=0,
                process_kwargs=_kwargs(job_ids),
            )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*), max(result::text) FROM ranking_runs WHERE resume_id = %s",
                (rid,),
            )
            row = cur.fetchone()
        assert row is not None and row[0] == 1  # 멱등 — 1행만(GS-1-through-queue)
    finally:
        _cleanup(conn, rid, job_ids)


@pytest.mark.skipif(not _HAS_DB, reason="requires migrated DATABASE_URL (podo_test)")
def test_AC_3_held_jobs_done_no_fake_score(
    conn: psycopg.Connection[tuple[Any, ...]],
) -> None:
    """LLM miss 공고 → recommendations.status='held'(fit_level NULL) + 작업은 done(가짜 점수 0)."""
    rid, job_ids = _seed(conn, fail_be=True)
    try:
        sqs = FakeSQS(
            [
                {
                    "Body": json.dumps({"resume_id": rid, "job_id": "job-1"}),
                    "ReceiptHandle": "rh1",
                }
            ]
        )
        consume_once(
            conn,
            sqs,
            "q",
            "statusq",
            wait_seconds=0,
            process_kwargs=_kwargs(job_ids, fail_marker="__FAIL__"),
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT job_posting_id, fit_level FROM recommendations WHERE status = 'held' "
                "AND run_id IN (SELECT id FROM ranking_runs WHERE resume_id = %s)",
                (rid,),
            )
            held = cur.fetchall()
        assert len(held) == 1 and held[0][0] == job_ids[1] and held[0][1] is None
        # 작업 자체는 done(held는 공고 레벨, 작업 실패 아님)
        statuses = [s["status"] for s in sqs.sent if s["job_id"] == "job-1"]
        assert statuses[-1] == "done" and "failed" not in statuses
    finally:
        _cleanup(conn, rid, job_ids)


def test_AC_4_failed_status_after_retry_limit() -> None:
    """worker 처리가 재시도 한도(3) 초과 → 'failed' 신호 + 종료(무한 재시도 X). DB 불요(fake conn)."""

    class _FailConn:
        """run()이 load_resume에서 ValueError(미존재) → 처리 실패 유도."""

        class _Cur:
            def __enter__(self) -> Any:
                return self

            def __exit__(self, *a: Any) -> bool:
                return False

            def execute(self, *a: Any, **k: Any) -> None:
                pass

            def fetchone(self) -> None:
                return None

        def cursor(self) -> Any:
            return self._Cur()

        def rollback(self) -> None:
            pass

        def commit(self) -> None:
            pass

    sqs = FakeSQS([])
    slept: list[float] = []
    status = process_message(
        _FailConn(),  # type: ignore[arg-type]
        {"resume_id": 999999, "job_id": "job-x"},
        sqs,
        "statusq",
        max_retries=3,
        sleep_fn=lambda s: slept.append(s),
    )
    assert status == "failed"
    statuses = [s["status"] for s in sqs.sent if s["job_id"] == "job-x"]
    assert statuses == ["running", "failed"]  # running 후 한도 초과 failed
    assert len(slept) == 2  # 3회 시도 사이 backoff 2회(무한 재시도 아님)
