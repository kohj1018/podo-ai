"""T-009: listwise 재랭킹 (SPEC §7-3).

compress_table: 매칭표를 압축해 LLM에 전달할 요약 dict 반환
    (JD/이력서 원문 없이 type별 카운트 + strong 수 + gap 분류 + invalid + risks).

listwise_rank: LLM(listwise_rerank) 호출 → 중복 제거 + 누락 시 재질의 1회
    → 여전히 누락이면 (fit_level, DOM_RANK)로 안전 위치 삽입 (맨끝 blind append 금지).

_ask_listwise: LLM 호출 + ranking 리스트·중복/누락 검출 내부 헬퍼.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from core.models import MatchingTable
from worker._json_util import extract_json

# DOM_RANK: rank_aggregate를 SSOT로 import — 캘리브레이션 상수를 복제하면 무음
# drift로 listwise 삽입 순서 ↔ BT 정렬 키가 어긋나 GS-1 회귀가 생긴다 (REV-M1-002).
from worker.rank_aggregate import DOM_RANK

# listwise_rerank 프롬프트 (T-005에서 verbatim 이식됨)
_PROMPT_PATH = Path(__file__).parent / "prompts" / "listwise_rerank.md"
_PROMPT_TEMPLATE: str = _PROMPT_PATH.read_text(encoding="utf-8")

# JSON_SYSTEM (SPEC §8-1) — 프로토타입 검증 문구(추출형·사실성 지시 포함).
_JSON_SYSTEM = (
    "You are a careful, literal information-extraction and evaluation engine. "
    "You follow instructions exactly, never invent facts, and output ONLY valid JSON "
    "with no extra text, no markdown, and no code fences."
)


# ---------------------------------------------------------------------------
# compress_table (SPEC §7-3)
# ---------------------------------------------------------------------------


def compress_table(table: MatchingTable, ctx: dict[str, str]) -> dict[str, Any]:
    """MatchingTable을 LLM 전달용 압축 요약 dict로 변환한다.

    JD/이력서 원문을 포함하지 않는다 — 카운트·strong 수·gap 분류·invalid·risks 요약만.

    Args:
        table: 매칭표
        ctx: {domain_alignment, role_family} — 도메인 정렬 컨텍스트

    Returns:
        압축 요약 dict:
            job_id, domain_alignment, role_family,
            counts (type별 {total, direct, adjacent, weak, missing}),
            strong_count,
            core_prerequisite_gaps (int),
            preferred_technical_gaps (int),
            behavioral_gaps (int),
            product_duty_gaps_not_blocking (int),
            invalid (int),
            risks (list[str])
    """
    counts: dict[str, dict[str, int]] = {}
    strong_count = 0
    core_prerequisite_gaps = 0
    preferred_technical_gaps = 0
    behavioral_gaps = 0
    product_duty_gaps_not_blocking = 0
    invalid_count = 0
    risks: list[str] = []

    _CORE_NATURES = {"technical", "domain", "experience_level", "language"}
    _UNMET = {"missing", "weak"}

    for row in table.rows:
        req_type = row.requirement_type  # critical/required/preferred/optional
        match_level = row.match_level

        # type별 카운트 누적
        if req_type not in counts:
            counts[req_type] = {
                "total": 0,
                "direct": 0,
                "adjacent": 0,
                "weak": 0,
                "missing": 0,
            }
        counts[req_type]["total"] += 1
        if match_level in counts[req_type]:
            counts[req_type][match_level] += 1

        # strong: direct + confidence≥medium + not invalid
        if (
            match_level == "direct"
            and row.confidence in ("high", "medium")
            and not row.invalid_match
        ):
            strong_count += 1

        # invalid
        if row.invalid_match:
            invalid_count += 1

        # risks (원문 아님 — risk_note/verifier_note)
        note = (row.risk_note or row.verifier_note or "").strip()
        if note:
            risks.append(note)

        is_unmet = match_level in _UNMET
        is_core = row.requirement_nature in _CORE_NATURES
        is_prereq = row.prerequisite_status == "prerequisite"
        is_behavioral = row.prerequisite_status == "behavioral_preference"
        is_product_duty = row.prerequisite_status in ("product_duty", "context")

        # core_prerequisite_gaps: prerequisite + core + unmet (critical/required)
        if req_type in ("critical", "required") and is_prereq and is_core and is_unmet:
            core_prerequisite_gaps += 1

        # preferred_technical_gaps: preferred/optional + prereq + core + unmet
        if req_type in ("preferred", "optional") and is_prereq and is_core and is_unmet:
            preferred_technical_gaps += 1

        # behavioral_gaps: behavioral_preference + unmet
        if is_behavioral and is_unmet:
            behavioral_gaps += 1

        # product_duty_gaps_not_blocking: product_duty/context + unmet
        if is_product_duty and is_unmet:
            product_duty_gaps_not_blocking += 1

    return {
        "job_id": table.job_id,
        "domain_alignment": ctx.get("domain_alignment", "weak"),
        "role_family": ctx.get("role_family", "other"),
        "counts": counts,
        "strong_count": strong_count,
        "core_prerequisite_gaps": core_prerequisite_gaps,
        "preferred_technical_gaps": preferred_technical_gaps,
        "behavioral_gaps": behavioral_gaps,
        "product_duty_gaps_not_blocking": product_duty_gaps_not_blocking,
        # 키 이름은 listwise_rerank/pairwise_compare 프롬프트가 참조하는
        # `invalid_matches`와 일치해야 한다 (프롬프트는 SPEC 고정 — 데이터를 맞춘다).
        "invalid_matches": invalid_count,
        "risks": risks[:8],  # SPEC §4-2 risks[:8] 상한 준수
    }


# ---------------------------------------------------------------------------
# _ask_listwise 내부 헬퍼 (SPEC §7-3)
# ---------------------------------------------------------------------------


def _ask_listwise(
    compressed_jobs: list[dict[str, Any]],
    call_fn: Callable[..., str],
) -> tuple[list[dict[str, str]], list[str]]:
    """listwise_rerank LLM 호출 → (ranking 리스트, warnings 리스트).

    ranking 리스트: [{"job_id": ..., "reason": ...}, ...]
    warnings: 중복/누락 검출 기록
    """
    user_prompt = _PROMPT_TEMPLATE.replace(
        "{{JOBS}}", json.dumps(compressed_jobs, ensure_ascii=False)
    )
    raw = call_fn(
        system=_JSON_SYSTEM,
        user=user_prompt,
        max_tokens=3000,
        temperature=0.0,
    )
    try:
        data = extract_json(raw)
        ranking = data.get("ranking", []) if isinstance(data, dict) else []
    except Exception:
        ranking = []

    warnings: list[str] = []
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for item in ranking:
        jid = item.get("job_id", "")
        if jid in seen:
            warnings.append(f"중복 job_id 제거: {jid}")
        else:
            seen.add(jid)
            deduped.append(item)

    return deduped, warnings


# ---------------------------------------------------------------------------
# listwise_rank (SPEC §7-3)
# ---------------------------------------------------------------------------


def listwise_rank(
    tables: dict[str, MatchingTable],
    domain_ctx: dict[str, dict[str, str]],
    fits: dict[str, dict[str, Any]],
    *,
    _call_fn: Callable[..., str] | None = None,
) -> tuple[list[dict[str, str]], list[str]]:
    """listwise 재랭킹 — LLM 호출 + 중복 제거 + 누락 보정 (SPEC §7-3).

    Args:
        tables: job_id → MatchingTable
        domain_ctx: job_id → {domain_alignment, role_family}
        fits: job_id → compute_fit 결과 dict (level 포함)
        _call_fn: 테스트용 LLM 주입 인터페이스

    Returns:
        (ranking, warnings)
        ranking: [{"job_id": ..., "reason": ...}, ...] — 모든 job_id 정확히 1회 포함
        warnings: 누락/중복 처리 기록
    """
    from worker.llm import _openai_call

    call_fn = _call_fn or _openai_call
    all_job_ids: set[str] = set(tables.keys())

    # 압축 매칭표 생성
    compressed_jobs = [
        compress_table(table, domain_ctx.get(jid, {})) for jid, table in tables.items()
    ]

    all_warnings: list[str] = []

    # 1차 LLM 호출
    ranking, warnings = _ask_listwise(compressed_jobs, call_fn)
    all_warnings.extend(warnings)

    ranked_ids = {item["job_id"] for item in ranking}
    missing = all_job_ids - ranked_ids

    # 누락 있으면 재질의 1회
    if missing:
        all_warnings.append(f"누락 job_id 감지, 재질의: {sorted(missing)}")
        ranking2, warnings2 = _ask_listwise(compressed_jobs, call_fn)
        all_warnings.extend(warnings2)

        # 재질의 결과에서 누락됐던 것 중 이번에 포함된 것 흡수
        seen_after_retry: set[str] = {item["job_id"] for item in ranking}
        for item in ranking2:
            jid = item["job_id"]
            if jid in missing and jid not in seen_after_retry:
                ranking.append(item)
                seen_after_retry.add(jid)

    # 최종 누락 확인 — 여전히 없으면 (fit_level, DOM_RANK) 기준 안전 삽입
    ranked_ids = {item["job_id"] for item in ranking}
    still_missing = all_job_ids - ranked_ids

    if still_missing:
        all_warnings.append(
            f"재질의 후에도 누락 잔존, 안전 배치: {sorted(still_missing)}"
        )
        ranking = _safe_insert_missing(ranking, still_missing, fits, domain_ctx)

    return ranking, all_warnings


# ---------------------------------------------------------------------------
# _safe_insert_missing (SPEC §7-3 — 맨끝 blind append 금지)
# ---------------------------------------------------------------------------


def _safe_insert_missing(
    ranking: list[dict[str, str]],
    missing: set[str],
    fits: dict[str, dict[str, Any]],
    domain_ctx: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    """누락 job_id를 (fit_level, DOM_RANK) 기준으로 적절 위치에 삽입한다.

    맨끝 blind append 금지 — 기존 ranking의 각 항목 fit/dom과 비교해
    누락 항목보다 낮은 fit/dom을 가진 첫 위치 앞에 삽입한다.

    삽입 키: key = (-fit_level, -DOM_RANK) — 내림차순 (높을수록 앞)
    """
    result = list(ranking)

    def _key(jid: str) -> tuple[int, int]:
        fit_level = int(fits.get(jid, {}).get("level", 1))
        dom = domain_ctx.get(jid, {}).get("domain_alignment", "weak")
        dom_rank = DOM_RANK.get(dom, 0)
        return (-fit_level, -dom_rank)

    # fit이 높은 것부터 처리해야 삽입 위치가 안정적으로 결정된다
    for jid in sorted(missing, key=_key):
        jid_key = _key(jid)
        # jid보다 낮은 fit/dom(= 더 큰 negated key)을 가진 첫 항목 앞에 삽입한다.
        # 찾지 못하면 맨끝(jid가 전체 중 가장 낮은 fit/dom). `<=`는 더 좋은 항목 앞에
        # 끼워넣어 누락 job을 맨앞으로 보내는 버그였으므로 `>`로 수정.
        insert_pos = len(result)
        for i, item in enumerate(result):
            if _key(item["job_id"]) > jid_key:
                insert_pos = i
                break

        result.insert(
            insert_pos,
            {"job_id": jid, "reason": "safe_placement (fit/domain key)"},
        )

    return result
