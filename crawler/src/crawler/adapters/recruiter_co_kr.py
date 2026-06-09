"""T-075 recruiter.co.kr (MIDAS IT — JOBFLEX/JOBDA) 위탁 SaaS 어댑터.

careers 사이트({slug}.recruiter.co.kr)는 Next.js SPA — 공고는 별도 API 호스트에서 POST로
가져온다(라이브 역추적 2026-06):
  POST {JOBFLEX|JOBDA}/position/v1/{product}
  headers: prefix={slug}.recruiter.co.kr (인터셉터가 window.location.hostname을 넣음)
  body: {"pageableRq":{"page":<1-indexed>,"size":N}, "filter":{}}
  → {"pagination":{page,size,totalCount,totalPages}, "list":[{positionSn,title,...}]}
회사마다 product(jobflex/jobda)가 달라 jobflex 먼저 시도 후 jobda fallback. 한국 전용.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from crawler.adapters.base import BaseCrawlerAdapter, GateResult, RawJob
from crawler.fetch_jobs import REQUEST_TIMEOUT, keyword_match
from crawler.gate import detect_block

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
# product별 prod API 호스트(MIDAS IT). 회사마다 둘 중 하나 사용 → 순서대로 시도.
_PRODUCTS = (
    "https://api-recruiter.recruiter.co.kr/position/v1/jobflex",
    "https://api.recruiter.im/position/v1/jobda",
)
_PAGE_SIZE = 100


class RecruiterCoKrAdapter(BaseCrawlerAdapter):
    """recruiter.co.kr(JOBFLEX/JOBDA) — slug로 회사, prefix 헤더로 테넌트 지정."""

    def __init__(
        self,
        company: str,
        slug: str,
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self.company = company
        self._slug = slug
        self._hostname = f"{slug}.recruiter.co.kr"
        self._client = client
        # base_url 주입 시 product 자동탐색 생략(테스트·고정용).
        self._base_url = base_url
        self._resolved_url: str | None = base_url

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": _BROWSER_UA,
            "Content-Type": "application/json",
            "prefix": self._hostname,  # 인터셉터가 hostname을 prefix 헤더로 넣음
        }

    def _resolve_client(self) -> Any:
        return self._client if self._client is not None else httpx.Client()

    def _post_list(self, client: Any, url: str, page: int) -> Any:
        body = {"pageableRq": {"page": page, "size": _PAGE_SIZE}, "filter": {}}
        return client.post(
            url, headers=self._headers(), json=body, timeout=REQUEST_TIMEOUT
        )

    def _resolve_endpoint(self, client: Any) -> str | None:
        """회사의 product API URL 탐색(jobflex→jobda). 결과 캐시."""
        if self._resolved_url is not None:
            return self._resolved_url
        for url in _PRODUCTS:
            try:
                resp = self._post_list(client, url, 1)
            except httpx.HTTPError:
                continue
            if resp.status_code == 200:
                self._resolved_url = url
                return url
        return None

    def _position_to_rawjob(self, pos: dict[str, Any]) -> RawJob | None:
        """position 1건 → RawJob. 비기술직(키워드 미스)·무효는 None."""
        title = pos.get("title", "")
        if not title or not keyword_match(title):
            return None
        sn = pos.get("positionSn", "")
        tag_list = pos.get("tagList") or []
        tags = " ".join(t.get("tagName", "") for t in tag_list if isinstance(t, dict))
        # 목록 API엔 본문·위치 없음 — 메타로 raw_text 구성(상세는 후속).
        parts = (
            title,
            pos.get("careerType", ""),
            pos.get("classificationCode", ""),
            tags,
        )
        raw_text = " / ".join(x for x in parts if x)
        return {
            "job_id": f"{self.company}-{sn}",
            "company": self.company,
            "title": title,
            "url": f"https://{self._hostname}/career/jobs/{sn}",
            "location": "대한민국",
            "raw_text": raw_text,
        }

    def fetch_jobs(self, location: str = "KR") -> list[RawJob]:
        """공고 목록 전 페이지 순회 → 기술직 RawJob list(recruiter.co.kr=한국 전용)."""
        client = self._resolve_client()
        url = self._resolve_endpoint(client)
        if url is None:
            return []
        results: list[RawJob] = []
        page = 1
        while True:
            resp = self._post_list(client, url, page)
            resp.raise_for_status()
            data = resp.json()
            for pos in data.get("list", []):
                if isinstance(pos, dict):
                    job = self._position_to_rawjob(pos)
                    if job is not None:
                        results.append(job)
            pagination = data.get("pagination") or {}
            if page >= int(pagination.get("totalPages", 1)):
                break
            page += 1
        return results

    def gate_check(self) -> GateResult:
        """product 탐색 + 200 응답 여부로 게이트 판정(차단 403/429 표면화)."""
        client = self._resolve_client()
        urls = [self._base_url] if self._base_url is not None else list(_PRODUCTS)
        last_status = 0
        for url in urls:
            try:
                resp = self._post_list(client, url, 1)
            except httpx.HTTPError as exc:  # 시스템 경계 — 네트워크 실패 표면화
                return GateResult(ok=False, reason=f"request error: {exc}")
            last_status = getattr(resp, "status_code", 0)
            block = detect_block(last_status)
            if block is not None:
                return GateResult(ok=False, reason=block)
            if last_status == 200:
                self._resolved_url = url
                return GateResult(ok=True, reason="ok")
        return GateResult(ok=False, reason=f"HTTP {last_status}: product 미매칭")
