"""worker/verify_matches.py — 신뢰 레이어 단계 5 (SPEC §6-2, T-007).

verify_table = _extractive_pass → _llm_verify.

레이어 1 (_extractive_pass): 결정적 추출형 체크.
  - 비추출 인용(이력서/evidence에 substring 없음) 제거 + risk_note.
  - 지지를 주장했으나 추출 인용 0 → invalid_match=True + 레벨 강등 + confidence=low.

레이어 2 (_llm_verify + _apply_verifier): 보수적 LLM verifier.
  - severity를 낮추기만 (new_sev = min(cur, v_sev)). 절대 올리지 않음.
  - downgrade/exaggerated면 추가 -1.
  - confidence = min(cur, v_conf). missing이면 low.

MAX_RESUME_CHARS = 9000 (verifier 프롬프트 이력서 컷오프, SPEC §6-2).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from core.models import (
    CONF_RANK,
    CONFIDENCES,
    MATCH_LEVELS,
    MATCH_SEVERITY,
    SEVERITY_TO_LEVEL,
    EvidenceItem,
    MatchingTable,
    MatchRow,
    Resume,
    clamp,
)
from worker.llm import JSON_SYSTEM, call_structured

MAX_RESUME_CHARS = 9000

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _render(template: str, **kwargs: object) -> str:
    """{{VAR}} 플레이스홀더를 치환한다."""
    result = template
    for key, value in kwargs.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


# ---------------------------------------------------------------------------
# 공개 헬퍼 (T-014 불변식 회귀가 import해 재사용 — 공개 심볼 유지)
# ---------------------------------------------------------------------------


def _norm(text: str) -> str:
    """whitespace 접고 lower. 추출형 체크의 정규화 기준 (SPEC §6-2)."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _build_haystack(resume_raw_text: str, evidence: list[EvidenceItem]) -> str:
    """이력서 raw_text + evidence exact_quote + normalized_summary를 정규화해 합친다.

    _is_extractive의 검색 대상(haystack). substring 검색이므로 단일 문자열로 연결.
    """
    parts = [_norm(resume_raw_text)]
    for item in evidence:
        parts.append(_norm(item.exact_quote))
        parts.append(_norm(item.normalized_summary))
    # 공백 구분자로 합침 — 개별 span 경계가 연결되어도 substring 탐색에 영향 없음
    return " ".join(parts)


def _is_extractive(quote: str, haystack: str) -> bool:
    """정규화된 인용이 haystack에 substring으로 존재하는지 확인한다."""
    return _norm(quote) in haystack


# ---------------------------------------------------------------------------
# 레이어 1: 결정적 추출형 체크
# ---------------------------------------------------------------------------

_DOWNGRADE_MAP: dict[str, str] = {
    "direct": "weak",
    "adjacent": "weak",
    "weak": "missing",
    "missing": "missing",
}


def _extractive_pass(rows: list[MatchRow], resume: Resume) -> list[MatchRow]:
    """SPEC §6-2 레이어 1: 비추출 인용 제거 + 근거 없는 행 invalid 강등.

    각 행의 evidence_quotes에서 haystack(이력서 raw + evidence)에
    substring으로 존재하지 않는 인용을 제거한다.
    지지를 주장했으나(match_level != missing) 추출 인용이 0개로 남으면:
      - invalid_match=True
      - match_level 강등 (direct/adjacent→weak, weak→missing)
      - confidence=low
    """
    haystack = _build_haystack(resume.raw_text, resume.evidence)
    result: list[MatchRow] = []

    for row in rows:
        kept_quotes: list[str] = []
        kept_ids: list[str] = []
        kept_sections: list[str] = []
        removed_notes: list[str] = []

        for idx, quote in enumerate(row.evidence_quotes):
            if _is_extractive(quote, haystack):
                kept_quotes.append(quote)
                if idx < len(row.matched_evidence_ids):
                    kept_ids.append(row.matched_evidence_ids[idx])
                if idx < len(row.evidence_source_sections):
                    kept_sections.append(row.evidence_source_sections[idx])
            else:
                removed_notes.append(f"비추출 인용 제거: {quote[:60]!r}")

        # 지지 주장 + 추출 인용 0 → invalid 강등
        claimed_match = row.match_level != "missing"
        extractive_zero = len(kept_quotes) == 0

        if claimed_match and extractive_zero:
            new_level = _DOWNGRADE_MAP[row.match_level]
            risk_addition = "; ".join(removed_notes) or "추출 인용 없음: invalid 강등"
            data = row.model_dump()
            data.update(
                evidence_quotes=kept_quotes,
                matched_evidence_ids=kept_ids,
                evidence_source_sections=kept_sections,
                match_level=new_level,
                confidence="low",
                invalid_match=True,
                extractive_ok=False,
                risk_note=(
                    (row.risk_note + "; " if row.risk_note else "") + risk_addition
                ),
            )
            result.append(MatchRow(**data))
        else:
            # 정상 또는 missing 행 — extractive_ok 표기
            extractive_ok = len(kept_quotes) > 0 or not claimed_match
            risk_note = row.risk_note
            if removed_notes:
                risk_note = (risk_note + "; " if risk_note else "") + "; ".join(
                    removed_notes
                )
            data = row.model_dump()
            data.update(
                evidence_quotes=kept_quotes,
                matched_evidence_ids=kept_ids,
                evidence_source_sections=kept_sections,
                extractive_ok=extractive_ok,
                risk_note=risk_note,
            )
            result.append(MatchRow(**data))

    return result


# ---------------------------------------------------------------------------
# 레이어 2: 보수적 LLM verifier
# ---------------------------------------------------------------------------


def _validate_verifier_response(data: Any) -> dict[str, Any]:
    """call_structured validate 콜백 — verified 리스트를 포함하는 dict인지 확인."""
    if not isinstance(data, dict):
        raise ValueError(f"dict 필요, got {type(data).__name__}")
    if "verified" not in data:
        raise ValueError("'verified' 키 없음")
    return data


def _apply_verifier(row: MatchRow, v_entry: dict[str, Any]) -> MatchRow:
    """SPEC §6-2 레이어 2: verifier 단일 항목 적용.

    severity는 낮추기만 (min). downgrade/exaggerated면 추가 -1.
    confidence = min(현재, verifier). missing이면 confidence=low.
    절대 올리지 않음.
    """
    cur_sev = MATCH_SEVERITY.get(row.match_level, 0)
    v_level_raw = clamp(
        v_entry.get("match_level", row.match_level), MATCH_LEVELS, row.match_level
    )
    v_sev = MATCH_SEVERITY.get(v_level_raw, cur_sev)

    # min severity = 낮추기만
    new_sev = min(cur_sev, v_sev)

    # downgrade 또는 exaggerated면 추가 -1 (0 미만 클램프)
    if v_entry.get("downgrade") or v_entry.get("exaggerated"):
        new_sev = max(0, new_sev - 1)

    new_level = SEVERITY_TO_LEVEL.get(new_sev, row.match_level)

    # confidence: 낮은 쪽 선택
    cur_conf_rank = CONF_RANK.get(row.confidence, 0)
    v_conf_raw = clamp(
        v_entry.get("confidence", row.confidence), CONFIDENCES, row.confidence
    )
    v_conf_rank = CONF_RANK.get(v_conf_raw, cur_conf_rank)
    new_conf_rank = min(cur_conf_rank, v_conf_rank)
    # 강등 시 medium 이하로 cap
    if new_level != row.match_level:
        new_conf_rank = min(new_conf_rank, CONF_RANK["medium"])
    # missing이면 low 강제
    if new_level == "missing":
        new_conf_rank = CONF_RANK["low"]

    conf_by_rank = {v: k for k, v in CONF_RANK.items()}
    new_conf = conf_by_rank[new_conf_rank]

    verifier_note = v_entry.get("verifier_note", "")
    downgraded = new_level != row.match_level

    data = row.model_dump()
    data.update(
        match_level=new_level,
        confidence=new_conf,
        downgraded=downgraded,
        verifier_note=verifier_note,
    )
    return MatchRow(**data)


def _llm_verify(
    rows: list[MatchRow],
    resume: Resume,
    evidence: list[EvidenceItem],
    *,
    _call_fn: Callable[..., Any] | None = None,
) -> list[MatchRow]:
    """SPEC §6-2 레이어 2: match_verifier LLM 호출 + _apply_verifier 적용."""
    if not rows:
        return rows

    template = _load_prompt("match_verifier")

    resume_text = resume.raw_text[:MAX_RESUME_CHARS]

    evidence_json = json.dumps(
        [
            {
                "evidence_id": e.evidence_id,
                "title": e.title,
                "source_section": e.source_section,
                "exact_quote": e.exact_quote,
                "normalized_summary": e.normalized_summary,
                "evidence_type": e.evidence_type,
                "strength": e.strength,
                "recency": e.recency,
            }
            for e in evidence
        ],
        ensure_ascii=False,
    )

    matches_json = json.dumps(
        [
            {
                "requirement_id": r.requirement_id,
                "requirement_text": r.requirement_text,
                "requirement_type": r.requirement_type,
                "matched_evidence_ids": r.matched_evidence_ids,
                "evidence_quotes": r.evidence_quotes,
                "match_level": r.match_level,
                "confidence": r.confidence,
                "explanation": r.explanation,
                "alternatives": r.alternatives,
                "requirement_category": r.requirement_category,
                "alternative_match_policy": r.alternative_match_policy,
            }
            for r in rows
        ],
        ensure_ascii=False,
    )

    user = _render(
        template,
        RESUME_TEXT=resume_text,
        EVIDENCE=evidence_json,
        MATCHES=matches_json,
    )

    call_fn = _call_fn or call_structured
    try:
        result = call_fn(
            system=JSON_SYSTEM,
            user=user,
            validate=_validate_verifier_response,
            max_tokens=10000,
        )
    except Exception:  # noqa: BLE001 — LLM 외부 경계 실패 → 원 rows 보존
        return rows

    verified_map: dict[str, dict[str, Any]] = {
        v["requirement_id"]: v
        for v in result.get("verified", [])
        if isinstance(v, dict) and "requirement_id" in v
    }

    return [
        _apply_verifier(row, verified_map[row.requirement_id])
        if row.requirement_id in verified_map
        else row
        for row in rows
    ]


# ---------------------------------------------------------------------------
# 공개 진입점
# ---------------------------------------------------------------------------


def verify_table(
    table: MatchingTable,
    resume: Resume,
    *,
    _call_fn: Callable[..., Any] | None = None,
) -> MatchingTable:
    """SPEC §6-2: 신뢰 레이어 2단계 적용.

    레이어 1 (결정적): _extractive_pass.
    레이어 2 (LLM verifier): _llm_verify.
    반환: 동일 job_id/company/title의 새 MatchingTable.
    """
    rows_after_extractive = _extractive_pass(table.rows, resume)
    rows_after_verifier = _llm_verify(
        rows_after_extractive,
        resume,
        resume.evidence,
        _call_fn=_call_fn,
    )
    return MatchingTable(
        job_id=table.job_id,
        company=table.company,
        title=table.title,
        rows=rows_after_verifier,
    )
