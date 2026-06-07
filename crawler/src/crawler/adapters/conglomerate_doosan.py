"""T-075 두산 그룹 채용포털 어댑터 (career.doosan.com).

목록 공개(list-public) — view_login=False.
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_DOOSAN_API = "https://career.doosan.com/api/jobs"
_REQUIRED_FIELDS = ("id", "title", "url")


class DoosanAdapter(BaseCustomAdapter):
    """두산 그룹 채용포털 어댑터."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "doosan",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            company=company, client=client, base_url=base_url or _DOOSAN_API
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
            results.append(
                {
                    "job_id": f"{self.company}-{job.get('id', '')}",
                    "company": self.company,
                    "title": title,
                    "url": job.get("url", ""),
                    "location": job.get("location", "대한민국"),
                    "raw_text": job.get("description", ""),
                }
            )
        return results
