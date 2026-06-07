"""T-062 토스 커스텀 어댑터 — 토스 공개 career API(목록 + 상세 2단계 fetch).

Greenhouse 계열이 아닌 custom JSON API(`api-public.toss.im`)라 별도 어댑터로 둔다.
SPEC §9-1 fetch 로직을 그대로 보유(키워드 필터 통과분만 상세 fetch). 단건 상세 실패는
스킵하고 루프를 계속한다(QA-M1-005).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from crawler.adapters.base import BaseCrawlerAdapter, GateResult, RawJob
from crawler.fetch_jobs import (
    REQUEST_TIMEOUT,
    TOSS_BASE,
    USER_AGENT,
    keyword_match,
    parse_toss_detail,
)
from crawler.gate import detect_block, detect_structure_change

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ("id", "title", "absolute_url")


class TossAdapter(BaseCrawlerAdapter):
    """토스 공개 career API custom 어댑터."""

    def __init__(self, *, client: Any | None = None) -> None:
        self._client = client

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT, "Accept": "application/json, text/html"}

    def _resolve_client(self) -> Any:
        return self._client if self._client is not None else httpx.Client()

    def fetch_jobs(self, location: str = "KR") -> list[RawJob]:
        """토스 목록 + 상세 fetch → 키워드 필터 통과분만 RawJob list로 반환."""
        client = self._resolve_client()
        headers = self._headers()
        resp = client.get(f"{TOSS_BASE}/jobs", headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        results: list[RawJob] = []
        for item in resp.json().get("success", []):
            title = item.get("title", "")
            if not keyword_match(title):
                continue
            gid = item.get("id", "")
            job_id = f"toss-{gid}"
            url = item.get("absolute_url", "")
            try:
                detail_resp = client.get(
                    f"{TOSS_BASE}/jobs/{gid}", headers=headers, timeout=REQUEST_TIMEOUT
                )
                detail_resp.raise_for_status()
                raw = parse_toss_detail(
                    "toss", detail_resp.json(), job_id=job_id, title=title, url=url
                )
            except httpx.HTTPStatusError as exc:  # 단건 실패 skip, 루프 계속(QA-M1-005)
                logger.warning("toss_detail_skip job_id=%s error=%s", job_id, exc)
                continue
            results.append(raw)
        return results

    def gate_check(self) -> GateResult:
        """차단(403/429) · 구조변경(목록 필수 필드 실패율 ≥30%) 감지 → GateResult."""
        client = self._resolve_client()
        try:
            resp = client.get(
                f"{TOSS_BASE}/jobs", headers=self._headers(), timeout=REQUEST_TIMEOUT
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

        items = resp.json().get("success", [])
        struct = detect_structure_change(items, _REQUIRED_FIELDS)
        if struct is not None:
            return GateResult(ok=False, reason=struct)
        return GateResult(ok=True, reason="ok")
