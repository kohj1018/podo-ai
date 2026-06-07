"""T-073 Uber Careers 어댑터 (Tier2 외국계 custom).

uber.com/api/loadSearchJobsResult?location=KOR-Seoul → RawJob list.
응답 구조: {"data": {"results": [...]}}
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter, _is_korea_location
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_UBER_API = "https://www.uber.com/api/loadSearchJobsResult?location=KOR-Seoul"
_REQUIRED_FIELDS = ("id", "title", "url")


class UberAdapter(BaseCustomAdapter):
    """Uber Careers 어댑터 — location=KOR-Seoul 필터."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "uber",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(company=company, client=client, base_url=base_url or _UBER_API)

    def _get_records(self, data: Any) -> list[Any]:
        if not isinstance(data, dict):
            return []
        records = data.get("data", {}).get("results", [])
        return records if isinstance(records, list) else []

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
