"""worker/grounding.py — GS-2 grounding 원시 연산 공개 모듈 (T-031, per ADR-103).

eval 및 worker 내부가 공통으로 의존하는 leaf 모듈.
외부 의존 없음 — 순환 불가.
"""

from __future__ import annotations

import re

from core.models import EvidenceItem


def _norm(text: str) -> str:
    """whitespace 접고 lower. 추출형 체크의 정규화 기준 (SPEC §6-2)."""
    return re.sub(r"\s+", " ", text).strip().lower()


def build_haystack(resume_raw_text: str, evidence: list[EvidenceItem]) -> str:
    """이력서 raw_text + evidence exact_quote + normalized_summary를 정규화해 합친다.

    is_extractive의 검색 대상(haystack). substring 검색이므로 단일 문자열로 연결.
    """
    parts = [_norm(resume_raw_text)]
    for item in evidence:
        parts.append(_norm(item.exact_quote))
        parts.append(_norm(item.normalized_summary))
    # 공백 구분자로 합침 — 개별 span 경계가 연결되어도 substring 탐색에 영향 없음
    return " ".join(parts)


def is_extractive(quote: str, haystack: str) -> bool:
    """정규화된 인용이 haystack에 substring으로 존재하는지 확인한다."""
    return _norm(quote) in haystack
