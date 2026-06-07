"""T-072 카카오 자체 채용사이트 어댑터.

careers.kakao.com 내부 JSON API → RawJob list.
계열사(카카오게임즈·카카오엔터프라이즈)는 base_url + company 파라미터로 config 재사용.
카카오페이·카카오엔터테인먼트·카카오모빌리티·카카오스타일은 그리팅 ATS(T-071).
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

_KAKAO_API = "https://careers.kakao.com/api/public/jobs?part=TECHNOLOGY&keyword="
_REQUIRED_FIELDS = ("id", "title", "url")


class KakaoAdapter(BaseCustomAdapter):
    """카카오 자체 채용사이트 어댑터 — 계열사 base_url 재사용 지원."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "kakao",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            company=company, client=client, base_url=base_url or _KAKAO_API
        )

    def _get_records(self, data: Any) -> list[Any]:
        """gate_check용 레코드 추출: data["jobList"] list."""
        return data.get("jobList", []) if isinstance(data, dict) else []

    def _parse_jobs(self, data: Any, location: str) -> list[RawJob]:
        """jobList → RawJob list (키워드 필터)."""
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
                    "location": job.get("location", "판교"),
                    "raw_text": job.get("description", ""),
                }
            )
        return results
