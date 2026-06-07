"""T-073 Apple Jobs 어댑터 (Tier2 외국계 custom).

jobs.apple.com/en-kr/search API → RawJob list (location=korea-KOR 필터).
응답 구조: {"searchResults": [...]}
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter, _is_korea_location
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_APPLE_API = "https://jobs.apple.com/api/role/search?location=korea-KOR&team=software-and-services"
_REQUIRED_FIELDS = ("positionId", "postingTitle", "retailPostingUrl")


class AppleAdapter(BaseCustomAdapter):
    """Apple Jobs 어댑터 — location=korea-KOR 필터."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "apple",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            company=company, client=client, base_url=base_url or _APPLE_API
        )

    def _get_records(self, data: Any) -> list[Any]:
        return data.get("searchResults", []) if isinstance(data, dict) else []

    def _parse_jobs(self, data: Any, location: str) -> list[RawJob]:
        results: list[RawJob] = []
        for job in self._get_records(data):
            if not isinstance(job, dict):
                continue
            title = job.get("postingTitle", "")
            if not keyword_match(title):
                continue
            loc = job.get("homeOffice", "")
            if location == "KR" and loc and not _is_korea_location(loc):
                continue
            url = job.get("retailPostingUrl", "")
            if url and not url.startswith("http"):
                url = f"https://jobs.apple.com{url}"
            results.append(
                {
                    "job_id": f"{self.company}-{job.get('positionId', '')}",
                    "company": self.company,
                    "title": title,
                    "url": url,
                    "location": loc,
                    "raw_text": job.get("jobSummary", ""),
                }
            )
        return results
