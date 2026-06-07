"""T-072 Tier1 custom 어댑터 공통 골격.

BaseCustomAdapter(BaseCrawlerAdapter): 자체 채용사이트용 공통 추상 어댑터.
- 내부 JSON API 발견 우선, 실패 시 HTML 파싱(BeautifulSoup4).
- 페이지네이션 추상 (fetch_page / has_next_page).
- parse 실패율 게이트(A-1): 필수 필드 실패율 ≥30% → GateResult(ok=False).
- location 필터: 서브클래스에서 _is_korea_location() 사용 또는 override.

httpx + BeautifulSoup4 사용 (현재 deps). Playwright 미사용.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any

import httpx

from crawler.adapters.base import BaseCrawlerAdapter, GateResult, RawJob
from crawler.fetch_jobs import REQUEST_TIMEOUT, USER_AGENT
from crawler.gate import detect_block, detect_structure_change

logger = logging.getLogger(__name__)

_KR_LOCATION_KEYWORDS = ("korea", "seoul", "한국", "서울", "판교", "성남", "부산")


def _is_korea_location(location_str: str) -> bool:
    """location 문자열에 한국 관련 키워드 포함 여부."""
    loc = location_str.lower()
    return any(kw in loc for kw in _KR_LOCATION_KEYWORDS)


class BaseCustomAdapter(BaseCrawlerAdapter):
    """Tier1 자체 채용사이트용 공통 골격.

    서브클래스가 구현해야 할 것:
    - _required_fields: tuple[str, ...] — gate_check용 필수 필드
    - _parse_jobs(data): 응답(JSON dict 또는 HTML str) → RawJob list
    - _get_records(data): gate_check용 레코드 list 추출

    선택 override:
    - _api_url: 내부 JSON API URL
    - fetch_page(page): 단일 페이지 응답 반환 (페이지네이션)
    - has_next_page(data, page): 다음 페이지 존재 여부
    """

    _required_fields: tuple[str, ...] = ("id", "title", "url")

    def __init__(
        self,
        company: str,
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self.company = company
        self._client = client
        self._base_url = base_url

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT, "Accept": "application/json"}

    def _resolve_client(self) -> Any:
        return self._client if self._client is not None else httpx.Client()

    def fetch_page(self, page: int = 1) -> Any:
        """단일 페이지 응답(JSON dict) 반환. 서브클래스가 URL·파라미터 조정."""
        assert self._base_url is not None, "base_url must be set"
        client = self._resolve_client()
        resp = client.get(
            self._base_url, headers=self._headers(), timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()

    def has_next_page(self, data: Any, page: int) -> bool:
        """다음 페이지 존재 여부. 기본은 단일 페이지(False)."""
        return False

    @abstractmethod
    def _parse_jobs(self, data: Any, location: str) -> list[RawJob]:
        """응답 데이터 → RawJob list. 서브클래스가 구현."""

    @abstractmethod
    def _get_records(self, data: Any) -> list[Any]:
        """gate_check용 레코드 list 추출. 서브클래스가 구현."""

    def fetch_jobs(self, location: str = "KR") -> list[RawJob]:
        """모든 페이지 순회하며 RawJob 수집. 키워드 필터 + location 필터 적용."""
        results: list[RawJob] = []
        page = 1
        while True:
            data = self.fetch_page(page)
            results.extend(self._parse_jobs(data, location))
            if not self.has_next_page(data, page):
                break
            page += 1
        return results

    def gate_check(self) -> GateResult:
        """차단(403/429) · 구조변경(필수 필드 실패율 ≥30%) 감지 → GateResult."""
        client = self._resolve_client()
        assert self._base_url is not None, "base_url must be set"
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

        data = resp.json()
        records = self._get_records(data)
        struct = detect_structure_change(records, self._required_fields)
        if struct is not None:
            return GateResult(ok=False, reason=struct)
        return GateResult(ok=True, reason="ok")
