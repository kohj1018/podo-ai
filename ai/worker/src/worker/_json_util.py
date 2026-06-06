"""worker/_json_util.py — JSON 추출 단일 출처 (per ADR-104).

compare_pairwise._extract_json · llm._extract_json ·
rerank_listwise._extract_json_raw 세 곳의 중복 구현을 통합한다.

동작: code-fence 제거 → 첫 { 또는 [ 부터 마지막 } 또는 ] 까지 greedy shrink.
실패 시 ValueError.
"""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json(text: str) -> Any:
    """응답에서 JSON을 추출한다 — code fence 제거 + greedy shrink (SPEC §8-1).

    실패 시 ValueError를 raise한다.
    """
    # code fence 제거
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    # 첫 { 또는 [ 부터 마지막 } 또는 ] 까지 greedy shrink
    for start_ch, end_ch in [("{", "}"), ("[", "]")]:
        start = cleaned.find(start_ch)
        end = cleaned.rfind(end_ch)
        if start != -1 and end != -1 and end >= start:
            return json.loads(cleaned[start : end + 1])
    raise ValueError(f"JSON을 찾을 수 없음: {text[:120]!r}")
