"""T-073 Meta Careers 어댑터 (Tier2 외국계 custom).

metacareers.com/jobs?offices=Seoul → RawJob list.
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter, _is_korea_location
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_META_API = "https://www.metacareers.com/jobs?offices=Seoul&q=software+engineer"
_REQUIRED_FIELDS = ("id", "title", "url")


class MetaAdapter(BaseCustomAdapter):
    """Meta Careers 어댑터 — offices=Seoul 필터."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "meta",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(company=company, client=client, base_url=base_url or _META_API)

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
