"""T-071 Lever Postings API 어댑터.

Lever 공개 Postings API(`api.lever.co/v0/postings/{company}`) → RawJob list.
location 필터: categories.location 필드에 korea/seoul 포함 여부로 KR 공고 판별.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from crawler.adapters.base import BaseCrawlerAdapter, GateResult, RawJob
from crawler.fetch_jobs import REQUEST_TIMEOUT, USER_AGENT, keyword_match
from crawler.gate import detect_block, detect_structure_change

logger = logging.getLogger(__name__)

_LEVER_API = "https://api.lever.co/v0/postings/{company}?mode=json"
_REQUIRED_FIELDS = ("id", "text", "hostedUrl")
_KR_LOCATION_KEYWORDS = ("korea", "seoul", "한국", "서울")


def _is_korea_location(location_str: str) -> bool:
    """location 문자열에 한국 관련 키워드 포함 여부."""
    loc = location_str.lower()
    return any(kw in loc for kw in _KR_LOCATION_KEYWORDS)


class LeverAdapter(BaseCrawlerAdapter):
    """Lever Postings API 어댑터(company slug 단위)."""

    def __init__(
        self,
        company_slug: str,
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self.company_slug = company_slug
        self._client = client
        self._base_url = base_url or _LEVER_API.format(company=company_slug)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT, "Accept": "application/json"}

    def _resolve_client(self) -> Any:
        return self._client if self._client is not None else httpx.Client()

    def fetch_jobs(self, location: str = "KR") -> list[RawJob]:
        """Lever 공고 목록 → 키워드 필터 + location 필터 통과분 RawJob list.

        응답: [{id, text, hostedUrl, descriptionPlain, categories.location}, ...]
        location="KR": categories.location에 korea/seoul 포함 공고만 반환.
        """
        client = self._resolve_client()
        resp = client.get(
            self._base_url, headers=self._headers(), timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()

        results: list[RawJob] = []
        for job in resp.json():
            if not isinstance(job, dict):
                continue
            title = job.get("text", "")
            if not keyword_match(title):
                continue

            loc_str = job.get("categories", {}).get("location", "")
            if location == "KR" and loc_str and not _is_korea_location(loc_str):
                continue

            job_id = f"{self.company_slug}-{job.get('id', '')}"
            results.append(
                {
                    "job_id": job_id,
                    "company": self.company_slug,
                    "title": title,
                    "url": job.get("hostedUrl", ""),
                    "location": loc_str,
                    "raw_text": job.get("descriptionPlain", ""),
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

        jobs = resp.json() if isinstance(resp.json(), list) else []
        struct = detect_structure_change(jobs, _REQUIRED_FIELDS)
        if struct is not None:
            return GateResult(ok=False, reason=struct)
        return GateResult(ok=True, reason="ok")
