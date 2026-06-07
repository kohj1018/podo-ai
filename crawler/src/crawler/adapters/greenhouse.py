"""T-062 Greenhouse Job Board API 어댑터.

Greenhouse 공개 Job Board API(`/v1/boards/{slug}/jobs?content=true`)는 board의 전체
공고를 단일 응답으로 반환한다(커서 페이지네이션 없음) — 단일 GET로 수집한다. 기존
`fetch_daangn_jobs`(동일 API)를 slug 일반화한 형태(daangn=slug 1 사례).
인증 불필요(public). location 필터는 외국계 ATS 적용분(T-071)에서 method별로 붙는다.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from crawler.adapters.base import BaseCrawlerAdapter, GateResult, RawJob
from crawler.fetch_jobs import (
    REQUEST_TIMEOUT,
    USER_AGENT,
    _clean_html,
    keyword_match,
)
from crawler.gate import detect_block, detect_structure_change

logger = logging.getLogger(__name__)

_BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
_REQUIRED_FIELDS = ("id", "title", "absolute_url")


class GreenhouseAdapter(BaseCrawlerAdapter):
    """Greenhouse Job Board API 어댑터(slug 단위)."""

    def __init__(
        self,
        company_slug: str,
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self.company_slug = company_slug
        self._client = client
        self._base_url = base_url or _BOARD_URL.format(slug=company_slug)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT, "Accept": "application/json"}

    def _resolve_client(self) -> Any:
        return self._client if self._client is not None else httpx.Client()

    def fetch_jobs(self, location: str = "KR") -> list[RawJob]:
        """board 전체 공고를 단일 GET 수집, 키워드 필터 통과분만 RawJob list 반환."""
        client = self._resolve_client()
        resp = client.get(
            self._base_url, headers=self._headers(), timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        results: list[RawJob] = []
        for job in resp.json().get("jobs", []):
            title = job.get("title", "")
            if not keyword_match(title):
                continue
            raw_html = job.get("content", "")
            results.append(
                {
                    "job_id": f"{self.company_slug}-{job.get('id', '')}",
                    "company": self.company_slug,
                    "title": title,
                    "url": job.get("absolute_url", ""),
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

        jobs = resp.json().get("jobs", [])
        struct = detect_structure_change(jobs, _REQUIRED_FIELDS)
        if struct is not None:
            return GateResult(ok=False, reason=struct)
        return GateResult(ok=True, reason="ok")
