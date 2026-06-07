"""T-072 네이버 자체 채용포털 어댑터.

recruit.navercorp.com 내부 JSON API → RawJob list.
계열사(SNOW·네이버클라우드 등)는 동일 포털 패턴 → company 파라미터로 config 재사용.
"""

from __future__ import annotations

import logging
from typing import Any

from crawler.adapters.base import RawJob
from crawler.adapters.custom_base import BaseCustomAdapter, _is_korea_location
from crawler.fetch_jobs import keyword_match

logger = logging.getLogger(__name__)

# recruit.navercorp.com 내부 공개 API (로그인 불필요)
_NAVER_API = "https://recruit.navercorp.com/rcrt/list.do?sysempGrpCodeArr=1000&sw="
_REQUIRED_FIELDS = ("id", "title", "url")


class NaverAdapter(BaseCustomAdapter):
    """네이버 자체 채용포털 어댑터 — 계열사 config 재사용 지원."""

    _required_fields = _REQUIRED_FIELDS

    def __init__(
        self,
        company: str = "naver",
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            company=company, client=client, base_url=base_url or _NAVER_API
        )

    def _get_records(self, data: Any) -> list[Any]:
        """gate_check용 레코드 추출: data["result"] list."""
        return data.get("result", []) if isinstance(data, dict) else []

    def _parse_jobs(self, data: Any, location: str) -> list[RawJob]:
        """result list → RawJob list (키워드 필터, 한국 공고만)."""
        results: list[RawJob] = []
        for job in self._get_records(data):
            if not isinstance(job, dict):
                continue
            title = job.get("title", "")
            if not keyword_match(title):
                continue
            work_place = job.get("workPlace", "")
            # 네이버 국내 포털 — workPlace가 비어있지 않으면 한국 공고로 간주
            # location="KR" 필터: 해외 키워드 포함 시 제외
            if location == "KR" and work_place and not _is_korea_location(work_place):
                continue
            job_id = f"{self.company}-{job.get('id', '')}"
            results.append(
                {
                    "job_id": job_id,
                    "company": self.company,
                    "title": title,
                    "url": job.get("url", ""),
                    "location": work_place or "대한민국",
                    "raw_text": job.get("jobGroupName", ""),
                }
            )
        return results
