"""worker/prefilter.py — 하이브리드 후보 선별 (T-065, ADR-108 D2).

select_candidates(): 벡터 top-K_v ∪ 도메인/role_family ∪ 스킬/키워드 합집합으로
K_max개 후보를 결정적으로(GS-1) 선별한다.

tie-break 규칙: 유사도 desc → job_id asc (ADR-108 D2 결정성 요건).
스킬 매칭: job_postings.raw_text 키워드 기반(tech_stack 컬럼 없음 — §8 확정).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import psycopg

# 기본 파라미터 (ADR-108 D2 — F-023 recall 측정 후 조정)
DEFAULT_K_V: int = 50
DEFAULT_K_MAX: int = 80


@dataclass
class CandidateSet:
    """select_candidates 반환 컨테이너.

    candidates: 결정적 순서(유사도 desc / job_id asc)의 후보 job_id 리스트.
    similarity_map: job_id → 코사인 유사도(벡터 후보에 속한 것만, 나머지 0.0).
    non_candidates: 후보 밖 job_id 리스트(coarse_materialize 입력).
    """

    candidates: list[str] = field(default_factory=list)
    similarity_map: dict[str, float] = field(default_factory=dict)
    non_candidates: list[str] = field(default_factory=list)


def _fetch_vector_top_k(
    conn: psycopg.Connection[tuple[Any, ...]],
    resume_embedding: list[float],
    K_v: int,
) -> list[tuple[str, float]]:
    """pgvector HNSW ANN 쿼리 — top-K_v (job_id str, similarity float) 반환.

    ADR-108 D3: 벡터 검색은 worker 전용.
    유사도 = 1 - cosine_distance(<=> 연산자 반환값).
    """
    vec_str = "[" + ",".join(str(v) for v in resume_embedding) + "]"
    with conn.cursor() as cur:
        cur.execute(
            "SELECT job_posting_id::text, "
            "       (1.0 - (embedding <=> %s::vector))::float AS similarity "
            "FROM job_embeddings "
            "ORDER BY embedding <=> %s::vector "
            "LIMIT %s",
            (vec_str, vec_str, K_v),
        )
        rows = cur.fetchall()
    return [(str(r[0]), float(r[1])) for r in rows]


def _domain_match_ids(
    jobs: list[dict[str, Any]],
    resume_domains: list[str],
) -> set[str]:
    """도메인/role_family 매칭 — resume_domains ↔ job.role_family.

    role_family가 resume_domains 중 하나와 일치(부분 포함 포함)하면 후보.
    """
    if not resume_domains:
        return set()
    domain_lower = {d.lower() for d in resume_domains}
    matched: set[str] = set()
    for job in jobs:
        rf = (job.get("role_family") or "").lower()
        if rf and rf in domain_lower:
            matched.add(job["job_id"])
    return matched


def _skill_match_ids(
    jobs: list[dict[str, Any]],
    resume_domains: list[str],
) -> set[str]:
    """스킬/키워드 매칭 — raw_text 기반(§8: tech_stack 컬럼 없음).

    resume_domains 키워드가 job.raw_text에 포함되면 후보.
    대소문자 무시, 영문 키워드 기준 단어 경계 없이 포함 여부만 검사(단순 recall 우선).
    """
    if not resume_domains:
        return set()
    keywords = [d.lower() for d in resume_domains if d]
    matched: set[str] = set()
    for job in jobs:
        raw = (job.get("raw_text") or "").lower()
        if any(kw in raw for kw in keywords):
            matched.add(job["job_id"])
    return matched


def select_candidates(
    conn: psycopg.Connection[tuple[Any, ...]],
    resume_embedding: list[float],
    jobs: list[dict[str, Any]],
    resume_domains: list[str],
    K_v: int = DEFAULT_K_V,
    K_max: int = DEFAULT_K_MAX,
) -> CandidateSet:
    """하이브리드 합집합으로 후보 K_max개 선별.

    1. 벡터: pgvector ANN top-K_v → (job_id, similarity) 목록
    2. 도메인: resume_domains ↔ role_family 매칭
    3. 스킬: resume_domains 키워드 ↔ raw_text 매칭
    4. 합집합 → K_max cap
    5. 정렬: 유사도 desc, job_id asc (결정적 tie-break — GS-1, ADR-108 D2)

    Returns:
        CandidateSet — candidates(K_max 이하), similarity_map, non_candidates.
    """
    all_job_ids = {j["job_id"] for j in jobs}

    # 1. 벡터 top-K_v
    vector_rows = _fetch_vector_top_k(conn, resume_embedding, K_v)
    vector_ids = {row[0] for row in vector_rows}
    similarity_map: dict[str, float] = {row[0]: row[1] for row in vector_rows}

    # 2. 도메인 매칭
    domain_ids = _domain_match_ids(jobs, resume_domains)

    # 3. 스킬/키워드 매칭
    skill_ids = _skill_match_ids(jobs, resume_domains)

    # 4. 합집합 — 전체 공고 중 존재하는 것만
    union_ids = (vector_ids | domain_ids | skill_ids) & all_job_ids

    # 5. 결정적 정렬: 유사도 desc → job_id asc
    #    similarity_map에 없는 id(도메인/스킬만 해당)는 0.0
    sorted_ids = sorted(
        union_ids,
        key=lambda jid: (
            -similarity_map.get(jid, 0.0),
            int(jid) if jid.isdigit() else jid,
        ),
    )

    # K_max cap
    candidates = sorted_ids[:K_max]
    candidate_set = set(candidates)
    non_candidates = [j["job_id"] for j in jobs if j["job_id"] not in candidate_set]

    return CandidateSet(
        candidates=candidates,
        similarity_map={jid: similarity_map.get(jid, 0.0) for jid in candidates},
        non_candidates=non_candidates,
    )
