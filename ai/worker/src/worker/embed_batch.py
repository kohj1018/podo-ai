"""worker/embed_batch.py — 신규 JD 배치 임베딩 (T-064, ADR-108 D5/D6).

embed_new_jobs(): job_postings LEFT JOIN job_embeddings로 임베딩 없는 JD 조회 →
embed_jd() 순차 호출 → 처리 건수 반환.

per-JD 단건 증분 트리거는 비범위(ADR-108 D5 후속).
배치는 현재 단건 루프 — 대량 초기적재 시 Batch API 전환(§8 메모).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from worker.embedding import embed_jd

if TYPE_CHECKING:
    import psycopg

# OpenAI 호출은 embed_jd → worker.embedding.openai_client 경유(단일 클라이언트).
# 테스트는 worker.embedding.openai_client를 patch한다.


def embed_new_jobs(conn: psycopg.Connection[tuple[Any, ...]]) -> int:
    """job_embeddings에 없는 신규 JD를 임베딩·영속, 처리 건수를 반환.

    LEFT JOIN으로 임베딩 미존재 JD만 선별 — 이미 처리된 JD는 건너뜀(증분 안전).
    embed_jd() 내부에서 version-match skip이 재차 수행(이중 방어).
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT jp.id, jp.raw_text "
            "FROM job_postings jp "
            "LEFT JOIN job_embeddings je ON jp.id = je.job_posting_id "
            "WHERE je.job_posting_id IS NULL "
            "ORDER BY jp.id"
        )
        rows = cur.fetchall()

    count = 0
    for row in rows:
        job_id = int(row[0])
        raw_text = str(row[1])
        embed_jd(conn, job_posting_id=job_id, jd_text=raw_text)
        count += 1

    return count
