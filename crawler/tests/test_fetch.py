"""T-012 Red phase tests — AC-1, AC-2, AC-3."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# AC-1: 토스·당근 API 응답 fixture 파싱 → raw 공고 정규화
# ---------------------------------------------------------------------------

TOSS_LIST_FIXTURE = {
    "success": [
        {
            "id": 12345,
            "title": "Frontend Engineer",
            "absolute_url": "https://toss.im/jobs/12345",
        },
        {
            "id": 99999,
            "title": "콘텐츠 마케터",
            "absolute_url": "https://toss.im/jobs/99999",
        },
    ]
}

TOSS_DETAIL_FIXTURE = {
    "success": {
        "content": "<p>We are looking for a <b>Frontend Engineer</b></p><ul><li>React</li></ul>",
        "title": "Frontend Engineer",
        "absolute_url": "https://toss.im/jobs/12345",
    }
}

DAANGN_LIST_FIXTURE = {
    "jobs": [
        {
            "id": 67890,
            "title": "Backend Engineer",
            "absolute_url": "https://daangn.com/jobs/67890",
            "content": "<p>당근페이 <b>Backend</b> 엔지니어를 찾습니다.</p>",
        }
    ]
}


def test_AC_1_parse_toss_daangn_fixtures():
    """AC-1: 토스·당근 fixture 파싱 → (job_id, company, title, url, raw_text) + HTML→텍스트 변환."""
    from crawler.fetch_jobs import parse_daangn_jobs, parse_toss_detail

    # 토스 상세 파싱
    toss_raw = parse_toss_detail(
        "toss",
        TOSS_DETAIL_FIXTURE,
        job_id="toss-12345",
        title="Frontend Engineer",
        url="https://toss.im/jobs/12345",
    )
    assert toss_raw["job_id"] == "toss-12345"
    assert toss_raw["company"] == "toss"
    assert toss_raw["title"] == "Frontend Engineer"
    assert toss_raw["url"] == "https://toss.im/jobs/12345"
    # HTML이 텍스트로 변환됐는지 확인 (태그 없음)
    assert "<p>" not in toss_raw["raw_text"]
    assert "<b>" not in toss_raw["raw_text"]
    assert "Frontend Engineer" in toss_raw["raw_text"]

    # 당근 목록+content 파싱 (2차 fetch 불필요)
    daangn_jobs = parse_daangn_jobs(DAANGN_LIST_FIXTURE)
    assert len(daangn_jobs) == 1
    job = daangn_jobs[0]
    assert job["job_id"] == "daangn-67890"
    assert job["company"] == "daangn"
    assert job["title"] == "Backend Engineer"
    assert job["url"] == "https://daangn.com/jobs/67890"
    assert "<p>" not in job["raw_text"]
    assert "Backend" in job["raw_text"]


# ---------------------------------------------------------------------------
# AC-2: 키워드 필터 — 대소문자/공백/하이픈 무시
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title, expected",
    [
        ("콘텐츠 마케터", False),
        ("Frontend Engineer", True),
        ("front-end engineer", True),
        ("BACKEND DEVELOPER", True),
        ("풀스택 개발자", True),
        ("iOS 엔지니어", True),
        ("소프트웨어 엔지니어", True),
        ("디자이너", False),
        ("운영 매니저", False),
        ("Platform Engineer", True),
        ("서버 개발자", True),
        ("데이터 분석가", False),  # '데이터'는 TARGET_KEYWORDS에 없음
    ],
)
def test_AC_2_keyword_filter(title: str, expected: bool):
    """AC-2: keyword_match — 엔지니어링 토큰 포함 여부 (대소문자/공백/하이픈 무시)."""
    from crawler.fetch_jobs import keyword_match

    assert keyword_match(title) is expected


# ---------------------------------------------------------------------------
# AC-3: upsert + diff + CoverageState
# ---------------------------------------------------------------------------


def test_AC_3_upsert_diff_and_coverage():
    """AC-3: 전일 집합 vs 금일 결과 → 신규/마감 diff + 수집 실패 CoverageState 노출."""
    from crawler.store import CoverageState, compute_diff

    yesterday = [
        {
            "job_id": "toss-1",
            "company": "toss",
            "title": "A",
            "url": "u1",
            "raw_text": "",
        },
        {
            "job_id": "toss-2",
            "company": "toss",
            "title": "B",
            "url": "u2",
            "raw_text": "",
        },
    ]
    today = [
        {
            "job_id": "toss-1",
            "company": "toss",
            "title": "A",
            "url": "u1",
            "raw_text": "",
        },
        {
            "job_id": "toss-3",
            "company": "toss",
            "title": "C",
            "url": "u3",
            "raw_text": "",
        },
    ]

    diff = compute_diff(yesterday, today)
    assert "toss-3" in diff["new"]  # 신규
    assert "toss-2" in diff["closed"]  # 마감
    assert "toss-1" in diff["kept"]  # 유지

    # 수집 실패 CoverageState 노출 — 조용한 무시 금지
    state = CoverageState()
    state.record_failure("toss", error="timeout")
    assert state.has_failures()
    failures = state.get_failures()
    assert any(f["source"] == "toss" for f in failures)


# ---------------------------------------------------------------------------
# manual 폴백: === JOB === 블록 파싱 + 필수필드 누락 스킵 (§3 jobs_manual 동등)
# ---------------------------------------------------------------------------


def test_manual_fallback_parses_blocks_and_skips_incomplete():
    """parse_manual: === JOB === 블록 → raw 공고, job_id 등 필수필드 누락 블록은 스킵."""
    from crawler.manual import parse_manual

    text = (
        "=== JOB ===\n"
        "job_id: manual-1\n"
        "company: toss\n"
        "title: Frontend Engineer\n"
        "url: https://toss.im/jobs/manual-1\n"
        "We are hiring a frontend engineer.\n"
        "React, TypeScript.\n"
        "\n"
        "=== JOB ===\n"
        "company: daangn\n"
        "title: Backend\n"
        "url: https://daangn.com/x\n"
        "job_id 누락 → 이 블록은 스킵돼야 함\n"
    )

    jobs = parse_manual(text)

    # 두 번째 블록은 job_id 누락 → 스킵
    assert len(jobs) == 1
    j = jobs[0]
    assert j["job_id"] == "manual-1"
    assert j["company"] == "toss"
    assert j["title"] == "Frontend Engineer"
    assert j["url"] == "https://toss.im/jobs/manual-1"
    # 필드 선언 줄은 제거되고 본문만 raw_text로 남는다
    assert "frontend engineer" in j["raw_text"].lower()
    assert "job_id:" not in j["raw_text"]
