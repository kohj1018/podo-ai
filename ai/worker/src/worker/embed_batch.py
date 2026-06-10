"""worker/embed_batch.py — 신규 JD 배치 임베딩 (T-064, ADR-108 D5/D6).

embed_new_jobs(): job_postings LEFT JOIN job_embeddings로 임베딩 없는 JD 조회 →
embed_jds_batch()로 *배치* 임베딩(OpenAI input 배열, N→ceil(N/batch) 호출).

per-JD 단건 증분 트리거는 비범위(ADR-108 D5 후속).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from worker.embedding import embed_jds_batch

if TYPE_CHECKING:
    import psycopg

# OpenAI 호출은 embed_jds_batch → worker.embedding.openai_client 경유(단일 클라이언트).
# 테스트는 worker.embedding.openai_client를 patch한다.


def embed_new_jobs(conn: psycopg.Connection[tuple[Any, ...]]) -> int:
    """job_embeddings에 없는 신규 JD를 *배치* 임베딩·영속, 처리 건수를 반환.

    LEFT JOIN으로 임베딩 미존재 JD만 선별 — 이미 처리된 JD는 건너뜀(증분 안전).
    선별분을 embed_jds_batch에 넘겨 배치 입력 1회로 다건 임베딩(직렬 N호출 → 배치).
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

    items = [(int(row[0]), str(row[1])) for row in rows]
    return embed_jds_batch(conn, items)


def main() -> None:
    """`python -m worker.embed_batch` — 미임베딩 JD를 일괄 임베딩·영속 후 커밋.

    크롤 직후 호출 — 임베딩을 수집 시점에 미리 생성(채점 경로 부담↓).
    OPENAI_API_KEY 필요. 미임베딩 JD 없으면 0(증분, LEFT JOIN skip).
    """
    from core import db

    conn = db.connect()
    try:
        count = embed_new_jobs(conn)
        conn.commit()
    finally:
        conn.close()
    print(f"[embed] new_jobs_embedded={count}")


if __name__ == "__main__":
    main()
