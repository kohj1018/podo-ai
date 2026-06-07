"""worker/embedding.py — JD·resume 임베딩 영속 (T-064, ADR-108 D6).

결정성(GS-1): 동일 embedding_version 행 존재 시 저장 벡터를 재사용한다.
OpenAI 임베딩은 호출마다 byte-identical이 아님(cosine 0.968~0.99999 변동 — §8 실측).
영속+재사용으로만 결정성 보장(ADR-108 D6).

DDL 경계: job_embeddings·resume_embeddings는 vector 타입 → Prisma 모델 아님.
DML(SELECT/UPSERT)은 Python psycopg raw SQL(ADR-108 D3 — worker 전용).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from openai import OpenAI

from worker.config import OPENAI_API_KEY

if TYPE_CHECKING:
    import psycopg

# 버전 상수 — 변경 시 전 임베딩 재생성 + cache_key_version bump 필요
EMBEDDING_VERSION = "v1-text-embedding-3-small-1536"
_EMBEDDING_MODEL = "text-embedding-3-small"

# 모듈 레벨 클라이언트 — patch 지점 (테스트에서 worker.embedding.openai_client로 교체)
openai_client: Any = OpenAI(api_key=OPENAI_API_KEY)


def _call_embed(text: str) -> list[float]:
    """OpenAI embeddings API 단건 호출 → 1536차원 float 벡터."""
    resp = openai_client.embeddings.create(
        model=_EMBEDDING_MODEL,
        input=[text],
        encoding_format="float",
    )
    return cast("list[float]", resp.data[0].embedding)


def embed_jd(
    conn: psycopg.Connection[tuple[Any, ...]],
    job_posting_id: int,
    jd_text: str,
) -> None:
    """JD 임베딩 영속. 동일 embedding_version 행 존재 시 API 미호출(skip).

    - 행 없음 또는 버전 불일치: API 1회 호출 → UPSERT
    - 동일 버전 존재: early return(저장 벡터 재사용 — GS-1 ADR-108 D6)
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT embedding_version FROM job_embeddings WHERE job_posting_id = %s",
            (job_posting_id,),
        )
        row = cur.fetchone()

    if row is not None and row[0] == EMBEDDING_VERSION:
        return  # 동일 버전 — 저장 벡터 재사용, API 호출 없음

    vector = _call_embed(jd_text)
    # pgvector upsert: vector는 list → str '[x,y,...]' 형식으로 변환
    vec_str = "[" + ",".join(str(v) for v in vector) + "]"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO job_embeddings "
            "(job_posting_id, embedding, embedding_version, model_id) "
            "VALUES (%s, %s::vector, %s, %s) "
            "ON CONFLICT (job_posting_id) DO UPDATE SET "
            "embedding = EXCLUDED.embedding, "
            "embedding_version = EXCLUDED.embedding_version, "
            "model_id = EXCLUDED.model_id, "
            "created_at = now()",
            (job_posting_id, vec_str, EMBEDDING_VERSION, _EMBEDDING_MODEL),
        )


def embed_resume(
    conn: psycopg.Connection[tuple[Any, ...]],
    resume_id: int,
    masked_content: str,
) -> None:
    """이력서 임베딩 영속. 동일 embedding_version 행 존재 시 API 미호출(skip).

    - 행 없음 또는 버전 불일치: API 1회 호출 → UPSERT
    - 동일 버전 존재: early return(저장 벡터 재사용 — GS-1 ADR-108 D6)
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT embedding_version FROM resume_embeddings WHERE resume_id = %s",
            (resume_id,),
        )
        row = cur.fetchone()

    if row is not None and row[0] == EMBEDDING_VERSION:
        return  # 동일 버전 — 저장 벡터 재사용, API 호출 없음

    vector = _call_embed(masked_content)
    vec_str = "[" + ",".join(str(v) for v in vector) + "]"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO resume_embeddings "
            "(resume_id, embedding, embedding_version, model_id) "
            "VALUES (%s, %s::vector, %s, %s) "
            "ON CONFLICT (resume_id) DO UPDATE SET "
            "embedding = EXCLUDED.embedding, "
            "embedding_version = EXCLUDED.embedding_version, "
            "model_id = EXCLUDED.model_id, "
            "created_at = now()",
            (resume_id, vec_str, EMBEDDING_VERSION, _EMBEDDING_MODEL),
        )
