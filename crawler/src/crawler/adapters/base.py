"""T-062 ATS 어댑터 공통 인터페이스.

BaseCrawlerAdapter: 모든 ATS/커스텀 어댑터가 구현해야 할 ABC.
GateResult: 게이트 검사 결과 dataclass.
RawJob = dict[str, str] — persistence.upsert_jobs 소비 형태.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

# persistence.py와 동일한 타입 — 크롤러 계층 내 공유
RawJob = dict[str, str]


@dataclass
class GateResult:
    """A-1형 게이트 검사 결과.

    ok=False이면 소스가 차단/구조변경 상태임을 의미한다.
    reason은 차단 원인(예: "HTTP 403 Forbidden", "parse failure rate 40.0% >= 30%").
    """

    ok: bool
    reason: str


class BaseCrawlerAdapter(ABC):
    """ATS/커스텀 어댑터 공통 인터페이스.

    모든 어댑터는 fetch_jobs(location)와 gate_check()를 구현한다.
    location 파라미터는 외국계 한국 채용 필터용 — 구체 적용은 어댑터별(T-071/T-072).
    """

    @abstractmethod
    def fetch_jobs(self, location: str = "KR") -> list[RawJob]:
        """공고 목록을 수집해 RawJob(dict[str,str]) list로 반환한다."""

    @abstractmethod
    def gate_check(self) -> GateResult:
        """A-1형 게이트 검사: 차단·구조변경 감지 후 GateResult 반환."""
