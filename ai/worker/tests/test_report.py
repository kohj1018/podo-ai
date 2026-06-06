"""QA-M2-001: build_report가 pending_job_ids를 결정적으로(정렬) 직렬화 (GS-1-through-DB)."""

from __future__ import annotations

from worker.report import build_report


def test_pending_job_ids_sorted_deterministic() -> None:
    # set→list 순서는 PYTHONHASHSEED로 프로세스간 비결정 → 정렬해야 result JSONB byte-identical.
    payload = {"pending_job_ids": {"10", "2", "1", "33"}}
    report = build_report(payload)
    assert report["pending_job_ids"] == sorted({"10", "2", "1", "33"})
    # 동일 입력 → 동일 출력(결정성)
    assert build_report(payload)["pending_job_ids"] == report["pending_job_ids"]
