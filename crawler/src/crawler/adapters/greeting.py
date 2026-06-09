"""T-071 그리팅(greetinghr) 어댑터 — 한국 스타트업 ATS 1위.

{company}.career.greetinghr.com careers 페이지는 Next.js + React Query SSR이라
공고 전체가 페이지 HTML에 dehydrated JSON("openings" 쿼리)으로 박혀 있다. 별도 공개
JSON API(구 /api/v2/postings)는 404 — 페이지 GET 후 임베디드 openings 배열을 파싱한다
(브라우저 불요, 라이브 확인 2026-06).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from crawler.adapters.base import BaseCrawlerAdapter, GateResult, RawJob
from crawler.fetch_jobs import REQUEST_TIMEOUT, keyword_match
from crawler.gate import detect_block

logger = logging.getLogger(__name__)

_CAREERS_URL = "https://{company}.career.greetinghr.com/"
# 공개 채용페이지지만 일반 UA에도 서빙되도록 브라우저 UA 사용.
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
# React Query dehydrate 앵커 — openings 쿼리의 state.data 배열을 찾는 기준.
_OPENINGS_MARKER = '"queryKey":["openings"]'
_STATE_DATA = '"state":{"data":'


def _extract_openings(html: str) -> list[dict[str, Any]]:
    """React Query SSR 하이드레이션에서 openings 쿼리의 data 배열 추출.

    dehydrated 구조: {"state":{"data":[...openings...],...},"queryKey":["openings"],...}
    queryKey 직전의 `"state":{"data":[`를 앵커로 잡고 JSONDecoder.raw_decode로 배열만
    안전 파싱한다(문자열 내 대괄호·이스케이프를 디코더가 정확히 처리).
    """
    qk = html.find(_OPENINGS_MARKER)
    if qk == -1:
        return []
    state = html.rfind(_STATE_DATA, 0, qk)
    if state == -1:
        return []
    arr_start = html.find("[", state)
    if arr_start == -1:
        return []
    try:
        data, _ = json.JSONDecoder().raw_decode(html, arr_start)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


class GreetingAdapter(BaseCrawlerAdapter):
    """그리팅(greetinghr) 어댑터 — 페이지 임베디드 openings 파싱(브라우저 불요)."""

    def __init__(
        self,
        company: str,
        *,
        client: Any | None = None,
        base_url: str | None = None,
    ) -> None:
        self.company = company
        self._client = client
        self._base_url = base_url or _CAREERS_URL.format(company=company)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": _BROWSER_UA, "Accept": "text/html"}

    def _resolve_client(self) -> Any:
        if self._client is not None:
            return self._client
        # 로케일 리다이렉트 가능성 대비 follow_redirects.
        return httpx.Client(follow_redirects=True)

    def _opening_to_rawjob(self, opening: dict[str, Any]) -> RawJob | None:
        """openings 항목 1건 → RawJob. 비기술직(키워드 미스)·무효는 None."""
        title = opening.get("title", "")
        if not title or not keyword_match(title):
            return None
        opening_id = opening.get("openingId", "")
        positions = (opening.get("openingJobPosition") or {}).get(
            "openingJobPositions"
        ) or []
        field = occupation = location = career = employment = ""
        if positions:
            pos = positions[0]
            field = (pos.get("workspaceField") or {}).get("field", "") or ""
            occupation = (pos.get("workspaceOccupation") or {}).get(
                "occupation", ""
            ) or ""
            place = pos.get("workspacePlace") or {}
            location = place.get("place") or place.get("location") or ""
            career = (pos.get("jobPositionCareer") or {}).get("careerType", "") or ""
            employment = (pos.get("jobPositionEmployment") or {}).get(
                "employmentType", ""
            ) or ""
        # greetinghr 목록 데이터엔 JD 본문이 없음 — 구조화 필드로 raw_text 구성(상세
        # 본문은 후속: openingId 상세페이지 추가 fetch 필요).
        raw_text = " / ".join(
            x for x in (field, occupation, location, career, employment) if x
        )
        return {
            "job_id": f"{self.company}-{opening_id}",
            "company": self.company,
            "title": title,
            "url": f"https://{self.company}.career.greetinghr.com/ko/o/{opening_id}",
            "location": location or "대한민국",
            "raw_text": raw_text,
        }

    def fetch_jobs(self, location: str = "KR") -> list[RawJob]:
        """careers 페이지 GET → 임베디드 openings 파싱 → 기술직 RawJob list.

        greetinghr는 한국 전용 ATS라 location 필터 불필요("KR" 인터페이스 정합용).
        """
        client = self._resolve_client()
        resp = client.get(
            self._base_url, headers=self._headers(), timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        results: list[RawJob] = []
        for opening in _extract_openings(resp.text):
            job = self._opening_to_rawjob(opening)
            if job is not None:
                results.append(job)
        return results

    def gate_check(self) -> GateResult:
        """차단(403/429) · 임베디드 openings 마커 존재 여부 → GateResult."""
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

        # 마커 부재 = SSR 데이터 위치 변경(구조 변경) 신호 → 게이트 실패로 표면화.
        if _OPENINGS_MARKER not in resp.text:
            return GateResult(ok=False, reason="openings 마커 없음(페이지 구조 변경)")
        return GateResult(ok=True, reason="ok")
