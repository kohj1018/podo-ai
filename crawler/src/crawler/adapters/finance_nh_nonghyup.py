"""T-076 NH농협(범농협 통합) 자체 채용사이트 어댑터 (Tier5 금융 custom).

with.nonghyup.com JSON API → RawJob list.
범농협 통합 채용포털 사용.
공개 목록만 수집(list-public 소스).
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_BASE_URL = "https://with.nonghyup.com/api/jobs"
_REQUIRED_FIELDS = ("id", "title", "url")


class NHNonghyupAdapter(BaseCustomAdapter):
    """NH농협 범농협 통합 채용포털 어댑터."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self, *, client: Any | None = None, base_url: str | None = None
    ) -> None:
        super().__init__(
            company="nh-nonghyup",
            client=client,
            base_url=base_url or _BASE_URL,
        )

    def _get_records(self, data: Any) -> list[Any]:
        return data.get("data", []) if isinstance(data, dict) else []

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
                    "job_id": f"nh-nonghyup-{job.get('id', '')}",
                    "company": "nh-nonghyup",
                    "title": title,
                    "url": job.get("url", ""),
                    "location": "대한민국",
                    "raw_text": job.get("description", ""),
                }
            )
        return results
