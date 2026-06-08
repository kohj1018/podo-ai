"""worker/coarse_materialize.py — 후보 밖 공고 coarse projection (T-065, ADR-108 D3).

후보 밖 공고를 coarse_candidates에 (job_posting_id, resume_id, user_id, similarity_rank,
cache_key_version) 로 upsert한다. **fit_level 없음** — 유사도 rank만(피드 coarse 섹션은
배지 없이 유사도순 노출). 벡터 쿼리는 worker 전용(api는 read-only 서빙만, ADR-108 D3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import psycopg


def materialize_coarse(
    conn: psycopg.Connection[tuple[Any, ...]],
    *,
    non_candidates: list[str],
    resume_embedding: list[float],
    resume_id: int,
    user_id: str | None = None,
    cache_key_version: str = "",
) -> int:
    """후보 밖 공고를 coarse_candidates에 upsert(resume_id 범위). 처리 건수 반환.

    이전 coarse(같은 resume_id)는 삭제 후 재생성 — 이력서 교체·재채점 시 stale 차단
    (M5-repair-38). similarity_rank = 1 - cosine_distance(resume_embedding↔JD 임베딩).
    """
    ids_int = [int(j) for j in non_candidates if str(j).isdigit()]
    with conn.cursor() as cur:
        # 현재 run 범위(resume_id)의 이전 coarse 삭제 — stale 혼입 차단
        cur.execute("DELETE FROM coarse_candidates WHERE resume_id = %s", (resume_id,))
        if not ids_int or not resume_embedding:
            return 0

        vec_str = "[" + ",".join(str(v) for v in resume_embedding) + "]"
        # 후보 밖 공고의 유사도(임베딩 있는 것만 — 없으면 rank 0.0)
        cur.execute(
            "SELECT job_posting_id, (1.0 - (embedding <=> %s::vector))::float "
            "FROM job_embeddings WHERE job_posting_id = ANY(%s)",
            (vec_str, ids_int),
        )
        sims = {int(r[0]): float(r[1]) for r in cur.fetchall()}

        for jid in ids_int:
            cur.execute(
                "INSERT INTO coarse_candidates "
                "(job_posting_id, resume_id, user_id, similarity_rank, "
                "cache_key_version) VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (job_posting_id, resume_id) DO UPDATE SET "
                "user_id = EXCLUDED.user_id, "
                "similarity_rank = EXCLUDED.similarity_rank, "
                "cache_key_version = EXCLUDED.cache_key_version, "
                "scored_at = now()",
                (jid, resume_id, user_id, sims.get(jid, 0.0), cache_key_version),
            )
    return len(ids_int)
