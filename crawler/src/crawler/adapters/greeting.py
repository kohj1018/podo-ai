"""T-071 그리팅(greetinghr) 어댑터 — 한국 스타트업 ATS 1위.

{company}.career.greetinghr.com JSON API → RawJob list.
greetinghr는 한국 스타트업 전용 ATS이므로 location 필터가 별도로 필요 없다
(모든 공고가 국내 채용). location="KR" 인자는 인터페이스 정합용으로 받고 무시한다.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from crawler.adapters.base import BaseCrawlerAdapter, GateResult, RawJob
from crawler.fetch_jobs import REQUEST_TIMEOUT, USER_AGENT, _clean_html, keyword_match
from crawler.gate import detect_block, detect_structure_change

logger = logging.getLogger(__name__)

_GREETING_API = "https://{company}.career.greetinghr.com/api/v2/postings"
_REQUIRED_FIELDS = ("id", "title", "url")


class GreetingAdapter(BaseCrawlerAdapter):
    """그리팅(greetinghr) 어댑터 — 한국 스타트업 1위 ATS."""

    def __init__(
        self,
        company: str,
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self.company = company
        self._client = client
        self._base_url = base_url or _GREETING_API.format(company=company)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT, "Accept": "application/json"}

    def _resolve_client(self) -> Any:
        return self._client if self._client is not None else httpx.Client()

    def fetch_jobs(self, location: str = "KR") -> list[RawJob]:
        """그리팅 공고 목록 → 키워드 필터 통과분 RawJob list.

        greetinghr는 한국 전용 ATS이므로 location 필터 불필요. "KR" 인터페이스 정합용.
        API 응답 구조: {"data": [{id, title, url, description, ...}, ...]}
        """
        client = self._resolve_client()
        resp = client.get(
            self._base_url, headers=self._headers(), timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()

        results: list[RawJob] = []
        for job in resp.json().get("data", []):
            title = job.get("title", "")
            if not keyword_match(title):
                continue
            job_id = f"{self.company}-{job.get('id', '')}"
            url = job.get("url", "")
            raw_html = job.get("description", "")
            results.append(
                {
                    "job_id": job_id,
                    "company": self.company,
                    "title": title,
                    "url": url,
                    "location": job.get("location", "서울"),
                    "raw_text": _clean_html(raw_html) if raw_html else "",
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

        jobs = resp.json().get("data", [])
        struct = detect_structure_change(jobs, _REQUIRED_FIELDS)
        if struct is not None:
            return GateResult(ok=False, reason=struct)
        return GateResult(ok=True, reason="ok")
