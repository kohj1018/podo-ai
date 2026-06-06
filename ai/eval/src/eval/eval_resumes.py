"""T-015 멀티-페르소나 진단 (SPEC §10-2) — 방향성 일반화 게이트.

4개 합성 페르소나(backend_platform / junior_frontend / ai_ml_application /
devops_infra_security)로 *방향성*(정확도 아님)을 점검한다. 페르소나별
primary/secondary_domains 프로파일을 주입해 6 방향성 불변식을 검사하고,
3 랭킹 모드(bt_primary / fit_primary / domain_fit_bt)를 ablation한다.

추출형 재검은 worker.verify_matches._is_extractive/_build_haystack을 재사용한다
(T-014 regression과 동일 신뢰 레이어). 모드 비교는 worker.rank_aggregate.aggregate를
모드만 바꿔 재사용한다(랭킹 로직 100% 동일 — SPEC §11 "aggregate(3 모드) 재사용").
저장 합성 산출물만 읽는다(LLM 미호출 — F-004 §6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.models import MatchingTable, PairwiseResult, Resume
from worker.grounding import build_haystack, is_extractive  # per ADR-103
from worker.rank_aggregate import DOM_RANK, RANKING_MODES, aggregate

_PERSONA_DIR = Path(__file__).parent / "fixtures" / "personas"

# SPEC §10-2 표: 4 합성 페르소나 (도메인 프로파일은 각 fixture에 baked-in)
PERSONAS: dict[str, str] = {
    "backend_platform": "backend_platform.json",
    "junior_frontend": "junior_frontend.json",
    "ai_ml_application": "ai_ml_application.json",
    "devops_infra_security": "devops_infra_security.json",
}


@dataclass
class Persona:
    """합성 페르소나 — 도메인 프로파일 + 저장 스코어링 산출물 + 이력서."""

    persona_id: str
    primary_domains: list[str]
    secondary_domains: list[str]
    resume: Resume
    ranking: list[dict[str, Any]]
    tables: dict[str, Any]
    pairwise: list[dict[str, Any]]
    expected_behavior: dict[str, Any]


@dataclass
class InvariantEntry:
    """단일 방향성 불변식 결과. severity: pass | warning | na | fail."""

    name: str
    severity: str
    detail: str = ""


@dataclass
class DiagnosticResult:
    """한 페르소나의 진단 결과 — 6 불변식 + pass 판정(fail=0)."""

    persona_id: str
    domain_alignment: str
    invariants: list[InvariantEntry]
    passed: bool


@dataclass
class RankingModeComparison:
    """3 랭킹 모드 ablation 결과. mismatch_violation은 도메인 가드로 0이어야 함."""

    persona_id: str
    modes: list[str]
    fit_rank_inversions: int
    tier_inversions: int
    mismatch_violation: int
    by_mode: dict[str, dict[str, int]] = field(default_factory=dict)


def load_persona(name: str) -> Persona:
    """합성 페르소나 픽스처를 로드한다(expected_behavior 포함)."""
    data = json.loads((_PERSONA_DIR / PERSONAS[name]).read_text(encoding="utf-8"))
    return Persona(
        persona_id=data["persona_id"],
        primary_domains=data["primary_domains"],
        secondary_domains=data["secondary_domains"],
        resume=Resume.model_validate(data["resume"]),
        ranking=data["ranking"],
        tables=data["tables"],
        pairwise=data["pairwise"],
        expected_behavior=data.get("expected_behavior", {}),
    )


def _role_matches(role_family: str, domains: list[str]) -> bool:
    """role_family 토큰이 도메인 토큰과 겹치는가 (예: 'devops_infra' ~ 'devops')."""
    domain_tokens = {tok for d in domains for tok in d.split("_")}
    return bool(set(role_family.split("_")) & domain_tokens)


def diagnose(persona: Persona) -> DiagnosticResult:
    """SPEC §10-2 방향성 불변식 6종을 검사한다.

    fail 가능: extractive / fit_scale / mismatch_priority.
    warning|na|pass 전용(진단): expected_top_in_top3 / domain_order /
    primary_domain_available.
    """
    ranking = persona.ranking
    n = len(ranking)
    by_rank = sorted(ranking, key=lambda r: r["rank"])
    domain_alignment = str(by_rank[0]["domain_alignment"]) if by_rank else "na"

    invariants: list[InvariantEntry] = []
    primary_roles = [
        r for r in ranking if _role_matches(r["role_family"], persona.primary_domains)
    ]

    # 1. extractive (fail) — 살아남은 evidence 인용이 이력서 verbatim인가
    haystack = build_haystack(persona.resume.raw_text, persona.resume.evidence)
    non_extractive: list[str] = []
    for jid, table in persona.tables.items():
        for row in table["rows"]:
            for quote in row.get("evidence_quotes", []):
                if not is_extractive(quote, haystack):
                    non_extractive.append(f"{jid}:{quote!r}")
    invariants.append(
        InvariantEntry(
            "extractive",
            "fail" if non_extractive else "pass",
            f"non_extractive={non_extractive[:3]}"
            if non_extractive
            else "all extractive",
        )
    )

    # 2. fit_scale (fail) — fit_level이 1~5 정수(% 금지)
    bad_fits = [
        f"{r['role_family']}={r.get('fit_level')!r}"
        for r in ranking
        if not isinstance(r.get("fit_level"), int) or not 1 <= r["fit_level"] <= 5
    ]
    invariants.append(
        InvariantEntry(
            "fit_scale",
            "fail" if bad_fits else "pass",
            f"out_of_scale={bad_fits}" if bad_fits else "all 1..5 int",
        )
    )

    # 3. mismatch_priority (fail) — mismatch가 non-mismatch 위로 못 옴
    mm_ranks = [r["rank"] for r in ranking if r.get("domain_alignment") == "mismatch"]
    non_ranks = [r["rank"] for r in ranking if r.get("domain_alignment") != "mismatch"]
    guard_ok = not mm_ranks or not non_ranks or min(mm_ranks) > max(non_ranks)
    invariants.append(
        InvariantEntry(
            "mismatch_priority",
            "pass" if guard_ok else "fail",
            f"mismatch={sorted(mm_ranks)} nonmismatch={sorted(non_ranks)}",
        )
    )

    # 4. expected_top_in_top3 (warning/na) — primary 도메인 역할이 top3 안인가
    if not primary_roles:
        invariants.append(
            InvariantEntry("expected_top_in_top3", "na", "no primary-domain role")
        )
    else:
        best = min(r["rank"] for r in primary_roles)
        invariants.append(
            InvariantEntry(
                "expected_top_in_top3",
                "pass" if best <= 3 else "warning",
                f"best primary rank={best}",
            )
        )

    # 5. domain_order (warning/na) — 랭킹이 도메인 tier 비증가 순인가
    if n < 2:
        invariants.append(InvariantEntry("domain_order", "na", "n<2"))
    else:
        tiers = [DOM_RANK.get(r["domain_alignment"], 1) for r in by_rank]
        inv = sum(1 for a, b in zip(tiers, tiers[1:]) if a < b)
        invariants.append(
            InvariantEntry(
                "domain_order",
                "pass" if inv == 0 else "warning",
                f"tier_inversions={inv}",
            )
        )

    # 6. primary_domain_available (warning/na) — primary 도메인 역할 존재
    if not ranking:
        invariants.append(
            InvariantEntry("primary_domain_available", "na", "empty ranking")
        )
    else:
        invariants.append(
            InvariantEntry(
                "primary_domain_available",
                "pass" if primary_roles else "warning",
                f"primary roles={[r['role_family'] for r in primary_roles]}",
            )
        )

    passed = all(e.severity != "fail" for e in invariants)
    return DiagnosticResult(persona.persona_id, domain_alignment, invariants, passed)


def compare_ranking_modes(persona: Persona) -> RankingModeComparison:
    """3 랭킹 모드(SPEC §5-2)를 ablation해 모드별 역전 지표를 산출한다.

    worker.rank_aggregate.aggregate를 모드만 바꿔 재사용한다(랭킹 로직 동일).
    도메인 가드가 mismatch를 항상 최하로 보내므로 mismatch_violation은 0이어야 한다.
    """
    tables_by_id = {
        jid: MatchingTable.model_validate(t) for jid, t in persona.tables.items()
    }
    pairwise = [PairwiseResult.model_validate(p) for p in persona.pairwise]
    by_rank = sorted(persona.ranking, key=lambda r: r["rank"])
    listwise = [r["job_id"] for r in by_rank]
    fits: dict[str, dict[str, Any]] = {
        r["job_id"]: {"level": r["fit_level"]} for r in persona.ranking
    }
    domain_ctx: dict[str, dict[str, str]] = {
        r["job_id"]: {
            "domain_alignment": r["domain_alignment"],
            "role_family": r["role_family"],
        }
        for r in persona.ranking
    }
    candidate_ids = {p["job_a"] for p in persona.pairwise} | {
        p["job_b"] for p in persona.pairwise
    }

    by_mode: dict[str, dict[str, int]] = {}
    total_fit = total_tier = total_mismatch = 0
    for mode in RANKING_MODES:
        results, _bt, _guard = aggregate(
            jobs_by_id=tables_by_id,
            tables_by_id=tables_by_id,
            listwise=listwise,
            pairwise=pairwise,
            candidate_ids=candidate_ids,
            fits=fits,
            domain_ctx=domain_ctx,
            ranking_mode=mode,
        )
        ordered = sorted(results, key=lambda fr: fr.rank)
        fit_seq = [fr.fit_level for fr in ordered]
        tier_seq = [DOM_RANK.get(fr.domain_alignment, 1) for fr in ordered]
        fit_inv = sum(1 for a, b in zip(fit_seq, fit_seq[1:]) if a < b)
        tier_inv = sum(1 for a, b in zip(tier_seq, tier_seq[1:]) if a < b)
        mm = [fr.rank for fr in ordered if fr.domain_alignment == "mismatch"]
        non = [fr.rank for fr in ordered if fr.domain_alignment != "mismatch"]
        violation = sum(1 for mr in mm for nr in non if mr < nr)
        by_mode[mode] = {
            "fit_rank_inversions": fit_inv,
            "tier_inversions": tier_inv,
            "mismatch_violation": violation,
        }
        total_fit += fit_inv
        total_tier += tier_inv
        total_mismatch += violation

    return RankingModeComparison(
        persona_id=persona.persona_id,
        modes=list(RANKING_MODES),
        fit_rank_inversions=total_fit,
        tier_inversions=total_tier,
        mismatch_violation=total_mismatch,
        by_mode=by_mode,
    )
