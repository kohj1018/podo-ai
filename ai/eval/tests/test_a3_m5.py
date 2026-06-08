"""T-069 A-3 τ M5 확대 표본 테스트.

AC-3: 확대 표본 JD + 수기 랭킹 라벨 → Kendall τ + 자명 페어 위반율 + 판정 라벨.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# AC-3: τ 계산 + 판정 라벨 (합성 라벨 기반 단위 테스트)
# ---------------------------------------------------------------------------


def test_AC_3_tau_verdict_computation() -> None:
    """AC-3: 합성 수기 랭킹 라벨 → compute_tau → 판정 라벨 산출.

    Given: 8개 JD 수기 랭킹 라벨 + 모델 랭킹(완전 일치)
    When: run_a3_report 실행 (run_a3_m5 wrapper)
    Then: Kendall τ + 자명 페어 위반율 산출 + verdict 판정 기록됨.
    """
    from eval.a3_tau import VERDICT_PROCEED, TauReport, run_a3

    human_order = [f"jd-{i}" for i in range(8)]
    model_ranking = {jid: i + 1 for i, jid in enumerate(human_order)}

    report = run_a3(human_order=human_order, model_ranking=model_ranking)

    assert isinstance(report, TauReport)
    assert report.tau == pytest.approx(1.0)
    assert report.verdict == VERDICT_PROCEED
    assert report.n_pairs > 0


def test_AC_3_nogo_verdict_recorded() -> None:
    """AC-3: τ < 0.6 이면 verdict=NOGO가 기록된다.

    Given: 완전 역순 수기 랭킹 라벨
    When: run_a3 실행
    Then: verdict == NOGO 기록됨.
    """
    from eval.a3_tau import VERDICT_NOGO, run_a3

    human_order = ["jd-a", "jd-b", "jd-c", "jd-d"]
    # 모델 역순 → τ = -1.0 → NOGO
    model_ranking = {"jd-a": 4, "jd-b": 3, "jd-c": 2, "jd-d": 1}

    report = run_a3(human_order=human_order, model_ranking=model_ranking)

    assert report.verdict == VERDICT_NOGO


def test_AC_3_run_a3_m5_with_fixture_labels(tmp_path: Path) -> None:
    """AC-3: run_a3_m5가 fixture 라벨 파일을 로드해 TauReport를 반환하고 JSON에 기록한다.

    Given: 합성 a3_labels_m5.json fixture (pair 형식)
    When: run_a3_m5.run_a3_report 실행
    Then: TauReport 반환 + m5_cost_and_a3.json에 a3 섹션이 기록된다.
    """
    from eval.run_a3_m5 import run_a3_report

    # 합성 라벨: human_order + model_ranking 형식
    labels_data = {
        "human_order": ["jd-0", "jd-1", "jd-2", "jd-3", "jd-4"],
        "model_ranking": {"jd-0": 1, "jd-1": 2, "jd-2": 3, "jd-3": 4, "jd-4": 5},
        "note": "합성 테스트용 fixture",
    }
    labels_file = tmp_path / "a3_labels_m5.json"
    labels_file.write_text(json.dumps(labels_data), encoding="utf-8")

    report_path = tmp_path / "m5_cost_and_a3.json"

    tau_report = run_a3_report(
        labels_path=labels_file,
        report_path=report_path,
    )

    # TauReport 반환 확인
    from eval.a3_tau import TauReport

    assert isinstance(tau_report, TauReport)
    assert tau_report.tau == pytest.approx(1.0)
    assert tau_report.verdict == "PROCEED"

    # JSON 기록 확인
    assert report_path.exists(), "m5_cost_and_a3.json 미생성"
    with open(report_path, encoding="utf-8") as f:
        data = json.load(f)

    assert "a3" in data, "a3 섹션 누락"
    assert "tau" in data["a3"]
    assert "verdict" in data["a3"]


def test_AC_3_missing_labels_raises_informative_error(tmp_path: Path) -> None:
    """AC-3: 라벨 파일이 없으면 FileNotFoundError가 발생한다 (사용자 입력 대기 안내).

    WHY: A-3 실데이터는 창업자 수기 라벨이 없으면 실행 불가 — 명확한 에러가
         라벨 입력 필요성을 사용자에게 알린다.
    """
    from eval.run_a3_m5 import run_a3_report

    nonexistent = tmp_path / "missing_labels.json"
    report_path = tmp_path / "out.json"

    with pytest.raises(FileNotFoundError):
        run_a3_report(labels_path=nonexistent, report_path=report_path)
