"""worker/parse_resume.py — 이력서 evidence 추출 (SPEC §7-1).

extract_evidence: LLM(resume_extract) 호출 → EvidenceItem 목록 반환.
extract_skills_evidence: 결정적 Skills 헤딩 파싱 → LLM 누락 보완 (AC-1 핵심).
  - Skills/기술스택 헤딩 아래 불릿을 코드로 파싱.
  - exact_quote = verbatim 불릿, skills = 토큰 분해.
  - id 충돌 시 _x suffix.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from core.models import EvidenceItem

_PROMPTS_DIR = Path(__file__).parent / "prompts"

# Skills 헤딩으로 인식할 정규식 패턴 (한/영 대소문자 포함)
_SKILLS_HEADING_RE = re.compile(
    r"^#{1,3}\s*(Skills?|기술스택|기술\s*스택|기술|Tech(?:nical)?\s*Skills?|Technical\s*Stack)",
    re.IGNORECASE | re.MULTILINE,
)

# 불릿 라인 패턴 (-, *, •, · 시작)
_BULLET_RE = re.compile(r"^\s*[-*•·]\s+(.+)$")

# 헤딩 패턴 (다음 섹션 시작 감지용)
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S|^\s*[-*•·]\s+\S", re.MULTILINE)
_SECTION_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)


def _load_prompt(name: str) -> str:
    """prompts/<name>.md 파일을 읽어 반환한다."""
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _render(template: str, **kwargs: object) -> str:
    """{{VAR}} 플레이스홀더를 치환한다 (SPEC §7-1)."""
    result = template
    for key, value in kwargs.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


def _parse_bullets_from_section(
    resume_text: str, heading_match: re.Match[str]
) -> list[str]:
    """Skills 헤딩 이후 다음 섹션 헤딩까지의 불릿 라인을 추출한다."""
    start = heading_match.end()
    # 다음 섹션 헤딩(##) 위치 찾기
    next_heading = _SECTION_HEADING_RE.search(resume_text, start)
    section_text = (
        resume_text[start : next_heading.start()]
        if next_heading
        else resume_text[start:]
    )

    bullets: list[str] = []
    for line in section_text.splitlines():
        m = _BULLET_RE.match(line)
        if m:
            bullets.append(m.group(1).strip())
    return bullets


def _tokenize_skills(bullet_text: str) -> list[str]:
    """불릿 텍스트를 쉼표/슬래시로 분해해 스킬 토큰 목록을 반환한다."""
    tokens: list[str] = []
    for part in re.split(r"[,/]", bullet_text):
        tok = part.strip()
        if tok:
            tokens.append(tok)
    return tokens


def extract_skills_evidence(
    resume_text: str,
    existing_ids: set[str] | None = None,
) -> list[EvidenceItem]:
    """결정적 Skills 헤딩 파싱으로 evidence 목록을 반환한다 (LLM 없음 — AC-1).

    - Skills/기술스택 헤딩 아래 불릿 → 각각 EvidenceItem(evidence_type="skills")
    - exact_quote = verbatim 불릿 라인 (이력서 텍스트 내 span)
    - skills = 쉼표/슬래시 분해 토큰
    - id 충돌 시 _x suffix
    """
    if existing_ids is None:
        existing_ids = set()

    items: list[EvidenceItem] = []
    used_ids = set(existing_ids)

    for heading_m in _SKILLS_HEADING_RE.finditer(resume_text):
        bullets = _parse_bullets_from_section(resume_text, heading_m)

        for i, bullet in enumerate(bullets):
            base_id = f"SK{i + 1}"
            eid = base_id
            if eid in used_ids:
                eid = f"{base_id}_x"
            used_ids.add(eid)

            skills = _tokenize_skills(bullet)

            item = EvidenceItem(
                evidence_id=eid,
                title=f"Skills: {bullet[:60]}",
                source_section="Skills",
                exact_quote=bullet,
                normalized_summary=f"Skills evidence: {bullet}",
                skills=skills,
                domain=[],
                evidence_type="skills",
                strength="medium",
                recency=None,
            )
            items.append(item)

    return items


def extract_evidence(
    resume_text: str,
    *,
    _call_fn: Callable[..., Any] | None = None,
) -> list[EvidenceItem]:
    """LLM(resume_extract)으로 evidence를 추출하고 Skills 보강을 수행한다 (SPEC §7-1).

    _call_fn: 테스트용 주입 (기본값 = call_structured).
    """
    from worker.llm import JSON_SYSTEM, call_structured

    template = _load_prompt("resume_extract")
    user = _render(template, RESUME_TEXT=resume_text)

    def _validate(data: dict[str, Any]) -> dict[str, Any]:
        if "evidence" not in data or not isinstance(data["evidence"], list):
            raise ValueError("evidence 키 없음 또는 리스트가 아님")
        return data

    fn = _call_fn or call_structured
    result = fn(
        system=JSON_SYSTEM,
        user=user,
        validate=_validate,
        max_tokens=4096,
        cache_label="resume_extract",
    )

    llm_items: list[EvidenceItem] = []
    existing_ids: set[str] = set()
    for raw in result.get("evidence", []):
        item = EvidenceItem(**raw)
        llm_items.append(item)
        existing_ids.add(item.evidence_id)

    # 결정적 Skills 보강 (SPEC §7-1 — LLM 누락 방지)
    skills_items = extract_skills_evidence(resume_text, existing_ids=existing_ids)

    # skills_debug: _KEY_FRONTEND_SKILLS 존재 점검 (SPEC §7-1)
    skills_debug = [it.evidence_id for it in skills_items]
    if skills_debug:
        pass  # 디버그 목적 — 실제 로깅은 호출자 책임

    return llm_items + skills_items
