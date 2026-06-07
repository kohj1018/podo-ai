"""T-011: Scorer 파이프라인 오케스트레이션 (SPEC §2·§7-4·§11·§12).

run_scoring: 단계 1~12를 하나의 결정적 단일 진입점으로 묶는다 (`ai/worker` 진입점).
  - 단계 1~6 (추출·JD구조화·도메인정렬·매칭·검증·compute_fit)을 공고별로 실행
  - compute_fit은 단계 6에서 공고당 1회만 호출하고 7·8·11에 공유 (재계산 금지)
  - 공고별 LLM 단계(2·4·5) 실패는 해당 공고만 보류(pending)로 처리 (가짜 점수 금지)
  - 단계 7~12 (listwise·후보집합·pairwise·BT/aggregate·리포트)는 내부 헬퍼 _rank

_rank: 단계 7~12 결정적 오케스트레이션 — 이미 계산된 tables/domain_ctx/fits를 받는다
  (테스트가 7~12만 독립 검증할 수 있도록 분리).
"""

from __future__ import annotations

from typing import Any, Callable

from core.models import MatchingTable, PairwiseResult, Resume, domain_alignment
from worker.compare_pairwise import run_pairwise
from worker.domain_classifier import CLASSIFIER_VERSION, classify_domains
from worker.matching import build_matching_table
from worker.parse_job import structure_job
from worker.parse_resume import extract_evidence
from worker.rank_aggregate import DOM_RANK, aggregate, compute_fit
from worker.rerank_listwise import listwise_rank
from worker.verify_matches import verify_table

# ---------------------------------------------------------------------------
# SPEC §7-4 상수
# ---------------------------------------------------------------------------

TOP_K_PAIRWISE: int = 5
MAX_PAIRWISE_CANDIDATES: int = 8


# ---------------------------------------------------------------------------
# LLM 실패 표지 (시스템 경계 예외)
# ---------------------------------------------------------------------------


class LLMCallError(Exception):
    """LLM 호출 실패 — 해당 공고는 보류(pending) 처리된다.

    가짜 점수 생성 금지 (SPEC §2 / Charter §7-4 보류 표현 / FAC-5).
    실제 LLM 게이트웨이는 worker.llm.LLMError를 던지므로 run_scoring은 둘 다 잡는다.
    """


# ---------------------------------------------------------------------------
# SPEC §7-4: _build_pairwise_candidates (그대로 이식)
# ---------------------------------------------------------------------------


def _build_pairwise_candidates(
    ordered_ids: list[str],
    fits: dict[str, dict[str, Any]],
    domain_ctx: dict[str, dict[str, str]],
    top_k: int,
) -> tuple[list[str], dict[str, Any]]:
    """SPEC §7-4 결정적 후보 집합 구성.

    4단 누적 포함 규칙:
      1) listwise top-K
      2) fit>=4 (엔지니어링 한정 — mismatch는 cap으로 fit>=4 불가)
      3) strong frontend/fullstack 구제 (fit > 집합 최약)
      4) strong-domain catch-all 구제 (더 낮은-fit adjacent/weak가 비교될 때)

    상한: MAX_PAIRWISE_CANDIDATES=8, 정렬 키 (-fit, -DOM_RANK, listwise_rank).
    제외분: reason에 [bounded out] 기록.
    """

    def fit(j: str) -> int:
        return int(fits.get(j, {}).get("level", 1))

    def dom(j: str) -> str:
        return domain_ctx.get(j, {}).get("domain_alignment", "weak")

    def rf(j: str) -> str:
        return domain_ctx.get(j, {}).get("role_family", "other")

    def is_strong_fe(j: str) -> bool:
        return dom(j) == "strong" and rf(j) in ("frontend", "fullstack")

    lw_rank = {j: i for i, j in enumerate(ordered_ids)}
    candidates: list[str] = []
    reasons: dict[str, str] = {}

    def add(j: str, why: str) -> None:
        if j not in reasons:
            candidates.append(j)
            reasons[j] = why

    # 1) listwise top-K (any domain)
    for j in ordered_ids[:top_k]:
        add(j, "listwise top-5")

    # 2) any fit>=4 (mismatch는 DOMAIN_CAP으로 fit>=4 불가 → 사실상 엔지니어링 한정)
    for j in ordered_ids:
        if fit(j) >= 4:
            add(j, "fit>=4")

    # 3) strong frontend/fullstack with fit > 현재 집합의 최약 fit
    for j in ordered_ids:
        if j in reasons or not is_strong_fe(j):
            continue
        weakest = min((fit(c) for c in candidates), default=0)
        if fit(j) > weakest:
            add(j, f"strong frontend rescue (fit {fit(j)} > weakest-in-set {weakest})")

    # 4) catch-all: 더 낮은-fit adjacent/weak가 비교되는데 strong이 빠진 경우 구제
    for j in ordered_ids:
        if j in reasons or dom(j) != "strong":
            continue
        if any(
            dom(c) in ("adjacent", "weak", "mismatch") and fit(c) < fit(j)
            for c in candidates
        ):
            add(j, "strong-domain rescue (a lower-fit adjacent/weak role is compared)")

    # bound: fit → domain → listwise rank 우선
    cap = MAX_PAIRWISE_CANDIDATES
    if len(candidates) > cap:
        kept = set(
            sorted(
                candidates,
                key=lambda j: (-fit(j), -DOM_RANK.get(dom(j), 1), lw_rank.get(j, 999)),
            )[:cap]
        )
        for j in candidates:
            if j not in kept:
                reasons[j] += " [bounded out]"
        candidates = [j for j in ordered_ids if j in kept]

    info: dict[str, Any] = {
        "pairwise_candidate_set": [
            {
                "job_id": j,
                "reason": reasons[j],
                "fit": fit(j),
                "domain_alignment": dom(j),
                "role_family": rf(j),
            }
            for j in candidates
        ],
        "rescued_strong_domain": [
            j for j in candidates if reasons[j].startswith("strong")
        ],
        "strong_domain_excluded": [
            {
                "job_id": j,
                "fit": fit(j),
                "reason": (
                    "bounded out (max candidates)"
                    if "[bounded out]" in reasons.get(j, "")
                    else f"not rescued (fit {fit(j)} not above weakest-in-set)"
                ),
            }
            for j in ordered_ids
            if is_strong_fe(j) and j not in candidates
        ],
    }
    return candidates, info


# ---------------------------------------------------------------------------
# run_scoring: 단계 1~12 단일 진입점 (SPEC §2)
# ---------------------------------------------------------------------------


def run_scoring(
    resume: Resume,
    jobs: list[dict[str, str]],
    *,
    ranking_mode: str = "domain_fit_bt",
    structured_call_fn: Callable[..., Any] | None = None,
    listwise_call_fn: Callable[..., str] | None = None,
    pairwise_call_fn: Callable[..., str] | None = None,
    user_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """단계 1~12 단일 오케스트레이션 진입점 (SPEC §2).

    Args:
        resume: 이력서 (raw_text + primary_domains/secondary_domains). evidence는
            단계 1에서 채워진다.
        jobs: 원본 공고 목록. 각 항목 {job_id, company, title, url, raw_text}.
        ranking_mode: "domain_fit_bt" | "fit_primary" | "bt_primary".
        structured_call_fn: 단계 1·2·4·5 LLM 주입 (call_structured 인터페이스).
        listwise_call_fn / pairwise_call_fn: 단계 7·9 LLM 주입 (_openai_call).
        user_profile: 리포트에 echo할 사용자 프로파일 메타 (선택).

    오케스트레이션 규율 (SPEC §2 — 이식 시 보존):
        compute_fit은 단계 6에서 공고당 *한 번* 계산하고 단계 7·8·11에서 공유한다.
        공고별 LLM 단계(2·4·5) 실패는 가짜 점수를 만들지 않고 해당 공고만 보류한다.

    Returns:
        _rank와 동일 계약 (final_ranking / matching_tables / pairwise_comparisons /
        pending_job_ids).
    """
    from worker.llm import LLMError

    # 단계 1: 이력서 evidence 추출 (LLM, 전역 — 실패 시 채점 불가하므로 전파)
    evidence = extract_evidence(resume.raw_text, _call_fn=structured_call_fn)

    # T-066: evidence 추출 직후 도메인 분류 (결정적, LLM 0 — domain_alignment 사용 전).
    # 신호 빈약(confidence=low) 시 입력 domains 유지 — known/seed 도메인을 unknown으로
    # 덮지 않는다. 신호 있으면 분류 결과를 scoring(domain_alignment)에 반영.
    domain_result = classify_domains(evidence)
    if domain_result.confidence != "low":
        primary_domains = domain_result.primary_domains
        secondary_domains = domain_result.secondary_domains
    else:
        primary_domains = resume.primary_domains
        secondary_domains = resume.secondary_domains
    resume_full = Resume(
        raw_text=resume.raw_text,
        evidence=evidence,
        primary_domains=primary_domains,
        secondary_domains=secondary_domains,
    )

    tables: dict[str, MatchingTable] = {}
    domain_ctx: dict[str, dict[str, str]] = {}
    fits: dict[str, dict[str, Any]] = {}
    pending: set[str] = set()

    for job in jobs:
        jid = job["job_id"]
        try:
            # 단계 2: JD 요구사항 구조화 (LLM)
            jp = structure_job(
                job_id=jid,
                company=job.get("company", ""),
                title=job.get("title", ""),
                url=job.get("url", ""),
                raw_text=job.get("raw_text", ""),
                _call_fn=structured_call_fn,
            )
            # 단계 3: 도메인 정렬 컨텍스트 (결정적, ai/core)
            tier, reason = domain_alignment(
                jp.role_family,
                primary_domains,
                secondary_domains,
            )
            # 단계 4: 요구↔근거 매칭 (LLM)
            table = build_matching_table(jp, evidence, _call_fn=structured_call_fn)
            # 단계 5: 매칭 검증 (결정적 추출 + 보수적 LLM verifier)
            table = verify_table(table, resume_full, _call_fn=structured_call_fn)
            # 단계 6: compute_fit (결정적, 공고당 1회 — 다운스트림 공유, 재계산 금지)
            fit = compute_fit(table, tier)
        except (LLMError, LLMCallError):
            # 가짜 점수 금지 — 해당 공고만 보류, 파이프라인은 나머지로 계속 (FAC-5)
            pending.add(jid)
            continue

        tables[jid] = table
        domain_ctx[jid] = {
            "domain_alignment": tier,
            "role_family": jp.role_family,
            "domain_alignment_reason": reason,
        }
        fits[jid] = fit

    # 단계 7~12: 결정적 오케스트레이션 (이미 계산된 fits 공유 — 재계산 없음)
    result = _rank(
        tables=tables,
        domain_ctx=domain_ctx,
        fits=fits,
        listwise_call_fn=listwise_call_fn,
        pairwise_call_fn=pairwise_call_fn,
        ranking_mode=ranking_mode,
        failed_job_ids=pending,
        user_profile=user_profile,
    )
    # T-066: 분류 결과를 persist_run이 resume_domains로 영속하도록 내부 키로 전달.
    # persist_run이 build_report 전에 pop → 저장 result(§12 계약)·feed 미오염.
    result["_resume_domains"] = {
        "primary_domains": domain_result.primary_domains,
        "secondary_domains": domain_result.secondary_domains,
        "confidence": domain_result.confidence,
        "classifier_version": CLASSIFIER_VERSION,
    }
    return result


# ---------------------------------------------------------------------------
# _rank: 단계 7~12 오케스트레이션 (내부 헬퍼)
# ---------------------------------------------------------------------------


def _rank(
    tables: dict[str, MatchingTable],
    domain_ctx: dict[str, dict[str, str]],
    fits: dict[str, dict[str, Any]],
    *,
    listwise_call_fn: Callable[..., str] | None = None,
    pairwise_call_fn: Callable[..., str] | None = None,
    ranking_mode: str = "domain_fit_bt",
    failed_job_ids: set[str] | None = None,
    user_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """단계 7~12 오케스트레이션 (단계 6 산출 tables/domain_ctx/fits를 입력으로 받음).

    fits는 단계 6에서 *사전 계산*된 결과 — 본 함수는 재계산하지 않고 공유만 한다.
    failed_job_ids: 단계 1~6에서 LLM 실패로 보류된 공고 id 집합.

    Returns:
        {
            "final_ranking": {note, user_profile, guard_moves, ranking[FitResult dict]},
            "matching_tables": {job_id: MatchingTable dict},
            "pairwise_comparisons": {bradley_terry_scores, candidate_set, comparisons},
            "pending_job_ids": set[str],
        }
    """
    pending: set[str] = set(failed_job_ids or set())

    # 보류 공고 제외 후 활성 공고집합
    active_tables = {jid: t for jid, t in tables.items() if jid not in pending}
    active_fits = {jid: f for jid, f in fits.items() if jid not in pending}
    active_ctx = {jid: c for jid, c in domain_ctx.items() if jid not in pending}

    # 단계 7: listwise 재랭킹 (LLM)
    listwise_result, _lw_warnings = listwise_rank(
        tables=active_tables,
        domain_ctx=active_ctx,
        fits=active_fits,
        _call_fn=listwise_call_fn,
    )
    # active_tables에 없는 초과 id는 제거 (LLM이 pending 공고를 반환할 수 있음)
    active_set = set(active_tables.keys())
    ordered_ids = [
        item["job_id"] for item in listwise_result if item["job_id"] in active_set
    ]
    # listwise reason 맵 (aggregate에서 listwise_reason 필드로 활용)
    listwise_reasons: dict[str, str] = {
        item["job_id"]: item.get("reason", "")
        for item in listwise_result
        if item["job_id"] in active_set
    }

    # 단계 8: pairwise 후보 집합 구성 (결정적)
    top_k = min(TOP_K_PAIRWISE, len(ordered_ids))
    candidate_ids, pairwise_info = _build_pairwise_candidates(
        ordered_ids=ordered_ids,
        fits=active_fits,
        domain_ctx=active_ctx,
        top_k=top_k,
    )

    # 단계 9: pairwise 비교 (LLM)
    pairwise_results: list[PairwiseResult] = run_pairwise(
        tables=active_tables,
        candidate_ids=candidate_ids,
        domain_ctx=active_ctx,
        _call_fn=pairwise_call_fn,
    )

    # 단계 10·11: BT + aggregate (결정적)
    fit_results, bt_scores, guard_moves = aggregate(
        jobs_by_id=active_tables,
        tables_by_id=active_tables,
        listwise=ordered_ids,
        pairwise=pairwise_results,
        candidate_ids=set(candidate_ids),
        fits=active_fits,
        domain_ctx=active_ctx,
        ranking_mode=ranking_mode,
    )

    # listwise_reason 주입 (FitResult는 이미 조립됨 — dict로 변환 후 필드 보충)
    ranking_dicts: list[dict[str, Any]] = []
    for fr in fit_results:
        d = fr.model_dump()
        d["listwise_reason"] = listwise_reasons.get(fr.job_id, "")
        ranking_dicts.append(d)

    # 단계 12: 리포트 조립 (결정적 직렬화)
    final_ranking: dict[str, Any] = {
        # fit은 확률이 아니라 검증된 요구 커버리지 기반의 보수적 레벨 (SPEC §1)
        "note": "fit은 합격확률이 아니며 요구사항 커버리지 기반의 보수적 레벨입니다.",
        "user_profile": user_profile or {},
        "guard_moves": guard_moves,
        "ranking": ranking_dicts,
    }

    # matching_tables: job_id → MatchingTable dict (ARCH §3-2 JSONB pass-through)
    matching_tables: dict[str, Any] = {
        jid: t.model_dump() for jid, t in active_tables.items()
    }

    # pairwise_comparisons
    pairwise_comparisons: dict[str, Any] = {
        "bradley_terry_scores": bt_scores,
        "candidate_set": pairwise_info["pairwise_candidate_set"],
        "comparisons": [pr.model_dump() for pr in pairwise_results],
    }

    return {
        "final_ranking": final_ranking,
        "matching_tables": matching_tables,
        "pairwise_comparisons": pairwise_comparisons,
        "pending_job_ids": pending,
    }
