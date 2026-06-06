"""worker/matching.py — 요구↔근거 매칭표 생성 (SPEC §6-1, T-006).

build_matching_table: LLM(requirement_evidence_match) 호출 →
  - _resolve_evidence: 존재하는 id만 남기고 exact_quote verbatim 복사(구성상 추출형).
  - 요구당 정확히 1행 보장 (누락 backfill + 권위 메타데이터 덮어쓰기).
  - _needs_rematch 판정 후 1회 rematch(rematch_evidence) 재시도.
  - 재시도 후에도 유효 근거 없으면: over-claim → invalid_match=True, genuine miss 유지.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from core.models import (
    EvidenceItem,
    JobPosting,
    MatchingTable,
    MatchRow,
    Requirement,
)
from worker._prompts import load_prompt, render
from worker.llm import JSON_SYSTEM, call_structured

# SPEC §6-1: same-category 그룹 재시도 대상 카테고리
GROUP_CATEGORIES: set[str] = {
    "state_management",
    "styling",
    "data_fetching",
    "build_tooling",
    "testing",
    "framework",
    "language",
}


def _resolve_evidence(
    matched_ids: list[str],
    evidence_map: dict[str, EvidenceItem],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """존재하는 id만 남기고 exact_quote·source_section을 verbatim 복사한다.

    GS-2 1차 보증. 반환: (valid_ids, invalid_ids, quotes, source_sections)
    """
    valid_ids: list[str] = []
    invalid_ids: list[str] = []
    quotes: list[str] = []
    source_sections: list[str] = []
    for eid in matched_ids:
        item = evidence_map.get(eid)
        if item is not None:
            valid_ids.append(eid)
            quotes.append(item.exact_quote)
            source_sections.append(item.source_section)
        else:
            invalid_ids.append(eid)
    return valid_ids, invalid_ids, quotes, source_sections


def _needs_rematch(row: MatchRow) -> bool:
    """SPEC §6-1: missing/weak same-category 그룹 false-negative 재시도 조건.

    유효 근거가 이미 있는 행은 재시도하지 않는다 (프로토타입 _needs_rematch(has_valid)
    동작 복원). 증거 있는 weak 행까지 재매칭하면 LLM 호출 분산이 커지고, rematch가
    weak→direct로 올려 fit이 baseline 대비 흔들릴 수 있다 (REV: 검증 동작 보존).

    (b) critical/required인데 same-category 그룹(category in GROUP_CATEGORIES 또는
        alternatives 보유)이 missing/weak으로 왔고, 유효 근거가 0인 경우만 재시도.
    (over-claim = 매칭 주장했으나 유효 근거 0인 행은 호출부 was_overclaim이 별도 처리.)
    """
    if row.matched_evidence_ids:
        return False  # 이미 유효 근거 있음 → 재시도 불필요 (has_valid 가드)
    if row.requirement_type not in ("critical", "required"):
        return False
    if row.match_level not in ("missing", "weak"):
        return False
    if row.requirement_category in GROUP_CATEGORIES:
        return True
    # alternatives가 있는 경우도 same-category 그룹으로 간주
    if row.alternatives:
        return True
    return False


def _row_from_req(req: Requirement) -> MatchRow:
    """Requirement에서 backfill용 missing 행을 생성한다."""
    return MatchRow(
        **req.model_dump(),
        matched_evidence_ids=[],
        evidence_quotes=[],
        evidence_source_sections=[],
        match_level="missing",
        confidence="low",
        explanation="",
        risk_note="",
    )


def _apply_authority_metadata(row: MatchRow, req: Requirement) -> MatchRow:
    """권위 메타데이터(Requirement에서 온 분류 값)를 덮어쓴다.

    LLM이 requirement_type 등을 잘못 출력해도 원본 Requirement 값이 우선한다.
    """
    data = row.model_dump()
    authority_fields = (
        "requirement_type",
        "requirement_nature",
        "requirement_origin",
        "prerequisite_status",
        "alternatives",
        "requirement_category",
        "alternative_match_policy",
        "requirement_text",
    )
    for field in authority_fields:
        data[field] = getattr(req, field)
    return MatchRow(**data)


def _validate_match_response(data: Any) -> dict[str, Any]:
    """call_structured validate 콜백 — matches 키를 포함하는 dict인지 확인."""
    if not isinstance(data, dict):
        raise ValueError(f"dict 필요, got {type(data).__name__}")
    if "matches" not in data:
        raise ValueError("'matches' 키 없음")
    return data


def _validate_rematch_response(data: Any) -> dict[str, Any]:
    """rematch call_structured validate 콜백."""
    if not isinstance(data, dict):
        raise ValueError(f"dict 필요, got {type(data).__name__}")
    if "matched_evidence_ids" not in data:
        raise ValueError("'matched_evidence_ids' 키 없음")
    return data


def _do_rematch(
    row: MatchRow,
    evidence_map: dict[str, EvidenceItem],
    *,
    _call_fn: Callable[..., Any] | None = None,
) -> MatchRow:
    """1회 rematch 재시도 — 실패 시 원 row 반환."""
    template = load_prompt("rematch_evidence")
    evidence_json = json.dumps(
        [
            {
                "evidence_id": e.evidence_id,
                "title": e.title,
                "exact_quote": e.exact_quote,
                "normalized_summary": e.normalized_summary,
                "skills": e.skills,
                "domain": e.domain,
                "strength": e.strength,
            }
            for e in evidence_map.values()
        ],
        ensure_ascii=False,
    )
    user = render(
        template,
        REQUIREMENT_TEXT=row.requirement_text,
        REQUIREMENT_TYPE=row.requirement_type,
        REQUIREMENT_NATURE=row.requirement_nature,
        ALTERNATIVES=", ".join(row.alternatives) if row.alternatives else "none",
        EVIDENCE=evidence_json,
    )

    call_fn = _call_fn or call_structured
    try:
        result = call_fn(
            system=JSON_SYSTEM,
            user=user,
            validate=_validate_rematch_response,
            max_tokens=2000,
        )
    except Exception:  # noqa: BLE001 — LLM 외부 경계 실패 → genuine miss 유지
        return row

    raw_ids: list[str] = result.get("matched_evidence_ids", [])
    valid_ids, _, quotes, sections = _resolve_evidence(raw_ids, evidence_map)

    from core.models import CONFIDENCES, MATCH_LEVELS, clamp

    match_level = clamp(result.get("match_level", "missing"), MATCH_LEVELS, "missing")
    confidence = clamp(result.get("confidence", "low"), CONFIDENCES, "low")

    data = row.model_dump()
    data.update(
        matched_evidence_ids=valid_ids,
        evidence_quotes=quotes,
        evidence_source_sections=sections,
        match_level=match_level,
        confidence=confidence,
        explanation=result.get("explanation", ""),
        rematched=True,
    )
    return MatchRow(**data)


def build_matching_table(
    job: JobPosting,
    evidence: list[EvidenceItem],
    *,
    _call_fn: Callable[..., Any] | None = None,
) -> MatchingTable:
    """SPEC §6-1: 요구↔근거 매칭표 생성.

    1. LLM(requirement_evidence_match) 호출 → matches 목록.
    2. _resolve_evidence: id 검증 + exact_quote verbatim 복사.
    3. 누락 요구 backfill (missing/low) + 권위 메타데이터 덮어쓰기.
    4. _needs_rematch 판정 → 1회 rematch.
    5. rematch 후에도 유효 근거 없으면: over-claim → invalid_match, genuine miss 유지.
    """
    evidence_map: dict[str, EvidenceItem] = {e.evidence_id: e for e in evidence}
    all_reqs: list[Requirement] = job.all_requirements()
    req_map: dict[str, Requirement] = {r.requirement_id: r for r in all_reqs}

    # --- 1. LLM 호출 ---
    template = load_prompt("requirement_evidence_match")
    evidence_json = json.dumps(
        [
            {
                "evidence_id": e.evidence_id,
                "title": e.title,
                "exact_quote": e.exact_quote,
                "normalized_summary": e.normalized_summary,
                "skills": e.skills,
                "domain": e.domain,
                "strength": e.strength,
            }
            for e in evidence
        ],
        ensure_ascii=False,
    )
    req_json = json.dumps(
        [
            {
                "requirement_id": r.requirement_id,
                "requirement_text": r.requirement_text,
                "requirement_type": r.requirement_type,
                "requirement_nature": r.requirement_nature,
                "prerequisite_status": r.prerequisite_status,
                "alternatives": r.alternatives,
                "requirement_category": r.requirement_category,
                "alternative_match_policy": r.alternative_match_policy,
            }
            for r in all_reqs
        ],
        ensure_ascii=False,
    )
    user = render(
        template,
        COMPANY=job.company,
        TITLE=job.title,
        REQUIREMENTS=req_json,
        EVIDENCE=evidence_json,
    )

    # AI/ML 직군은 요구사항이 많고 reasoning 토큰이 예산을 먹으므로 여유를 둔다
    # (프로토타입 검증값 — 잘림 시 행 누락 → missing backfill → fit 하락).
    call_fn = _call_fn or call_structured
    llm_result = call_fn(
        system=JSON_SYSTEM,
        user=user,
        validate=_validate_match_response,
        max_tokens=16000,
    )

    # --- 2. LLM 응답 → MatchRow 목록 (id 검증 + verbatim 복사) ---
    from core.models import CONFIDENCES, MATCH_LEVELS, clamp

    rows_by_id: dict[str, MatchRow] = {}
    for m in llm_result.get("matches", []):
        rid = m.get("requirement_id", "")
        if rid not in req_map:
            continue  # 알 수 없는 requirement_id는 무시
        req = req_map[rid]
        raw_ids: list[str] = m.get("matched_evidence_ids", [])
        valid_ids, invalid_ids, quotes, sections = _resolve_evidence(
            raw_ids, evidence_map
        )

        match_level = clamp(m.get("match_level", "missing"), MATCH_LEVELS, "missing")
        confidence = clamp(m.get("confidence", "low"), CONFIDENCES, "low")

        risk_note = m.get("risk_note", "")
        if invalid_ids:
            # 존재하지 않는 id가 있었음을 risk_note에 기록
            ghost_note = f"존재하지 않는 evidence_id 무시됨: {invalid_ids}"
            risk_note = f"{risk_note}; {ghost_note}".lstrip("; ")

        # model_validate(dict): LLM 파생 str(match_level/confidence)을 Literal 필드에
        # 넘기되 clamp validator가 coerce — strict 정합 (ADR-102 D3).
        row = MatchRow.model_validate(
            {
                **req.model_dump(),
                "matched_evidence_ids": valid_ids,
                "evidence_quotes": quotes,
                "evidence_source_sections": sections,
                "match_level": match_level,
                "confidence": confidence,
                "explanation": m.get("explanation", ""),
                "risk_note": risk_note,
            }
        )
        rows_by_id[rid] = row

    # --- 3. 누락 요구 backfill + 권위 메타데이터 덮어쓰기 ---
    for rid, req in req_map.items():
        if rid not in rows_by_id:
            rows_by_id[rid] = _row_from_req(req)
        else:
            rows_by_id[rid] = _apply_authority_metadata(rows_by_id[rid], req)

    # --- 4. rematch 판정 + 1회 재시도 ---
    for rid, row in rows_by_id.items():
        req = req_map[rid]
        # over-claim: 매칭을 주장(match_level != missing)했으나 유효 근거 0
        was_overclaim = (
            row.match_level != "missing"
            and not row.matched_evidence_ids
            and row.match_level  # 방어
        )
        if was_overclaim or _needs_rematch(row):
            rematched = _do_rematch(row, evidence_map, _call_fn=_call_fn)
            if rematched.matched_evidence_ids:
                rows_by_id[rid] = rematched
            elif was_overclaim:
                # 재시도 후에도 유효 근거 없음 → invalid_match
                data = row.model_dump()
                data.update(
                    matched_evidence_ids=[],
                    evidence_quotes=[],
                    evidence_source_sections=[],
                    match_level="missing",
                    confidence="low",
                    invalid_match=True,
                    rematched=True,
                    risk_note=(
                        (row.risk_note + "; " if row.risk_note else "")
                        + "over-claim: rematch 후에도 유효 근거 없음"
                    ),
                )
                rows_by_id[rid] = MatchRow(**data)
            else:
                # genuine miss — 그대로 유지 (rematched 플래그만 업데이트)
                data = row.model_dump()
                data["rematched"] = True
                rows_by_id[rid] = MatchRow(**data)

    # 원본 요구사항 순서 보존
    rows = [rows_by_id[r.requirement_id] for r in all_reqs]

    return MatchingTable(
        job_id=job.job_id,
        company=job.company,
        title=job.title,
        rows=rows,
    )
