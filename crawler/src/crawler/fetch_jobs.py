"""T-012 공고 수집 — 토스·당근 fetch + 키워드 필터 + HTML 정규화.

SPEC §9-1 (fetch 소스·헤더·파싱), §9-2 (키워드 필터) 그대로 이식.
HTTP fetch는 주입된 httpx.Client를 받아 테스트에서 fixture로 대체 가능.
"""

from __future__ import annotations

import html
import re
from typing import Any

from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# §9-1 상수 (어댑터 공유 — adapters/toss.py·greenhouse.py가 import)
# ---------------------------------------------------------------------------

TOSS_BASE = "https://api-public.toss.im/api/v3/ipd-eggnog/career"
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
    """토스 목록 + 상세 fetch → raw 공고 list (TossAdapter 위임, 외부 행동 불변).

    어댑터 구조(T-062)로 이전했고 이 함수는 _CHANNELS 호환을 위한 thin wrapper다.
    어댑터 import는 순환 회피를 위해 호출 시점에 지연 로드한다.
    """
    from crawler.adapters.toss import TossAdapter

    return TossAdapter(client=client).fetch_jobs()


def fetch_daangn_jobs(client: Any) -> list[dict[str, str]]:
    """당근 목록 fetch → raw 공고 list (GreenhouseAdapter 위임, 외부 행동 불변).

    당근은 Greenhouse board API라 GreenhouseAdapter(slug="daangn")로 흡수했고 이 함수는
    _CHANNELS 호환용 thin wrapper다. 어댑터 import는 순환 회피를 위해 지연 로드한다.
    """
    from crawler.adapters.greenhouse import GreenhouseAdapter

    return GreenhouseAdapter(company_slug="daangn", client=client).fetch_jobs()
