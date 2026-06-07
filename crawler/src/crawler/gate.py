"""T-062 A-1형 게이트 검사 — 차단/구조변경 감지 + 어댑터 위임.

새 소스가 "수집 중"으로 승격되려면 이 게이트를 통과해야 한다(DISCOVERY A-1).
실제 fetch는 어댑터가 수행하고, 어댑터의 gate_check()가 여기의 감지 헬퍼를 호출한다.
"""

from __future__ import annotations

from typing import Any

from crawler.adapters.base import BaseCrawlerAdapter, GateResult

# 차단 감지 임계
BLOCK_STATUS_CODES: frozenset[int] = frozenset({403, 429})
CAPTCHA_KEYWORDS: tuple[str, ...] = (
    "captcha",
    "recaptcha",
    "are you human",
    "verify you are",
    "cf-challenge",
)
# 구조변경 감지: 필수 필드 parse 실패율 ≥ 30%
PARSE_FAILURE_THRESHOLD: float = 0.30


def detect_block(status_code: int, body: str = "") -> str | None:
    """차단 감지: HTTP 403/429 또는 body 내 CAPTCHA 키워드 → 사유 or None."""
    if status_code in BLOCK_STATUS_CODES:
        return f"HTTP {status_code} blocked"
    low = body.lower()
    for kw in CAPTCHA_KEYWORDS:
        if kw in low:
            return f"CAPTCHA detected ({kw})"
    return None


def parse_failure_rate(records: list[Any], required_keys: tuple[str, ...]) -> float:
    """필수 키 중 하나라도 누락한 레코드 비율(구조변경 신호)."""
    if not records:
        return 0.0
    missing = sum(1 for r in records if not all(k in r for k in required_keys))
    return missing / len(records)


def detect_structure_change(
    records: list[Any], required_keys: tuple[str, ...]
) -> str | None:
    """구조변경 감지: 필수 필드 parse 실패율 ≥ 임계 → 사유 문자열, 아니면 None."""
    rate = parse_failure_rate(records, required_keys)
    if rate >= PARSE_FAILURE_THRESHOLD:
        pct = int(PARSE_FAILURE_THRESHOLD * 100)
        return f"parse failure rate {rate * 100:.1f}% >= {pct}%"
    return None


def run_gate_check(adapter: BaseCrawlerAdapter) -> GateResult:
    """어댑터의 gate_check()를 실행해 차단/구조변경 여부를 GateResult로 반환한다.

    소스 status 갱신("수집 중"↔"수집 실패")의 단일 진입점.
    """
    return adapter.gate_check()
