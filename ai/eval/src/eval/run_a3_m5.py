"""eval/run_a3_m5.py — A-3 τ M5 확대 표본 실행 (T-069).

run_a3_report(): 창업자 수기 랭킹 라벨(a3_labels_m5.json)을
로드해 a3_tau.run_a3로 Kendall τ·위반율·판정(PROCEED/CONDITIONAL/NOGO)을 산출하고
m5_cost_and_a3.json의 'a3' 섹션으로 병합한다. 라벨 부재 시 FileNotFoundError.

A-3 τ는 선택 게이트(M5 §5) — 졸업 비차단. τ<0.6(NOGO) 시 F5 범위 재검토 알림.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from eval.a3_tau import TauReport, run_a3

# src/eval/run_a3_m5.py → parent×3 = ai/eval (fixtures·reports 위치)
_EVAL_ROOT = Path(__file__).parent.parent.parent
_FIXTURE_LABELS = _EVAL_ROOT / "fixtures" / "m5_expanded" / "a3_labels_m5.json"
_REPORT_PATH = _EVAL_ROOT / "reports" / "m5_cost_and_a3.json"


def run_a3_report(
    labels_path: Path = _FIXTURE_LABELS,
    report_path: Path = _REPORT_PATH,
) -> TauReport:
    """수기 랭킹 라벨 → A-3 τ 판정 → m5_cost_and_a3.json 'a3' 병합. 라벨 부재 시 raise.

    labels_path JSON: {"human_order": [job_id...], "model_ranking": {job_id: rank}}.
    """
    if not labels_path.exists():
        raise FileNotFoundError(
            f"A-3 라벨 파일 없음: {labels_path}. 창업자 수기 랭킹 라벨 입력 필요"
            " (README — A-3는 선택 게이트, 졸업 비차단)."
        )

    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    human_order: list[str] = labels["human_order"]
    model_ranking: dict[str, int] = labels["model_ranking"]

    report = run_a3(human_order=human_order, model_ranking=model_ranking)

    existing: dict[str, Any] = {}
    if report_path.exists():
        existing = json.loads(report_path.read_text(encoding="utf-8"))
    existing["a3"] = asdict(report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if report.verdict == "NOGO":  # 사용자 알림(자동 조치 없음 — F5 범위 재검토 결정)
        print(
            f"[A-3 NOGO] τ={report.tau:.3f} violation_rate={report.violation_rate:.1%}"
            " — F5 제품화 범위 재검토 필요(사용자 결정)."
        )
    return report


if __name__ == "__main__":  # pragma: no cover — 수기 실행 진입점
    _r = run_a3_report()
    print(f"A-3 τ={_r.tau:.3f} verdict={_r.verdict} n_pairs={_r.n_pairs}")
