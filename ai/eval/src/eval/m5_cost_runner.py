"""eval/m5_cost_runner.py — M5 확대 fixture 비용 회귀 실행 (T-069).

run_cost_regression(): m5_expanded JD를 N 전체 vs K 후보로 스코어링하며 LLM 토큰·호출
수를 계측해 m5_cost_and_a3.json의 'cost' 섹션으로 산출한다. 실 LLM 비호출(mock 토큰
추정 — 결정적). 실 토큰 계측은 M6 라이브 run에서 token_counter 콜백으로 회수.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from eval.cost_regression import CostReport, measure_cost

_REPORT_PATH = Path(__file__).parent.parent.parent / "reports" / "m5_cost_and_a3.json"

# JD당 deep 분석 LLM 단계 수(SPEC §2: 구조화·매칭·검증 ≈ 2/4/5).
_CALLS_PER_JD = 4


def _estimate_scoring_fn(
    jobs: list[dict[str, Any]], counter: dict[str, int]
) -> list[dict[str, Any]]:
    """mock 스코어링 — JD raw_text 길이로 토큰을 추정하고 호출 수를 누적(결정적)."""
    results: list[dict[str, Any]] = []
    for i, job in enumerate(jobs):
        counter["tokens"] = counter.get("tokens", 0) + max(
            1, len(job.get("raw_text", ""))
        )
        counter["calls"] = counter.get("calls", 0) + _CALLS_PER_JD
        results.append(
            {
                "job_id": job["job_id"],
                "fit_level": 3,
                "rank": i + 1,
                "evidence": [],
                "result": "scored",
            }
        )
    return results


def run_cost_regression(fixture_dir: Path) -> CostReport:
    """m5_expanded JD로 N 전체 vs K 후보 비용 비교 → m5_cost_and_a3.json 'cost' 병합."""
    jd_files = sorted((fixture_dir / "jds").glob("*.json"))
    jds = [json.loads(f.read_text(encoding="utf-8")) for f in jd_files]
    # K 후보 = 절반(최소 1) — 실제는 prefilter K_max 산출이나 측정용 비율 시연.
    k = max(1, len(jds) // 2)

    report = measure_cost(
        scoring_fn=_estimate_scoring_fn,
        resumes=[{"resume_id": "r_m5", "raw_text": "측정용 단일 이력서"}],
        jd_sets_n=jds,
        jd_sets_k=jds[:k],
    )

    existing: dict[str, Any] = {}
    if _REPORT_PATH.exists():
        existing = json.loads(_REPORT_PATH.read_text(encoding="utf-8"))
    cost = asdict(report)
    cost.pop("k_results", None)  # 결과 본문은 리포트에 미저장(요약 수치만)
    existing["cost"] = cost
    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report
