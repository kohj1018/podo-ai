"""worker/scoring_runner.py — N→K 비용 구조 전환 래퍼 (T-065, ADR-108 D2~D4).

run_full_scoring(): 이력서 임베딩(영속·재사용) → 하이브리드 후보 K개 선별 →
run_scoring을 K개에만 호출(파이프라인 본체·캐시 키·recommendations 불변) →
후보 밖 공고는 coarse projection으로 materialize(fit_level 없음).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from worker.coarse_materialize import materialize_coarse
from worker.embedding import EMBEDDING_VERSION, embed_resume
from worker.pipeline import run_scoring
from worker.prefilter import DEFAULT_K_MAX, DEFAULT_K_V, select_candidates

if TYPE_CHECKING:
    import psycopg

    from core.models import Resume

# cache_key_version — 임베딩·후보선별·K 반영(변경 시 결정적 무효화, ADR-108 D6)
COARSE_CACHE_KEY_VERSION = (
    f"{EMBEDDING_VERSION}|prefilter-v1|kv{DEFAULT_K_V}|kmax{DEFAULT_K_MAX}"
)


def _parse_vector(vec_text: str) -> list[float]:
    """pgvector '[x,y,...]' 텍스트 → list[float]."""
    inner = vec_text.strip().strip("[]")
    if not inner:
        return []
    return [float(x) for x in inner.split(",")]


def _load_resume_embedding(
    conn: psycopg.Connection[tuple[Any, ...]], resume_id: int, masked_content: str
) -> list[float]:
    """이력서 임베딩 영속·재사용 후 벡터 로드(매 채점 재생성 금지 — GS-1, T-064)."""
    embed_resume(conn, resume_id, masked_content)  # 없으면 1회 생성, 있으면 skip
    with conn.cursor() as cur:
        cur.execute(
            "SELECT embedding::text FROM resume_embeddings "
            "WHERE resume_id = %s AND embedding_version = %s",
            (resume_id, EMBEDDING_VERSION),
        )
        row = cur.fetchone()
    return _parse_vector(str(row[0])) if row is not None and row[0] else []


def _load_resume_domains(
    conn: psycopg.Connection[tuple[Any, ...]], resume_id: int
) -> list[str]:
    """resume_domains(T-066)에서 primary+secondary 도메인 로드(도메인 매칭 입력)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT primary_domains, secondary_domains FROM resume_domains "
            "WHERE resume_id = %s",
            (resume_id,),
        )
        row = cur.fetchone()
    if row is None:
        return []
    return list(row[0] or []) + list(row[1] or [])


def run_full_scoring(
    conn: psycopg.Connection[tuple[Any, ...]],
    resume: Resume,
    resume_id: int,
    all_jobs: list[dict[str, Any]],
    *,
    user_id: str | None = None,
    ranking_mode: str = "domain_fit_bt",
    structured_call_fn: Callable[..., Any] | None = None,
    listwise_call_fn: Callable[..., str] | None = None,
    pairwise_call_fn: Callable[..., str] | None = None,
    K_v: int = DEFAULT_K_V,
    K_max: int = DEFAULT_K_MAX,
) -> dict[str, Any]:
    """N개 JD 중 후보 K개에만 deep 분석, 후보 밖은 coarse materialize(ADR-108 D2~D4).

    1. 이력서 임베딩 영속·재사용(GS-1).
    2. 하이브리드 후보 선별(벡터∪도메인∪스킬, K_max cap).
    3. run_scoring을 K개에만 호출(파이프라인 본체·캐시 키·recommendations 불변).
    4. 후보 밖 → coarse_candidates materialize(fit_level 없음, 유사도 rank).
    """
    embedding = _load_resume_embedding(conn, resume_id, resume.raw_text)
    resume_domains = _load_resume_domains(conn, resume_id)

    cset = select_candidates(
        conn, embedding, all_jobs, resume_domains, K_v=K_v, K_max=K_max
    )
    candidate_ids = set(cset.candidates)
    candidate_jobs = [j for j in all_jobs if j["job_id"] in candidate_ids]

    # 핵심 비용 레버: run_scoring(step1~12)을 K개에만 호출 — 본체 불변(ADR-108 D4)
    result = run_scoring(
        resume=resume,
        jobs=candidate_jobs,
        ranking_mode=ranking_mode,
        structured_call_fn=structured_call_fn,
        listwise_call_fn=listwise_call_fn,
        pairwise_call_fn=pairwise_call_fn,
    )

    # 후보 밖 공고 → coarse projection(fit_level 없음 — Guardrail 1, ADR-108 D3)
    materialize_coarse(
        conn,
        non_candidates=cset.non_candidates,
        resume_embedding=embedding,
        resume_id=resume_id,
        user_id=user_id,
        cache_key_version=COARSE_CACHE_KEY_VERSION,
    )

    return result
