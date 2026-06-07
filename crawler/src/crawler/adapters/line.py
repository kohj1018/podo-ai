"""T-072 라인플러스(LINE) 자체 채용사이트 어댑터.

careers.linecorp.com 내부 JSON API → RawJob list.
location="KR": country=Korea 또는 location에 Seoul 포함 공고만 반환.
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter, _is_korea_location
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_LINE_API = "https://careers.linecorp.com/api/jobs?ca=Engineering&ci=Seoul"
_REQUIRED_FIELDS = ("id", "title", "url")
_KR_COUNTRY_KEYWORDS = ("korea", "한국")


class LineAdapter(BaseCustomAdapter):
    """라인플러스 채용사이트 어댑터."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "lineplus",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(company=company, client=client, base_url=base_url or _LINE_API)

    def _get_records(self, data: Any) -> list[Any]:
        """gate_check용 레코드 추출: data["data"] list."""
        return data.get("data", []) if isinstance(data, dict) else []

    def _parse_jobs(self, data: Any, location: str) -> list[RawJob]:
        """data list → RawJob list (키워드 필터 + location 필터)."""
        results: list[RawJob] = []
        for job in self._get_records(data):
            if not isinstance(job, dict):
                continue
            title = job.get("title", "")
            if not keyword_match(title):
                continue
            if location == "KR":
                country = job.get("country", "")
                loc_str = job.get("location", "")
                country_lower = country.lower()
                is_kr_country = any(kw in country_lower for kw in _KR_COUNTRY_KEYWORDS)
                is_kr_loc = _is_korea_location(loc_str)
                if not (is_kr_country or is_kr_loc):
                    continue
            job_id = f"{self.company}-{job.get('id', '')}"
            results.append(
                {
                    "job_id": job_id,
                    "company": self.company,
                    "title": title,
                    "url": job.get("url", ""),
                    "location": job.get("location", ""),
                    "raw_text": job.get("jobCategory", ""),
                }
            )
        return results
