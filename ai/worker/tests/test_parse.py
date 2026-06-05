"""T-005 parse_resume / parse_job TDD 테스트.

AC-1: extract_skills_evidence — LLM 무관 결정적 Skills evidence 보강.
AC-2: 프롬프트 7종이 SPEC 부록 A와 verbatim 동일.
AC-3: structure_job — behavioral prerequisite_status default 규칙.
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# AC-1: extract_skills_evidence — 결정적, LLM 무관
# ---------------------------------------------------------------------------


def test_AC_1_skills_evidence_deterministic():
    """Skills 헤딩 + 불릿이 있는 이력서에서 LLM 없이 evidence가 생성된다."""
    from worker.parse_resume import extract_skills_evidence

    resume_text = """
## Skills
- React, TypeScript, Next.js
- Tailwind CSS, styled-components
- Jest, Vitest
"""
    items = extract_skills_evidence(resume_text)

    # 1개 이상의 evidence 항목이 반환된다
    assert len(items) > 0, (
        "Skills 헤딩 아래 불릿이 있으면 evidence 항목이 생성되어야 한다"
    )

    for item in items:
        assert item.evidence_type == "skills", (
            f"evidence_type이 'skills'여야 함: {item.evidence_type}"
        )
        # exact_quote는 이력서에서 verbatim 복사된 불릿
        assert item.exact_quote in resume_text, (
            f"exact_quote는 이력서 텍스트 내 verbatim span이어야 함: {item.exact_quote!r}"
        )
        # skills 필드는 토큰으로 분해되어야 한다
        assert len(item.skills) > 0, f"skills 토큰 목록이 비어있음: {item}"


# ---------------------------------------------------------------------------
# AC-2: 프롬프트 7종 verbatim 스냅샷 — SPEC 부록 A ↔ 파일 동일성
# ---------------------------------------------------------------------------

_SPEC_PATH = (
    Path(__file__).parents[3] / "docs" / "20-system" / "SCORING_PIPELINE_SPEC.md"
)
_PROMPTS_DIR = Path(__file__).parents[1] / "src" / "worker" / "prompts"

_PROMPT_NAMES = [
    "resume_extract",
    "jd_extract",
    "requirement_evidence_match",
    "rematch_evidence",
    "match_verifier",
    "listwise_rerank",
    "pairwise_compare",
]


def _extract_appendix_a_prompts(spec_text: str) -> dict[str, str]:
    """SPEC 부록 A에서 각 ### A-N. `<name>.md` 섹션의 ```text 펜스 본문을 추출한다."""
    result: dict[str, str] = {}
    # 패턴: ### A-N. `<name>.md` 다음에 오는 ````text ... ```` 블록
    pattern = re.compile(
        r"### A-\d+\.\s+`([^`]+\.md)`\s*\n````text\n(.*?)````",
        re.DOTALL,
    )
    for m in pattern.finditer(spec_text):
        name = m.group(1).removesuffix(".md")
        body = m.group(2)
        result[name] = body
    return result


def _normalize(text: str) -> str:
    """줄 단위 정규화: trailing whitespace 제거 + 말미 개행 제거."""
    lines = [line.rstrip() for line in text.splitlines()]
    # 말미 빈 줄 제거
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def test_AC_2_prompts_verbatim_match_spec_appendix_a():
    """7개 프롬프트 파일이 SPEC 부록 A의 내용과 글자 단위로 동일하다."""
    assert _SPEC_PATH.exists(), f"SPEC 파일을 찾을 수 없음: {_SPEC_PATH}"

    spec_text = _SPEC_PATH.read_text(encoding="utf-8")
    spec_prompts = _extract_appendix_a_prompts(spec_text)

    missing_from_spec = [n for n in _PROMPT_NAMES if n not in spec_prompts]
    assert not missing_from_spec, (
        f"SPEC 부록 A에서 추출 실패한 프롬프트: {missing_from_spec}"
    )

    for name in _PROMPT_NAMES:
        prompt_file = _PROMPTS_DIR / f"{name}.md"
        assert prompt_file.exists(), f"프롬프트 파일이 없음: {prompt_file}"

        file_body = prompt_file.read_text(encoding="utf-8")
        spec_body = spec_prompts[name]

        norm_file = _normalize(file_body)
        norm_spec = _normalize(spec_body)

        assert norm_file == norm_spec, (
            f"{name}.md이 SPEC 부록 A와 다름.\n"
            f"파일 길이={len(norm_file)}, SPEC 길이={len(norm_spec)}"
        )


# ---------------------------------------------------------------------------
# AC-3: structure_job — behavioral prerequisite_status default 규칙
# ---------------------------------------------------------------------------


def test_AC_3_prerequisite_status_default():
    """behavioral nature인데 prerequisite_status 누락 시 behavioral_preference로,
    그 외 누락은 prerequisite로 default된다."""
    from worker.parse_job import _apply_prerequisite_defaults

    reqs_raw = [
        {
            "requirement_id": "R1",
            "requirement_text": "주도적으로 문제를 해결하는 자세",
            "requirement_type": "preferred",
            "requirement_nature": "behavioral",
            # prerequisite_status 없음 → behavioral_preference로 default
        },
        {
            "requirement_id": "R2",
            "requirement_text": "React 3년 이상 경험",
            "requirement_type": "required",
            "requirement_nature": "technical",
            # prerequisite_status 없음 → prerequisite로 default
        },
        {
            "requirement_id": "R3",
            "requirement_text": "결제 SDK 개발 경험",
            "requirement_type": "required",
            "requirement_nature": "domain",
            "prerequisite_status": "prerequisite",  # 명시된 경우 그대로
        },
    ]

    result = _apply_prerequisite_defaults(reqs_raw)

    r1 = next(r for r in result if r["requirement_id"] == "R1")
    r2 = next(r for r in result if r["requirement_id"] == "R2")
    r3 = next(r for r in result if r["requirement_id"] == "R3")

    assert r1["prerequisite_status"] == "behavioral_preference", (
        f"behavioral nature는 behavioral_preference로 default되어야 함: {r1['prerequisite_status']}"
    )
    assert r2["prerequisite_status"] == "prerequisite", (
        f"non-behavioral은 prerequisite로 default되어야 함: {r2['prerequisite_status']}"
    )
    assert r3["prerequisite_status"] == "prerequisite", (
        f"명시된 prerequisite_status는 그대로 유지되어야 함: {r3['prerequisite_status']}"
    )
