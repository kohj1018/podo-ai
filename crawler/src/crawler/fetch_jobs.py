"""T-012 공고 수집 — 토스·당근 fetch + 키워드 필터 + HTML 정규화.

SPEC §9-1 (fetch 소스·헤더·파싱), §9-2 (키워드 필터) 그대로 이식.
HTTP fetch는 주입된 httpx.Client를 받아 테스트에서 fixture로 대체 가능.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# §9-1 상수
# ---------------------------------------------------------------------------

TOSS_BASE = "https://api-public.toss.im/api/v3/ipd-eggnog/career"
DAANGN_LIST_URL = "https://boards-api.greenhouse.io/v1/boards/daangn/jobs?content=true"
REQUEST_TIMEOUT = 15
USER_AGENT = "podo-ai-crawler/0.1 (contact: koh1018.dev@gmail.com)"

# ---------------------------------------------------------------------------
# §9-2 키워드 필터
# ---------------------------------------------------------------------------

TARGET_KEYWORDS: list[str] = [
    "software",
    "engineer",
    "developer",
    "frontend",
    "backend",
    "fullstack",
    "android",
    "ios",
    "server",
    "platform",
    "소프트웨어",
    "엔지니어",
    "개발자",
    "프론트엔드",
    "백엔드",
    "서버",
    "플랫폼",
]


def _norm(s: str) -> str:
    """SPEC §9-2: 대소문자·공백·하이픈·언더스코어·슬래시 제거 후 소문자."""
    return re.sub(r"[\s\-_/]+", "", s.lower())


def keyword_match(title: str) -> bool:
    """SPEC §9-2: 제목에 TARGET_KEYWORDS 중 하나라도 포함되면 True."""
    norm_title = _norm(title)
    return any(_norm(kw) in norm_title for kw in TARGET_KEYWORDS)


# ---------------------------------------------------------------------------
# §9-1 HTML→텍스트 정규화
# ---------------------------------------------------------------------------


def _clean_html(raw: str) -> str:
    """HTML → 텍스트: BeautifulSoup get_text + 빈 줄 접기."""
    unescaped = html.unescape(raw)
    text = BeautifulSoup(unescaped, "html.parser").get_text("\n")
    # 연속 빈 줄 접기
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------------------------------------------------------------------------
# §9-1 파서: 토스 상세
# ---------------------------------------------------------------------------


def parse_toss_detail(
    company: str,
    detail_json: dict[str, Any],
    *,
    job_id: str,
    title: str,
    url: str,
) -> dict[str, str]:
    """토스 상세 API 응답 → raw 공고 dict.

    SPEC §9-1: success.content 또는 payload.content 시도.
    둘 다 없으면 에러 문자열 반환(비치명적 스킵용).
    """
    inner = detail_json.get("success") or detail_json.get("payload") or {}
    raw_html = inner.get("content", "")
    if not raw_html:
        raw_text = "[content_missing]"
    else:
        raw_text = _clean_html(raw_html)
    return {
        "job_id": job_id,
        "company": company,
        "title": title,
        "url": url,
        "raw_text": raw_text,
    }


# ---------------------------------------------------------------------------
# §9-1 파서: 당근 목록 (content 포함, 2차 fetch 불필요)
# ---------------------------------------------------------------------------


def parse_daangn_jobs(list_json: dict[str, Any]) -> list[dict[str, str]]:
    """당근 Greenhouse Board API 응답 → raw 공고 list.

    SPEC §9-1: 목록에 content 포함 — 2차 fetch 불필요.
    """
    results: list[dict[str, str]] = []
    for job in list_json.get("jobs", []):
        gid = job.get("id", "")
        job_id = f"daangn-{gid}"
        title = job.get("title", "")
        url = job.get("absolute_url", "")
        raw_html = job.get("content", "")
        raw_text = _clean_html(raw_html) if raw_html else ""
        results.append(
            {
                "job_id": job_id,
                "company": "daangn",
                "title": title,
                "url": url,
                "raw_text": raw_text,
            }
        )
    return results


# ---------------------------------------------------------------------------
# §9-1 fetch 함수 (실 네트워크 — 테스트는 fake client 주입)
# ---------------------------------------------------------------------------


def fetch_toss_jobs(client: Any) -> list[dict[str, str]]:
    """토스 목록 + 상세 fetch → raw 공고 list.

    client: httpx.Client 호환 (테스트에서 fake로 대체).
    키워드 필터 통과 공고만 상세 fetch 수행.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/html"}
    resp = client.get(f"{TOSS_BASE}/jobs", headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    list_json: dict[str, Any] = resp.json()

    results: list[dict[str, str]] = []
    for item in list_json.get("success", []):
        gid = item.get("id", "")
        title = item.get("title", "")
        url = item.get("absolute_url", "")
        if not keyword_match(title):
            continue
        job_id = f"toss-{gid}"
        try:
            detail_resp = client.get(
                f"{TOSS_BASE}/jobs/{gid}", headers=headers, timeout=REQUEST_TIMEOUT
            )
            detail_resp.raise_for_status()
            raw = parse_toss_detail(
                "toss", detail_resp.json(), job_id=job_id, title=title, url=url
            )
        except httpx.HTTPStatusError as exc:  # QA-M1-005: 단건 실패 skip, 루프 계속
            logger.warning("toss_detail_skip job_id=%s error=%s", job_id, exc)
            continue
        results.append(raw)
    return results


def fetch_daangn_jobs(client: Any) -> list[dict[str, str]]:
    """당근 목록 fetch → raw 공고 list (content 포함, 2차 fetch 불필요).

    키워드 필터 통과 공고만 반환.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/html"}
    resp = client.get(DAANGN_LIST_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    jobs = parse_daangn_jobs(resp.json())
    return [j for j in jobs if keyword_match(j["title"])]
