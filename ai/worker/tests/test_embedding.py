"""T-064 embedding worker 테스트 — AC-1~AC-4 (TDD Red → Green).

DATABASE_URL 없으면 DB-의존 테스트 skip(로컬 게이트).
OpenAI API는 mock으로 대체 — 네트워크 호출 0.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """OpenAI embeddings.create 응답을 mock."""
    client = MagicMock()
    embedding_data = MagicMock()
    embedding_data.embedding = [0.1] * 1536
    response = MagicMock()
    response.data = [embedding_data]
    response.model = "text-embedding-3-small"
    client.embeddings.create.return_value = response
    return client


@pytest.fixture
def db_conn() -> Any:
    """psycopg connection — DATABASE_URL 필수."""
    from core import db

    conn = db.connect()
    try:
        yield conn
        conn.rollback()
    finally:
        conn.close()


def _seed_job(cur: Any) -> int:
    """job_postings에 테스트용 JD 1건 삽입, job_posting_id 반환."""
    cur.execute(
        "INSERT INTO job_postings (source, company, title, url, raw_text) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (
            "test_src",
            "TestCo",
            "Engineer",
            "https://test.example/job-embed-1",
            "JD 텍스트",
        ),
    )
    row = cur.fetchone()
    assert row is not None
    return int(row[0])


def _seed_resume(cur: Any) -> int:
    """resumes에 테스트용 이력서 1건 삽입, resume_id 반환."""
    cur.execute(
        "INSERT INTO resumes (content) VALUES (%s) RETURNING id",
        ("이력서 내용 마스킹본",),
    )
    row = cur.fetchone()
    assert row is not None
    return int(row[0])


# ---------------------------------------------------------------------------
# AC-1: 신규 JD → embed_new_jobs → job_embeddings 영속
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires migrated DATABASE_URL",
)
def test_AC_1_new_job_embedded_and_persisted(
    db_conn: Any, mock_openai_client: MagicMock
) -> None:
    """AC-1: job_postings에 JD 존재 + job_embeddings 행 없을 때 embed_new_jobs() 실행 →
    해당 JD가 embedding_version 포함 upsert된다."""
    from worker.embed_batch import embed_new_jobs
    from worker.embedding import EMBEDDING_VERSION

    with db_conn.cursor() as cur:
        job_id = _seed_job(cur)

    with patch("worker.embedding.openai_client", mock_openai_client):
        count = embed_new_jobs(db_conn)

    assert count >= 1, "embed_new_jobs()가 최소 1건 처리해야 한다"

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT embedding_version FROM job_embeddings WHERE job_posting_id = %s",
            (job_id,),
        )
        row = cur.fetchone()

    assert row is not None, "job_embeddings에 행이 없음 — upsert 실패"
    assert row[0] == EMBEDDING_VERSION, f"embedding_version 불일치: {row[0]!r}"


# ---------------------------------------------------------------------------
# 배치 임베딩 — N건을 ceil(N/batch) API 호출로(직렬 N회 아님). DB 불필요(fake_conn).
# ---------------------------------------------------------------------------


def _batch_client() -> MagicMock:
    """embeddings.create가 input 길이만큼 벡터를 1회로 반환(배치 mock)."""
    client = MagicMock()

    def _create(**kwargs: Any) -> MagicMock:
        texts = kwargs["input"]
        resp = MagicMock()
        resp.data = [MagicMock(embedding=[0.1] * 1536) for _ in texts]
        return resp

    client.embeddings.create.side_effect = _create
    return client


def _fake_conn() -> tuple[MagicMock, MagicMock]:
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn, cur


def test_embed_jds_batch_one_call_per_chunk() -> None:
    """5건 + batch_size 기본 → API 1회(직렬 5회 아님) + 5건 upsert."""
    from worker.embedding import embed_jds_batch

    client = _batch_client()
    conn, cur = _fake_conn()
    items = [(i, f"JD {i}") for i in range(5)]

    with patch("worker.embedding.openai_client", client):
        count = embed_jds_batch(conn, items)

    assert count == 5
    assert client.embeddings.create.call_count == 1, "5건이 1 API 호출로 배치돼야 함"
    assert cur.execute.call_count == 5, "5건 upsert"


def test_embed_jds_batch_chunks_by_batch_size() -> None:
    """5건 + batch_size=2 → ceil(5/2)=3 API 호출."""
    from worker.embedding import embed_jds_batch

    client = _batch_client()
    conn, _cur = _fake_conn()
    items = [(i, f"JD {i}") for i in range(5)]

    with patch("worker.embedding.openai_client", client):
        count = embed_jds_batch(conn, items, batch_size=2)

    assert count == 5
    assert client.embeddings.create.call_count == 3


# ---------------------------------------------------------------------------
# AC-2: 동일 job_posting_id + 동일 embedding_version → API 0회 호출(skip)
# ---------------------------------------------------------------------------


def test_AC_2_no_reembed_when_version_matches(mock_openai_client: MagicMock) -> None:
    """AC-2: job_embeddings에 동일 job_posting_id·embedding_version 행 존재 →
    embed_jd() 재호출 시 API를 호출하지 않고 early return한다."""
    from worker.embedding import EMBEDDING_VERSION, embed_jd

    fake_conn = MagicMock()
    # DB SELECT: 동일 버전 행이 이미 존재하는 상황 mock
    mock_cur = MagicMock()
    mock_cur.__enter__ = MagicMock(return_value=mock_cur)
    mock_cur.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = (EMBEDDING_VERSION,)
    fake_conn.cursor.return_value = mock_cur

    with patch("worker.embedding.openai_client", mock_openai_client):
        embed_jd(fake_conn, job_posting_id=1, jd_text="이미 임베딩된 JD")

    mock_openai_client.embeddings.create.assert_not_called()


# ---------------------------------------------------------------------------
# AC-3: embedding_version 불일치(구버전 행) → API 1회 호출 + upsert
# ---------------------------------------------------------------------------


def test_AC_3_reembed_on_version_mismatch(mock_openai_client: MagicMock) -> None:
    """AC-3: job_embeddings에 구버전 행 존재(version 불일치) →
    embed_jd() 호출 시 신버전으로 upsert하고 API를 1회 호출한다."""
    from worker.embedding import embed_jd

    fake_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.__enter__ = MagicMock(return_value=mock_cur)
    mock_cur.__exit__ = MagicMock(return_value=False)
    # DB SELECT: 구버전 행 존재
    mock_cur.fetchone.return_value = ("v0-old-version",)
    fake_conn.cursor.return_value = mock_cur

    with patch("worker.embedding.openai_client", mock_openai_client):
        embed_jd(fake_conn, job_posting_id=2, jd_text="버전 바뀐 JD")

    mock_openai_client.embeddings.create.assert_called_once()
    # upsert execute 호출 확인 (execute 2회: SELECT + UPSERT)
    assert mock_cur.execute.call_count == 2, (
        f"execute 호출 수 불일치: {mock_cur.execute.call_count}"
    )


# ---------------------------------------------------------------------------
# AC-4: resume embed_resume — 최초 1회 API 호출·영속, 재호출은 skip
# ---------------------------------------------------------------------------


def test_AC_4_resume_embedding_persisted_and_reused(
    mock_openai_client: MagicMock,
) -> None:
    """AC-4: masked 이력서 embed_resume() 1회 호출 → API 1회 + 영속.
    동일 resume_id·embedding_version 재호출 → API 0회(저장 벡터 재사용)."""
    from worker.embedding import EMBEDDING_VERSION, embed_resume

    # ── 1차 호출: 행 없음(None) → API 호출 + upsert ─────────────────────────
    fake_conn_first = MagicMock()
    mock_cur_first = MagicMock()
    mock_cur_first.__enter__ = MagicMock(return_value=mock_cur_first)
    mock_cur_first.__exit__ = MagicMock(return_value=False)
    mock_cur_first.fetchone.return_value = None  # 행 없음
    fake_conn_first.cursor.return_value = mock_cur_first

    with patch("worker.embedding.openai_client", mock_openai_client):
        embed_resume(fake_conn_first, resume_id=10, masked_content="이력서 마스킹 내용")

    mock_openai_client.embeddings.create.assert_called_once()

    # ── 2차 호출: 동일 버전 행 존재 → API skip ──────────────────────────────
    mock_openai_client.reset_mock()
    fake_conn_second = MagicMock()
    mock_cur_second = MagicMock()
    mock_cur_second.__enter__ = MagicMock(return_value=mock_cur_second)
    mock_cur_second.__exit__ = MagicMock(return_value=False)
    mock_cur_second.fetchone.return_value = (EMBEDDING_VERSION,)  # 동일 버전 존재
    fake_conn_second.cursor.return_value = mock_cur_second

    with patch("worker.embedding.openai_client", mock_openai_client):
        embed_resume(
            fake_conn_second, resume_id=10, masked_content="이력서 마스킹 내용"
        )

    mock_openai_client.embeddings.create.assert_not_called()
