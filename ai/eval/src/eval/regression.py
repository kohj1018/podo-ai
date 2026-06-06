"""T-014 불변식 회귀 (SPEC §10-1) — GS-1 결정성·제품 규칙 게이트.

고정 3-JD 합성 픽스처(Frontend / Android / Marketing)에서 *정확한 fit 수치가 아닌
관계 불변식* 10종을 검사한다(회귀 철학: 프롬프트/스키마 개선으로 fit이 정당히
변동돼도 관계가 유지되면 통과).

추출형 재검은 worker.verify_matches._is_extractive/_build_haystack을 재사용한다
(eval→worker 의존 허용 — eval은 worker 산출 위의 측정 하니스, ARCH §3-1).
픽스처 캐시는 격리 네임스페이스(`fixture`)를 써서 일반 재계산이 골든을 흔들지 않게 한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.models import Resume
from worker.cache import CacheAdapter
from worker.grounding import build_haystack, is_extractive  # per ADR-103

# 회귀 골든 전용 캐시 네임스페이스 (SPEC §8-2 — 일반 실행 캐시와 분리)
FIXTURE_NAMESPACE = "fixture"

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "original_3_jds.json"


@dataclass
class InvariantResult:
    """단일 불변식 검사 결과."""

    name: str
    passed: bool
    detail: str


@dataclass
class Fixture:
    """회귀 골든 픽스처 — 합성 스코어링 산출물 + 이력서."""

    ranking: list[dict[str, Any]]
    tables: dict[str, Any]
    pairwise: list[dict[str, Any]]
    resume: Resume


def load_fixture(path: Path | None = None) -> Fixture:
    """고정 3-JD 합성 픽스처를 로드한다 (기본 경로 = fixtures/original_3_jds.json)."""
    data = json.loads((path or _FIXTURE_PATH).read_text(encoding="utf-8"))
    return Fixture(
        ranking=data["ranking"],
        tables=data["tables"],
        pairwise=data["pairwise"],
        resume=Resume.model_validate(data["resume"]),
    )


def make_fixture_cache() -> CacheAdapter:
    """회귀 골든 전용 격리 캐시 — 일반 캐시와 네임스페이스 분리(SPEC §8-2)."""
    return CacheAdapter(namespace=FIXTURE_NAMESPACE)


def _by_role(ranking: list[dict[str, Any]], role: str) -> dict[str, Any] | None:
    for item in ranking:
        if item.get("role_family") == role:
            return item
    return None


def check_invariants(
    ranking: list[dict[str, Any]],
    tables: dict[str, Any],
    pairwise: list[dict[str, Any]],
    resume: Resume,
) -> list[InvariantResult]:
    """SPEC §10-1 제품 불변식 10종을 검사하고 InvariantResult 목록을 반환한다."""
    results: list[InvariantResult] = []

    def add(name: str, passed: bool, detail: str = "") -> None:
        results.append(InvariantResult(name=name, passed=passed, detail=detail))

    fe = _by_role(ranking, "frontend")
    android = _by_role(ranking, "android")
    mkt = _by_role(ranking, "marketing")
    n = len(ranking)

    fe_rank = fe["rank"] if fe else None
    fe_fit = fe["fit_level"] if fe else None
    an_rank = android["rank"] if android else None
    an_fit = android["fit_level"] if android else None
    mkt_rank = mkt["rank"] if mkt else None
    mkt_fit = mkt["fit_level"] if mkt else None

    # 1. Frontend #1
    add("frontend_rank_1", fe_rank == 1, f"fe rank={fe_rank}")
    # 2. Frontend fit >= 4
    add("frontend_fit_ge_4", fe_fit is not None and fe_fit >= 4, f"fe fit={fe_fit}")
    # 3. Android가 Frontend보다 아래
    add(
        "android_below_frontend",
        an_rank is not None and fe_rank is not None and an_rank > fe_rank,
        f"android rank={an_rank}, fe rank={fe_rank}",
    )
    # 4. Android fit <= 3
    add("android_fit_le_3", an_fit is not None and an_fit <= 3, f"android fit={an_fit}")
    # 5. Android fit < Frontend fit
    add(
        "android_fit_lt_frontend",
        an_fit is not None and fe_fit is not None and an_fit < fe_fit,
        f"android fit={an_fit}, fe fit={fe_fit}",
    )
    # 6. Marketing 최하위
    add("marketing_rank_last", mkt_rank == n, f"mkt rank={mkt_rank}, n={n}")
    # 7. Marketing fit <= 2
    add(
        "marketing_fit_le_2", mkt_fit is not None and mkt_fit <= 2, f"mkt fit={mkt_fit}"
    )
    # 8. mismatch 우선순위 가드 (mismatch가 어떤 non-mismatch보다 위로 못 옴)
    mismatch_ranks = [
        it["rank"] for it in ranking if it.get("domain_alignment") == "mismatch"
    ]
    nonmismatch_ranks = [
        it["rank"] for it in ranking if it.get("domain_alignment") != "mismatch"
    ]
    guard_ok = (
        not mismatch_ranks
        or not nonmismatch_ranks
        or min(mismatch_ranks) > max(nonmismatch_ranks)
    )
    add(
        "mismatch_priority_guard",
        guard_ok,
        f"mismatch={sorted(mismatch_ranks)} nonmismatch={sorted(nonmismatch_ranks)}",
    )
    # 9. 살아남은 모든 evidence 인용이 추출형 (_is_extractive 재검)
    haystack = build_haystack(resume.raw_text, resume.evidence)
    non_extractive: list[str] = []
    for jid, table in tables.items():
        for row in table["rows"]:
            for quote in row["evidence_quotes"]:
                if not is_extractive(quote, haystack):
                    non_extractive.append(f"{jid}:{quote!r}")
    add(
        "all_quotes_extractive",
        not non_extractive,
        f"non_extractive={non_extractive[:3]}" if non_extractive else "all extractive",
    )
    # 10. pairwise 불일치는 보고되나 최상위 랭킹을 바꾸지 않음
    disagreement = any(not pr.get("agreed", True) for pr in pairwise)
    add(
        "disagreement_keeps_top",
        not disagreement or fe_rank == 1,
        f"disagreement={disagreement}, fe rank={fe_rank}",
    )

    return results


def all_pass(results: list[InvariantResult]) -> bool:
    """모든 불변식이 통과했는지."""
    return all(r.passed for r in results)


def failed(results: list[InvariantResult]) -> list[InvariantResult]:
    """실패한 불변식만 추린다."""
    return [r for r in results if not r.passed]
