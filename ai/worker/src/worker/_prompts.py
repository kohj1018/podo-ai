"""worker/_prompts.py — 프롬프트 로딩/렌더 단일 출처 (per ADR-104).

parse_resume · parse_job · verify_matches · matching 네 곳의 중복
_load_prompt / _render 구현을 통합한다. leaf 모듈(worker 내부 import 0).

경로 보존: `Path(__file__).parent / "prompts"` — 본 모듈이 worker/ 안에 있어
기존 4개 파일과 동일하게 worker/prompts/ 를 가리킨다.
"""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """prompts/<name>.md 파일을 읽어 반환한다 (SPEC §7-1)."""
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def render(template: str, **kwargs: object) -> str:
    """{{VAR}} 플레이스홀더를 치환한다 (SPEC §7-1)."""
    result = template
    for key, value in kwargs.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result
