"""T-075 LG 그룹 통합포털 어댑터 (careers.lg.com).

계열사(LG전자·CNS·U+)는 company 파라미터로 구분 — 동일 포털 config 재사용.
목록 공개(list-public) — view_login=False.
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_LG_API = "https://careers.lg.com/api/jobs"
_REQUIRED_FIELDS = ("id", "title", "url")


class LGAdapter(BaseCustomAdapter):
    """LG 그룹 통합포털 어댑터 — 계열사 config 재사용 지원."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "lg-electronics",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(company=company, client=client, base_url=base_url or _LG_API)

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
