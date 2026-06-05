"""worker/parse_job.py — JD 구조화 (SPEC §7-2).

structure_job: LLM(jd_extract) → JobPosting(role_family + requirements/preferred).
_apply_prerequisite_defaults: prerequisite_status 누락 시 보수적 default
  (behavioral → behavioral_preference, 그 외 → prerequisite).
_ensure_unique_ids: 리스트 내 requirement_id 유일성 보장.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from core.models import JobPosting

_PROMPTS_DIR = Path(__file__).parent / "prompts"

# JD 원문 컷오프 (SPEC §7-2)
MAX_RAW_CHARS = 12000


def _load_prompt(name: str) -> str:
    """prompts/<name>.md 파일을 읽어 반환한다."""
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _render(template: str, **kwargs: object) -> str:
    """{{VAR}} 플레이스홀더를 치환한다."""
    result = template
    for key, value in kwargs.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


def _apply_prerequisite_defaults(
    reqs_raw: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """prerequisite_status 누락 시 default 적용 (SPEC §7-2 — 보수적).

    - 이미 명시된 prerequisite_status는 그대로 둔다.
    - requirement_nature == "behavioral" → "behavioral_preference".
    - 그 외 → "prerequisite" (책임[product_duty]을 prereq로 승격하지 않음).
    """
    for req in reqs_raw:
        if req.get("prerequisite_status"):
            continue
        if req.get("requirement_nature") == "behavioral":
            req["prerequisite_status"] = "behavioral_preference"
        else:
            req["prerequisite_status"] = "prerequisite"
    return reqs_raw


def _ensure_unique_ids(reqs_raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """리스트 내 requirement_id 충돌 시 _x suffix로 유일성 보장 (SPEC §7-2)."""
    seen: set[str] = set()
    for req in reqs_raw:
        rid = str(req.get("requirement_id", ""))
        while rid in seen:
            rid = f"{rid}_x"
        req["requirement_id"] = rid
        seen.add(rid)
    return reqs_raw


def structure_job(
    job_id: str,
    company: str,
    title: str,
    url: str,
    raw_text: str,
    *,
    _call_fn: Callable[..., Any] | None = None,
) -> JobPosting:
    """LLM(jd_extract)으로 JD를 구조화해 JobPosting을 반환한다 (SPEC §7-2).

    job_id/company/title/url은 Collector가 제공한 known fields(LLM이 만들지 않음).
    LLM은 role_family·requirements·preferred_requirements 등 분류만 산출한다.
    _call_fn: 테스트용 주입 (기본값 = call_structured).
    """
    from worker.llm import JSON_SYSTEM, call_structured

    template = _load_prompt("jd_extract")
    user = _render(
        template,
        COMPANY=company,
        TITLE=title,
        URL=url,
        RAW_TEXT=raw_text[:MAX_RAW_CHARS],
    )

    def _validate(data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data.get("requirements"), list):
            raise ValueError("requirements 리스트 없음 또는 리스트가 아님")
        return data

    fn = _call_fn or call_structured
    result = fn(
        system=JSON_SYSTEM,
        user=user,
        validate=_validate,
        max_tokens=4096,
        cache_label="jd_extract",
    )

    reqs = _ensure_unique_ids(
        _apply_prerequisite_defaults(list(result.get("requirements", [])))
    )
    prefs = _ensure_unique_ids(
        _apply_prerequisite_defaults(list(result.get("preferred_requirements", [])))
    )

    return JobPosting.model_validate(
        {
            "job_id": job_id,
            "company": company,
            "title": title,
            "url": url,
            "role_family": result.get("role_family", "other"),
            "employment_type": result.get("employment_type") or None,
            "location": result.get("location") or None,
            "team": result.get("team") or None,
            "seniority": result.get("seniority") or None,
            "tech_stack": result.get("tech_stack", []),
            "responsibilities": result.get("responsibilities", []),
            "hard_constraints": result.get("hard_constraints", []),
            "requirements": reqs,
            "preferred_requirements": prefs,
            "raw_text": raw_text,
        }
    )
