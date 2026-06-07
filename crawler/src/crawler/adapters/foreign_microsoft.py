"""T-073 Microsoft Careers 어댑터 (Tier2 외국계 custom).

careers.microsoft.com v2 API → RawJob list (country=Korea 필터).
응답 구조: {"operationResult": {"result": {"jobs": [...]}}}
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter, _is_korea_location
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_MS_API = "https://careers.microsoft.com/api/v2/jobs?country=Korea&q=software+engineer"
_REQUIRED_FIELDS = ("jobId", "title", "jobDetailsUrl")


class MicrosoftAdapter(BaseCustomAdapter):
    """Microsoft Careers 어댑터 — country=Korea 필터."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "microsoft",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(company=company, client=client, base_url=base_url or _MS_API)

    def _get_records(self, data: Any) -> list[Any]:
        if not isinstance(data, dict):
            return []
        records = data.get("operationResult", {}).get("result", {}).get("jobs", [])
        return records if isinstance(records, list) else []

    def _parse_jobs(self, data: Any, location: str) -> list[RawJob]:
        results: list[RawJob] = []
        for job in self._get_records(data):
            if not isinstance(job, dict):
                continue
            title = job.get("title", "")
            if not keyword_match(title):
                continue
            loc = job.get("primaryWorkLocation", "")
            if location == "KR" and loc and not _is_korea_location(loc):
                continue
            job_path = job.get("jobDetailsUrl", "")
            url = (
                f"https://careers.microsoft.com{job_path}"
                if job_path.startswith("/")
                else job_path
            )
            results.append(
                {
                    "job_id": f"{self.company}-{job.get('jobId', '')}",
                    "company": self.company,
                    "title": title,
                    "url": url,
                    "location": loc,
                    "raw_text": job.get("descriptionTeaser", ""),
                }
            )
        return results
