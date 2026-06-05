"""T-010: pairwise 비교 (SPEC §7-4).

_compare_once: 단일 방향(A vs B) LLM 호출 → winner(a/b/tie) + confidence clamp.
run_pairwise: 모든 후보 쌍을 A/B·B/A 양방향 비교.
    agreed(양방향 일치)이면 outcome=공통 승자 job_id, confidence=min.
    불일치이면 outcome=tie, confidence=low (순서 편향 차단).
"""

from __future__ import annotations

import json
import re
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

from core.models import CONFIDENCES, MatchingTable, PairwiseResult, clamp
from worker.rerank_listwise import compress_table

# pairwise_compare 프롬프트 (T-005에서 verbatim 이식됨)
_PROMPT_PATH = Path(__file__).parent / "prompts" / "pairwise_compare.md"
_PROMPT_TEMPLATE: str = _PROMPT_PATH.read_text(encoding="utf-8")

# JSON_SYSTEM (SPEC §8-1) — 프로토타입 검증 문구(추출형·사실성 지시 포함).
_JSON_SYSTEM = (
    "You are a careful, literal information-extraction and evaluation engine. "
    "You follow instructions exactly, never invent facts, and output ONLY valid JSON "
    "with no extra text, no markdown, and no code fences."
)

# confidence 우선순위 (낮은 것 선택용)
_CONF_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


def _extract_json(text: str) -> Any:
    """응답에서 JSON을 추출한다 (순환 import 방지로 로컬 구현)."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    for start_ch, end_ch in [("{", "}"), ("[", "]")]:
        start = cleaned.find(start_ch)
        end = cleaned.rfind(end_ch)
        if start != -1 and end != -1 and end >= start:
            return json.loads(cleaned[start : end + 1])
    raise ValueError(f"JSON을 찾을 수 없음: {text[:120]!r}")


def _compare_once(
    compressed_a: dict[str, Any],
    compressed_b: dict[str, Any],
    call_fn: Callable[..., str],
) -> tuple[str, str]:
    """단일 방향(A vs B) LLM 호출 → (winner, confidence).

    winner는 "a" | "b" | "tie" 로 clamp된다.
    confidence는 "high" | "medium" | "low" 로 clamp된다 (PairwiseResult 조립 시
    field_validator가 Confidence Literal로 재확정).
    """
    user_prompt = _PROMPT_TEMPLATE.replace(
        "{{JOB_A}}", json.dumps(compressed_a, ensure_ascii=False)
    ).replace("{{JOB_B}}", json.dumps(compressed_b, ensure_ascii=False))
    raw = call_fn(
        system=_JSON_SYSTEM,
        user=user_prompt,
        max_tokens=800,
        temperature=0.0,
    )
    try:
        data = _extract_json(raw)
    except Exception:
        return "tie", "low"

    raw_winner = data.get("winner", "tie") if isinstance(data, dict) else "tie"
    raw_conf = data.get("confidence", "low") if isinstance(data, dict) else "low"

    winner = clamp(raw_winner, {"a", "b", "tie"}, "tie")
    confidence = clamp(raw_conf, CONFIDENCES, "low")
    return winner, confidence


def run_pairwise(
    tables: dict[str, MatchingTable],
    candidate_ids: list[str],
    domain_ctx: dict[str, dict[str, str]],
    *,
    _call_fn: Callable[..., str] | None = None,
) -> list[PairwiseResult]:
    """모든 후보 쌍을 A/B·B/A 양방향 비교 (SPEC §7-4).

    Args:
        tables: job_id → MatchingTable (압축 전 원본)
        candidate_ids: pairwise 비교 대상 후보 id 목록
        domain_ctx: job_id → {domain_alignment, role_family}
        _call_fn: 테스트용 LLM 주입 인터페이스

    Returns:
        각 (i<j) 쌍에 대한 PairwiseResult 목록 (core.models.PairwiseResult).
            outcome 은 합의 승자의 job_id, 불일치/무승부면 "tie"
            (소비자 rank_aggregate.bradley_terry 가 outcome==job_id 로 판별).
            ab_winner / ba_winner 는 각 방향 승자의 job_id (또는 "tie").
            confidence 는 두 방향 중 낮은 쪽 (불일치면 "low").
    """
    from worker.llm import _openai_call

    call_fn = _call_fn or _openai_call

    results: list[PairwiseResult] = []

    for id_a, id_b in combinations(candidate_ids, 2):
        ctx_a = domain_ctx.get(id_a, {})
        ctx_b = domain_ctx.get(id_b, {})

        compressed_a = compress_table(tables[id_a], ctx_a)
        compressed_b = compress_table(tables[id_b], ctx_b)

        # A/B 방향: a = id_a, b = id_b
        winner_ab_slot, conf_ab = _compare_once(compressed_a, compressed_b, call_fn)

        # B/A 방향: a = id_b, b = id_a (순서 반전)
        winner_ba_raw, conf_ba = _compare_once(compressed_b, compressed_a, call_fn)
        # B/A 프레임에서 winner=a는 id_b가 이겼음 → 원래 프레임(슬롯)으로 변환
        if winner_ba_raw == "a":
            winner_ba_slot = "b"  # B/A 프레임의 a = 원래 id_b
        elif winner_ba_raw == "b":
            winner_ba_slot = "a"  # B/A 프레임의 b = 원래 id_a
        else:
            winner_ba_slot = "tie"

        agreed = winner_ab_slot == winner_ba_slot and winner_ab_slot != "tie"

        if agreed:
            # 합의 승자 슬롯 → job_id (BT 소비자가 outcome==job_id 로 판별)
            outcome = id_a if winner_ab_slot == "a" else id_b
            # confidence = 두 방향 중 낮은 쪽 (SPEC §7-4)
            confidence = (
                conf_ab
                if _CONF_RANK.get(conf_ab, 0) <= _CONF_RANK.get(conf_ba, 0)
                else conf_ba
            )
        else:
            outcome = "tie"
            confidence = "low"

        # 슬롯 라벨 → job_id (PairwiseResult 계약: 식별자는 job_id)
        slot_to_job = {"a": id_a, "b": id_b}
        results.append(
            PairwiseResult.model_validate(
                {
                    "job_a": id_a,
                    "job_b": id_b,
                    "ab_winner": slot_to_job.get(winner_ab_slot, "tie"),
                    "ba_winner": slot_to_job.get(winner_ba_slot, "tie"),
                    "agreed": agreed,
                    "outcome": outcome,
                    "confidence": confidence,
                }
            )
        )

    return results
