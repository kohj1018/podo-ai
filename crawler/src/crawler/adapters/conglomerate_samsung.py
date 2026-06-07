"""T-075 삼성 그룹 통합포털 어댑터 (samsungcareers.com).

계열사(삼성전자·SDS·전기)는 company 파라미터로 구분 — 동일 포털 config 재사용.
목록 공개(view_login=False, spot-verified) — list-public만 수집.
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

# samsungcareers.com 내부 JSON API
_SAMSUNG_API = "https://www.samsungcareers.com/hr/api/jobs"
_REQUIRED_FIELDS = ("id", "title", "url")


class SamsungAdapter(BaseCustomAdapter):
    """삼성 그룹 통합포털 어댑터 — 계열사 config 재사용 지원."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "samsung-electronics",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            company=company, client=client, base_url=base_url or _SAMSUNG_API
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
