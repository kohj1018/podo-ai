"""T-073 Google Careers 어댑터 (Tier2 외국계 custom).

careers.google.com 내부 JSON API → RawJob list (location=Seoul, South Korea 필터).
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import BaseCrawlerAdapter, RawJob
from crawler.adapters.custom_base import BaseCustomAdapter, _is_korea_location
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

# careers.google.com/api/jobs/search — location 파라미터로 Seoul 필터
_GOOGLE_API = "https://careers.google.com/api/jobs/search/?location=Seoul%2C+South+Korea&q=software+engineer"
_REQUIRED_FIELDS = ("id", "title", "url")


def fetch_jobs_with_status(
    adapter: BaseCrawlerAdapter, *, location: str = "KR"
) -> tuple[list[RawJob], str]:
    """어댑터 fetch_jobs 실행 + 결과 건수에 따른 status 반환.

    Returns:
        (jobs, status): jobs=RawJob list, status="active" | "no-korea-jobs"

    한국 공고가 없으면 status=no-korea-jobs로 기록(조용한 누락 방지 — AC-3).
    이 helper는 foreign custom 어댑터 전용 공통 패턴이므로 본 모듈에 둔다.
    """
    jobs = adapter.fetch_jobs(location=location)
    status = "active" if jobs else "no-korea-jobs"
    return jobs, status


class GoogleAdapter(BaseCustomAdapter):
    """Google Careers 어댑터 — location=Seoul/Korea 필터로 KR 공고만 수집."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "google",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            company=company, client=client, base_url=base_url or _GOOGLE_API
        )

    def _get_records(self, data: Any) -> list[Any]:
        return data.get("jobs", []) if isinstance(data, dict) else []

    def _parse_jobs(self, data: Any, location: str) -> list[RawJob]:
        results: list[RawJob] = []
        for job in self._get_records(data):
            if not isinstance(job, dict):
                continue
            title = job.get("title", "")
            if not keyword_match(title):
                continue
            loc = job.get("location", "")
            if location == "KR" and loc and not _is_korea_location(loc):
                continue
            results.append(
                {
                    "job_id": f"{self.company}-{job.get('id', '')}",
                    "company": self.company,
                    "title": title,
                    "url": job.get("url", ""),
                    "location": loc,
                    "raw_text": job.get("description", ""),
                }
            )
        return results
