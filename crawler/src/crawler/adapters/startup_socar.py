"""T-074 쏘카(Socar) careers 어댑터 (Tier3 custom).

socarcorp.kr/recruit JSON API → RawJob list.
국내 전용 소스이므로 location 필터 불필요(all-kr).
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_SOCAR_API = "https://socarcorp.kr/api/recruit/jobs"
_REQUIRED_FIELDS = ("id", "title", "url")


class SocarAdapter(BaseCustomAdapter):
    """쏘카 careers 어댑터."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "socar",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            company=company, client=client, base_url=base_url or _SOCAR_API
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
                    "location": job.get("location", "서울"),
                    "raw_text": job.get("description", ""),
                }
            )
        return results
