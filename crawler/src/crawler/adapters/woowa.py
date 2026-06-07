"""T-072 우아한형제들(배민) 자체 채용사이트 어댑터.

career.woowahan.com 내부 JSON API → RawJob list.
국내 전용 채용 포털이므로 location 필터 별도 불필요.
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_WOOWA_API = "https://career.woowahan.com/api/v1/jobs?sort=recent"
_REQUIRED_FIELDS = ("id", "title", "url")


class WoowaAdapter(BaseCustomAdapter):
    """우아한형제들 채용사이트 어댑터."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "woowa",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            company=company, client=client, base_url=base_url or _WOOWA_API
        )

    def _get_records(self, data: Any) -> list[Any]:
        """gate_check용 레코드 추출: data["data"]["list"] list."""
        if isinstance(data, dict):
            records = data.get("data", {}).get("list", [])
            return records if isinstance(records, list) else []
        return []

    def _parse_jobs(self, data: Any, location: str) -> list[RawJob]:
        """data.data.list → RawJob list (키워드 필터)."""
        results: list[RawJob] = []
        for job in self._get_records(data):
            if not isinstance(job, dict):
                continue
            title = job.get("title", "")
            if not keyword_match(title):
                continue
            job_id = f"{self.company}-{job.get('id', '')}"
            results.append(
                {
                    "job_id": job_id,
                    "company": self.company,
                    "title": title,
                    "url": job.get("url", ""),
                    "location": job.get("location", "서울"),
                    "raw_text": job.get("part", ""),
                }
            )
        return results
