"""T-011: JSONB 계약 직렬화 (SPEC §12 / ARCH §3-2).

build_report: run_scoring 산출물 → JSONB 계약 dict.
  - 합격확률/% 출력 금지
  - BT="상대 강도, 확률 아님" 명시 보존 (Charter §5 / SPEC §1)
  - NestJS는 이 dict를 파싱하지 않고 그대로 ranking_runs.result에 저장

보존 불변: fit_label이 FIT_LABELS 값을 그대로 쓰고 '%' 없음.
"""

from __future__ import annotations

from typing import Any


def build_report(scoring_result: dict[str, Any]) -> dict[str, Any]:
    """run_scoring 산출물을 JSONB 계약 dict로 직렬화한다.

    Args:
        scoring_result: run_scoring 반환 dict

    Returns:
        ranking_runs.result에 그대로 저장될 JSONB dict.
        합격확률/% 필드 없음. BT="상대 강도" 명시.
    """
    final_ranking = scoring_result.get("final_ranking", {})
    matching_tables = scoring_result.get("matching_tables", {})
    pairwise_comparisons = scoring_result.get("pairwise_comparisons", {})
    pending_job_ids = scoring_result.get("pending_job_ids", set())

    # BT 점수에 "상대 강도, 확률 아님" 메타 부착 (SPEC §1 / Charter §5)
    bt_raw = pairwise_comparisons.get("bradley_terry_scores", {})
    bt_annotated = {
        "scores": bt_raw,
        "interpretation": "상대 적합도 강도 (합격확률 아님)",
    }

    return {
        "schema_version": "v1",
        "final_ranking": {
            "note": final_ranking.get("note", ""),
            "user_profile": final_ranking.get("user_profile", {}),
            "guard_moves": final_ranking.get("guard_moves", []),
            "ranking": final_ranking.get("ranking", []),
        },
        "matching_tables": matching_tables,
        "pairwise_comparisons": {
            "bradley_terry": bt_annotated,
            "candidate_set": pairwise_comparisons.get("candidate_set", []),
            "comparisons": pairwise_comparisons.get("comparisons", []),
        },
        "pending_job_ids": list(pending_job_ids),
    }
