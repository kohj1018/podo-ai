"""T-030 AC-2: load_prompt / render 단일 모듈 행동 불변 검증.

parse_resume·parse_job·verify_matches·matching 4곳이 쓰던
_load_prompt / _render가 단일 worker._prompts 모듈로 수렴한다.
"""

from worker._prompts import load_prompt, render


def test_AC_2_render_substitutes_placeholders() -> None:
    """{{VAR}} 플레이스홀더를 kwargs 값으로 치환한다 (SPEC §7-1)."""
    out = render("Hello {{NAME}}, age {{AGE}}", NAME="유진", AGE=25)
    assert out == "Hello 유진, age 25"


def test_AC_2_render_no_placeholder_unchanged() -> None:
    """플레이스홀더가 없으면 원문 그대로 반환한다."""
    assert render("no vars here") == "no vars here"


def test_AC_2_load_prompt_reads_existing() -> None:
    """존재하는 프롬프트 파일을 읽는다 (resume_extract.md는 T-005에서 이식됨)."""
    text = load_prompt("resume_extract")
    assert isinstance(text, str)
    assert len(text) > 0


def test_AC_2_load_prompt_single_source() -> None:
    """4개 모듈이 쓰던 프롬프트를 단일 load_prompt로 모두 로드한다."""
    for name in [
        "resume_extract",
        "jd_extract",
        "match_verifier",
        "rematch_evidence",
        "requirement_evidence_match",
    ]:
        assert len(load_prompt(name)) > 0
