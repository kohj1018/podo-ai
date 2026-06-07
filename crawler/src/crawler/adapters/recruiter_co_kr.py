"""T-075 recruiter.co.kr 위탁 SaaS 어댑터 (공유 — T-076 금융권 재사용).

slug(회사별 subdomain) 파라미터로 여러 회사 재사용.
공개 목록만 수집(view_login=False 소스 전용).
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

# recruiter.co.kr 레코드 키는 rNo(공고번호)·title·url — gate_check 실패율 산정에 사용
_REQUIRED_FIELDS = ("rNo", "title", "url")


def _build_api_url(slug: str) -> str:
    """recruiter.co.kr slug → 목록 API URL."""
    return f"https://{slug}.recruiter.co.kr/api/list"


class RecruiterCoKrAdapter(BaseCustomAdapter):
    """recruiter.co.kr 위탁 SaaS 어댑터 — slug로 회사 구분, Tier4/5 공유."""

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
        return data.get("list", []) if isinstance(data, dict) else []

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
                    "job_id": f"{self.company}-{job.get('rNo', '')}",
                    "company": self.company,
                    "title": title,
                    "url": job.get("url", ""),
                    "location": "대한민국",
                    "raw_text": job.get("description", ""),
                }
            )
        return results
