"""T-076 applyin 위탁 SaaS 어댑터 — Tier5 금융권 공유.

slug(회사별 subdomain) 파라미터로 회사 구분.
대상: 코스콤(koscom).
공개 목록만 수집(view_login=False 소스 전용).
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

# applyin 레코드 키 — gate_check 실패율 산정용
_REQUIRED_FIELDS = ("recNo", "recTitle", "applyUrl")


def _build_api_url(slug: str) -> str:
    """applyin slug → 목록 API URL."""
    return f"https://{slug}.applyin.co.kr/api/list"


class ApplyinAdapter(BaseCustomAdapter):
    """applyin 위탁 SaaS 어댑터 — slug로 회사 구분, Tier5 공유."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str,
        slug: str,
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            company=company,
            client=client,
            base_url=base_url or _build_api_url(slug),
        )
        self._slug = slug

    def _get_records(self, data: Any) -> list[Any]:
        return data.get("recruitList", []) if isinstance(data, dict) else []

    def _parse_jobs(self, data: Any, location: str) -> list[RawJob]:
        results: list[RawJob] = []
        for job in self._get_records(data):
            if not isinstance(job, dict):
                continue
            title = job.get("recTitle", "")
            if not keyword_match(title):
                continue
            results.append(
                {
                    "job_id": f"{self.company}-{job.get('recNo', '')}",
                    "company": self.company,
                    "title": title,
                    "url": job.get("applyUrl", ""),
                    "location": "대한민국",
                    "raw_text": job.get("recContent", ""),
                }
            )
        return results
