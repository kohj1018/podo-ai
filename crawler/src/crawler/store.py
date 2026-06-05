"""T-012 store — job_postings upsert + diff 계산 + CoverageState.

SPEC §9-1 이식: Collector 소유 테이블 upsert + 전일 대비 신규/유지/마감 diff.
수집 실패는 CoverageState에 반드시 노출 — 조용한 무시 금지 (F-002 Fail #3).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

RawJob = dict[str, str]


# ---------------------------------------------------------------------------
# diff 계산
# ---------------------------------------------------------------------------


def compute_diff(
    yesterday: list[RawJob],
    today: list[RawJob],
) -> dict[str, list[str]]:
    """전일 집합 vs 금일 집합 → 신규/유지/마감 job_id 집합.

    반환 dict 키: "new", "kept", "closed".
    """
    prev_ids = {j["job_id"] for j in yesterday}
    curr_ids = {j["job_id"] for j in today}

    return {
        "new": sorted(curr_ids - prev_ids),
        "kept": sorted(curr_ids & prev_ids),
        "closed": sorted(prev_ids - curr_ids),
    }


# ---------------------------------------------------------------------------
# CoverageState — 수집 실패 노출
# ---------------------------------------------------------------------------


@dataclass
class CoverageState:
    """수집 커버리지 상태. 실패를 조용히 무시하지 않고 기록·노출한다."""

    _failures: list[dict[str, str]] = field(default_factory=list)

    def record_failure(self, source: str, *, error: str) -> None:
        """수집 소스별 실패를 기록하고 로깅한다."""
        entry = {"source": source, "error": error}
        self._failures.append(entry)
        logger.error("fetch_failure source=%s error=%s", source, error)

    def has_failures(self) -> bool:
        return bool(self._failures)

    def get_failures(self) -> list[dict[str, str]]:
        return list(self._failures)


# ---------------------------------------------------------------------------
# upsert (DB 연동 없는 in-memory 구현 — 실 DB는 후속 task에서 연결)
# ---------------------------------------------------------------------------


def upsert_jobs(
    store: dict[str, RawJob],
    jobs: list[RawJob],
) -> None:
    """job_id 기준 upsert. store는 {job_id: raw_job} dict (in-memory 또는 DB 래퍼).

    Collector 소유(§3-2) — 다른 모듈은 읽기만 허용.
    실 DB 연결은 후속 task(T-014 등)에서 store를 교체한다.
    """
    for job in jobs:
        jid = job["job_id"]
        if jid in store:
            logger.debug("upsert_update job_id=%s", jid)
        else:
            logger.debug("upsert_insert job_id=%s", jid)
        store[jid] = job


def collect(
    sources: dict[str, Callable[[], list[RawJob]]],
    store: dict[str, RawJob],
    yesterday: list[RawJob],
    coverage: CoverageState,
) -> dict[str, list[str]]:
    """sources 별 fetch 호출 → upsert + diff 반환. 실패는 coverage에 기록.

    sources: {"toss": callable, "daangn": callable}
    각 callable은 () → list[RawJob] 시그니처.
    """
    today: list[RawJob] = []
    for source_name, fetcher in sources.items():
        try:
            jobs = fetcher()
            today.extend(jobs)
            logger.info("fetch_ok source=%s count=%d", source_name, len(jobs))
        except Exception as exc:  # 시스템 경계 — 외부 HTTP 실패 포착
            coverage.record_failure(source_name, error=str(exc))

    upsert_jobs(store, today)
    return compute_diff(yesterday, today)
