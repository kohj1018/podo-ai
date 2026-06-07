"""T-071 Workday 어댑터 — 외국계·유니콘 다수(NVIDIA·Intel·Salesforce 등).

Workday CxS(Career Experience Services) endpoint → RawJob list.
endpoint: https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{board}/jobs
location facet: locationsText 필드에 korea/seoul 포함 여부로 KR 공고 판별.

T-070 discovery: NVIDIA·Intel·Salesforce·Snowflake·야놀자·무신사 등 다수 확인.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from crawler.adapters.base import BaseCrawlerAdapter, GateResult, RawJob
from crawler.fetch_jobs import REQUEST_TIMEOUT, USER_AGENT, keyword_match
from crawler.gate import detect_block, detect_structure_change

logger = logging.getLogger(__name__)

# CxS API endpoint — tenant·board는 회사별 상이; 기본값은 외부 career site 관례
_WORKDAY_CXS = "https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{board}/jobs"
_REQUIRED_FIELDS = ("id", "title", "externalUrl")
_KR_LOCATION_KEYWORDS = ("korea", "seoul", "한국", "서울")

# fixture/mock 응답은 jobPostings 키를 사용(실제 CxS 응답 구조 반영)
_JOBS_KEY = "jobPostings"


def _is_korea_location(location_str: str) -> bool:
    """location 문자열에 한국 관련 키워드 포함 여부."""
    loc = location_str.lower()
    return any(kw in loc for kw in _KR_LOCATION_KEYWORDS)


class WorkdayAdapter(BaseCrawlerAdapter):
    """Workday CxS API 어댑터(tenant 단위)."""

    def __init__(
        self,
        tenant: str,
        *,
        board: str = "External",
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self.tenant = tenant
        self._client = client
        self._base_url = base_url or _WORKDAY_CXS.format(tenant=tenant, board=board)

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            # CxS API는 Content-Type 헤더를 필요로 함(POST도 동일)
            "Content-Type": "application/json",
        }

    def _resolve_client(self) -> Any:
        return self._client if self._client is not None else httpx.Client()

    def fetch_jobs(self, location: str = "KR") -> list[RawJob]:
        """Workday CxS 공고 목록 → 키워드 필터 + location 필터 통과분 RawJob list.

        응답: {"jobPostings": [{id, title, externalUrl, locationsText, ...}]}
        location="KR": locationsText에 korea/seoul 포함 공고만 반환.
        """
        client = self._resolve_client()
        resp = client.get(
            self._base_url, headers=self._headers(), timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()

        results: list[RawJob] = []
        for job in resp.json().get(_JOBS_KEY, []):
            title = job.get("title", "")
            if not keyword_match(title):
                continue

            loc_str = job.get("locationsText", "")
            if location == "KR" and loc_str and not _is_korea_location(loc_str):
                continue

            job_id = f"{self.tenant}-{job.get('id', '')}"
            results.append(
                {
                    "job_id": job_id,
                    "company": self.tenant,
                    "title": title,
                    "url": job.get("externalUrl", ""),
                    "location": loc_str,
                    "raw_text": job.get("briefDescription", ""),
                }
            )
        return results

    def gate_check(self) -> GateResult:
        """차단(403/429) · 구조변경(필수 필드 실패율 ≥30%) 감지 → GateResult."""
        client = self._resolve_client()
        try:
            resp = client.get(
                self._base_url, headers=self._headers(), timeout=REQUEST_TIMEOUT
            )
        except httpx.HTTPError as exc:  # 시스템 경계 — 네트워크 실패 표면화
            return GateResult(ok=False, reason=f"request error: {exc}")

        status = getattr(resp, "status_code", 200)
        block = detect_block(status)
        if block is not None:
            return GateResult(ok=False, reason=block)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return GateResult(ok=False, reason=f"HTTP {status}: {exc}")

        jobs = resp.json().get(_JOBS_KEY, [])
        struct = detect_structure_change(jobs, _REQUIRED_FIELDS)
        if struct is not None:
            return GateResult(ok=False, reason=struct)
        return GateResult(ok=True, reason="ok")
