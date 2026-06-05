"""T-013 도메인 인지 균형 선택 — SPEC §9-3·§9-4 그대로 이식.

역할:
- `classify_role_family`/`ROLE_PATTERNS`: 제목 → role_family (순서 우선 첫 매치)
- `role_tier`: role_family + 사용자 도메인 → tier (primary/adjacent/weak/mismatch)
- `build_pool`: 후보 목록에서 tier 계산 후 pool 구성 (pool_size, 회사 round-robin)
- `select_balanced`: pool → 균형 선택 (50/30/20 + priority backfill)
- `SelectionReport`: 선택 내역 리포트 (tier/role_family 분포, selected/skipped)

`domain_alignment`은 ai/core(T-002) import — crawler→worker 의존 위반 방지(§3-1).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import islice
from typing import Any

from core.models import domain_alignment

# job dict 별칭: fetch_jobs RawJob + role_family/tier enrich (값 혼합 가능 → Any)
Job = dict[str, Any]

# ---------------------------------------------------------------------------
# §9-3. 제목 기반 role_family 분류 (SPEC 상수 그대로)
# ---------------------------------------------------------------------------

# 순서 중요: 더 구체적인 패턴이 앞에 위치, 첫 매치 승
ROLE_PATTERNS: list[tuple[str, list[str]]] = [
    ("fullstack", ["fullstack", "full-stack", "full stack", "풀스택"]),
    (
        "frontend",
        [
            "frontend",
            "front-end",
            "front end",
            "프론트엔드",
            "프론트",
            "web frontend",
            "웹 프론트",
            "웹프론트",
            "react",
            "vue",
            "웹 프론트엔드",
        ],
    ),
    ("android", ["android", "안드로이드"]),
    ("ios", ["ios"]),
    (
        "ml_ai",
        [
            "ai engineer",
            " ai ",
            "machine learning",
            "ml engineer",
            "mlops",
            "deep learning",
            "data scientist",
            "llm",
            "인공지능",
            "생성형",
        ],
    ),
    (
        "data",
        [
            "data analytics",
            "analytics engineer",
            "data engineer",
            "data platform",
            "데이터 엔지니어",
            "데이터 분석",
            "데이터",
        ],
    ),
    (
        "security",
        [
            "security",
            "보안",
            "모의해킹",
            "detection",
            "response",
            "appsec",
            "침해사고",
        ],
    ),
    (
        "devops_infra",
        [
            "aiops",
            "devops",
            "sre",
            "platform engineer",
            "platform",
            "infra",
            "인프라",
            "network",
            "네트워크",
            "cloud",
            "클라우드",
            "kubernetes",
            "reliability",
            "플랫폼",
        ],
    ),
    ("backend", ["backend", "back-end", "back end", "서버", "백엔드", "server"]),
    ("marketing", ["marketer", "marketing", "마케팅", "마케터"]),
    ("design", ["designer", "design", "디자인"]),
    (
        "product",
        ["product manager", "프로덕트 매니저", "프로덕트매니저", "기획자"],
    ),
]

# MVP 단일 사용자 도메인 설정값 (SPEC §9-4 이식 적응 — 후속에서 후보별 값으로 교체)
USER_PRIMARY_DOMAINS: list[str] = ["frontend", "fullstack", "web", "robot_web"]
USER_SECONDARY_DOMAINS: list[str] = ["backend", "cloud", "mobile"]

# pool_size 기본값 (SPEC §9-4)
DEFAULT_POOL_SIZE: int = 50


def classify_role_family(title: str) -> str:
    """제목 키워드 → role_family. 순서대로 첫 매치 승, 미매칭은 'other'.

    WHY 소문자 변환: 대소문자 무관 매칭이 필요하고, ROLE_PATTERNS 키워드는 모두 소문자.
    """
    lower = title.lower()
    for family, keywords in ROLE_PATTERNS:
        if any(kw in lower for kw in keywords):
            return family
    return "other"


# ---------------------------------------------------------------------------
# tier 매핑
# ---------------------------------------------------------------------------

_ALIGNMENT_TO_TIER: dict[str, str] = {
    "strong": "primary",
    "adjacent": "adjacent",
    "weak": "weak",
    "mismatch": "mismatch",
}


def role_tier(
    role_family: str,
    primary: list[str] | None = None,
    secondary: list[str] | None = None,
) -> str:
    """role_family → tier(primary/adjacent/weak/mismatch).

    primary/secondary 미지정 시 모듈 기본값(USER_*_DOMAINS) 사용.
    """
    p = primary if primary is not None else USER_PRIMARY_DOMAINS
    s = secondary if secondary is not None else USER_SECONDARY_DOMAINS
    alignment, _ = domain_alignment(role_family, p, s)
    return _ALIGNMENT_TO_TIER[alignment]


# ---------------------------------------------------------------------------
# §9-4. build_pool — tier 계산 + 회사 round-robin
# ---------------------------------------------------------------------------


def build_pool(
    jobs: list[Job],
    pool_size: int = DEFAULT_POOL_SIZE,
    primary: list[str] | None = None,
    secondary: list[str] | None = None,
) -> list[Job]:
    """후보 목록에서 tier를 계산하고 회사 round-robin으로 pool_size만큼 반환.

    각 job dict에 'role_family'(없으면 제목으로 분류)와 'tier'를 채운다.
    회사 round-robin: 동일 회사가 pool를 독점하지 않도록 순서를 배분.
    """
    enriched: list[Job] = []
    for job in jobs:
        entry = dict(job)
        if "role_family" not in entry:
            entry["role_family"] = classify_role_family(entry.get("title", ""))
        entry["tier"] = role_tier(entry["role_family"], primary, secondary)
        enriched.append(entry)

    # 회사 round-robin: tier 순 정렬 후 같은 tier 내에서 회사 round-robin
    tier_order = {"primary": 0, "adjacent": 1, "weak": 2, "mismatch": 3}
    enriched.sort(key=lambda j: tier_order.get(j["tier"], 9))

    # 회사 round-robin 적용 (동일 회사 연속 방지)
    by_company: dict[str, list[Job]] = {}
    for job in enriched:
        company = job.get("company", "")
        by_company.setdefault(company, []).append(job)

    result: list[Job] = []
    # 라운드 로빈: 각 라운드에서 회사별 1개씩 꺼냄
    max_rounds = max(len(v) for v in by_company.values()) if by_company else 0
    for _ in range(max_rounds):
        for company_jobs in by_company.values():
            if company_jobs:
                result.append(company_jobs.pop(0))

    return list(islice(result, pool_size))


# ---------------------------------------------------------------------------
# §9-4. select_balanced — 균형 선택 (50/30/20 + priority backfill)
# ---------------------------------------------------------------------------


def select_balanced(pool: list[Job], limit: int = 10) -> list[Job]:
    """pool에서 tier 균형 비율로 limit개 선택.

    비율: primary 50%, adjacent 30%, contrast(weak+mismatch) 나머지.
    정원 미달 시 primary→adjacent→weak→mismatch 순 backfill.
    selected_count == min(limit, len(pool)) 보장.
    """
    q_primary = round(limit * 0.5)
    q_adjacent = round(limit * 0.3)
    q_contrast = limit - q_primary - q_adjacent  # weak + mismatch 합산

    by_tier: dict[str, list[Job]] = {
        "primary": [],
        "adjacent": [],
        "weak": [],
        "mismatch": [],
    }
    for job in pool:
        tier = job.get("tier", "weak")
        by_tier.setdefault(tier, []).append(job)

    # 각 버킷에서 정원만큼 꺼냄
    selected: list[Job] = []
    taken_primary = by_tier["primary"][:q_primary]
    taken_adjacent = by_tier["adjacent"][:q_adjacent]
    # contrast: weak 우선 소진 후 mismatch
    contrast_pool = by_tier["weak"] + by_tier["mismatch"]
    taken_contrast = contrast_pool[:q_contrast]
    n_weak_taken = min(q_contrast, len(by_tier["weak"]))
    n_mismatch_taken = max(0, q_contrast - n_weak_taken)

    selected.extend(taken_primary)
    selected.extend(taken_adjacent)
    selected.extend(taken_contrast)

    # priority backfill: 정원 미달 시 남은 풀에서 채움
    if len(selected) < limit:
        used_ids = {j["job_id"] for j in selected}
        # backfill 순서: primary → adjacent → weak → mismatch
        backfill_order = (
            by_tier["primary"][len(taken_primary) :]
            + by_tier["adjacent"][len(taken_adjacent) :]
            + by_tier["weak"][n_weak_taken:]
            + by_tier["mismatch"][n_mismatch_taken:]
        )
        for job in backfill_order:
            if len(selected) >= limit:
                break
            if job["job_id"] not in used_ids:
                selected.append(job)
                used_ids.add(job["job_id"])

    return selected[:limit]


# ---------------------------------------------------------------------------
# AC-3. 선택 리포트
# ---------------------------------------------------------------------------


@dataclass
class SelectionReport:
    """선택 실행 후 tier/role_family 분포와 selected/skipped 기록."""

    selected_count: int
    skipped_count: int
    selected_tier_dist: dict[str, int]
    skipped_tier_dist: dict[str, int]
    selected_role_family_dist: dict[str, int]
    skipped_role_family_dist: dict[str, int]
    # 주력 도메인(primary) 0건이면 True — SPEC §9-4 명시 요건
    zero_primary_warning: bool = field(default=False)

    @classmethod
    def from_run(
        cls,
        pool: list[Job],
        selected: list[Job],
    ) -> "SelectionReport":
        """pool과 selected를 받아 리포트를 생성한다."""
        selected_ids = {j["job_id"] for j in selected}
        skipped = [j for j in pool if j["job_id"] not in selected_ids]

        selected_tier_dist = dict(Counter(j.get("tier", "weak") for j in selected))
        skipped_tier_dist = dict(Counter(j.get("tier", "weak") for j in skipped))
        selected_role_family_dist = dict(
            Counter(j.get("role_family", "other") for j in selected)
        )
        skipped_role_family_dist = dict(
            Counter(j.get("role_family", "other") for j in skipped)
        )
        zero_primary_warning = selected_tier_dist.get("primary", 0) == 0

        return cls(
            selected_count=len(selected),
            skipped_count=len(skipped),
            selected_tier_dist=selected_tier_dist,
            skipped_tier_dist=skipped_tier_dist,
            selected_role_family_dist=selected_role_family_dist,
            skipped_role_family_dist=skipped_role_family_dist,
            zero_primary_warning=zero_primary_warning,
        )
