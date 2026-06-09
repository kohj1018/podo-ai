"""T-071 ATS 패밀리 어댑터 테스트 — AC-1, AC-2, AC-3.

어댑터: GreetingAdapter·WorkdayAdapter·LeverAdapter·AshbyAdapter.
fixture 기반 오프라인 테스트 — 실 네트워크 불필요.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# AC-1: 각 어댑터 fetch_jobs() → RawJob list + BaseCrawlerAdapter 인터페이스 정합
# ---------------------------------------------------------------------------


# greetinghr careers 페이지의 React Query dehydrate 구조 모사(HTML 임베디드 openings JSON).
_GREETING_HTML = (
    '<html><body>x"state":{"data":[{"openingId":111,"title":"백엔드 엔지니어",'
    '"openingJobPosition":{"openingJobPositions":[{'
    '"workspaceField":{"field":"개발"},'
    '"workspaceOccupation":{"occupation":"백엔드"},'
    '"workspacePlace":{"place":"서울특별시 강남구","location":"역삼"},'
    '"jobPositionCareer":{"careerType":"EXPERIENCED"},'
    '"jobPositionEmployment":{"employmentType":"FULL_TIME_WORKER"}}]}}],'
    '"status":"success"},"queryKey":["openings"],"queryHash":"h"}</body></html>'
)


def _greeting_mock_client() -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = _GREETING_HTML
    mock_resp.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    return mock_client


def test_AC_1_greeting_fetch_returns_rawjob_list():
    """AC-1 (greeting): 페이지 임베디드 openings 파싱 → RawJob list + 필수 키 보유."""
    from crawler.adapters.greeting import GreetingAdapter

    adapter = GreetingAdapter(company="bbank", client=_greeting_mock_client())
    jobs = adapter.fetch_jobs()

    assert isinstance(jobs, list)
    assert len(jobs) == 1
    assert jobs[0]["url"] == "https://bbank.career.greetinghr.com/ko/o/111"
    assert jobs[0]["title"] == "백엔드 엔지니어"
    for job in jobs:
        assert isinstance(job, dict)
        for key in ("job_id", "company", "title", "url", "raw_text"):
            assert key in job


def test_AC_1_lever_fetch_returns_rawjob_list():
    """AC-1 (lever): fixture 기반 fetch_jobs() → RawJob list + 필수 키 보유."""
    from crawler.adapters.lever import LeverAdapter

    fixture_data = json.loads(
        (FIXTURES_DIR / "lever_jobs.json").read_text(encoding="utf-8")
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fixture_data
    mock_resp.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    adapter = LeverAdapter(company_slug="acme", client=mock_client)
    jobs = adapter.fetch_jobs()

    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, dict)
        assert "job_id" in job
        assert "company" in job
        assert "title" in job
        assert "url" in job
        assert "raw_text" in job


def test_AC_1_ashby_fetch_returns_rawjob_list():
    """AC-1 (ashby): fixture 기반 fetch_jobs() → RawJob list + 필수 키 보유."""
    from crawler.adapters.ashby import AshbyAdapter

    fixture_data = json.loads(
        (FIXTURES_DIR / "ashby_jobs.json").read_text(encoding="utf-8")
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fixture_data
    mock_resp.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    adapter = AshbyAdapter(company_slug="acme", client=mock_client)
    jobs = adapter.fetch_jobs()

    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, dict)
        assert "job_id" in job
        assert "company" in job
        assert "title" in job
        assert "url" in job
        assert "raw_text" in job


def test_AC_1_workday_fetch_returns_rawjob_list():
    """AC-1 (workday): fixture 기반 fetch_jobs() → RawJob list + 필수 키 보유."""
    from crawler.adapters.workday import WorkdayAdapter

    fixture_data = json.loads(
        (FIXTURES_DIR / "workday_jobs.json").read_text(encoding="utf-8")
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fixture_data
    mock_resp.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    adapter = WorkdayAdapter(tenant="nvidia", client=mock_client)
    jobs = adapter.fetch_jobs()

    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, dict)
        assert "job_id" in job
        assert "company" in job
        assert "title" in job
        assert "url" in job
        assert "raw_text" in job


def test_AC_1_all_adapters_implement_base_interface():
    """AC-1: 4개 어댑터가 모두 BaseCrawlerAdapter 서브클래스."""
    from crawler.adapters.ashby import AshbyAdapter
    from crawler.adapters.base import BaseCrawlerAdapter
    from crawler.adapters.greeting import GreetingAdapter
    from crawler.adapters.lever import LeverAdapter
    from crawler.adapters.workday import WorkdayAdapter

    for cls in (GreetingAdapter, WorkdayAdapter, LeverAdapter, AshbyAdapter):
        assert issubclass(cls, BaseCrawlerAdapter)


# ---------------------------------------------------------------------------
# AC-2: location="KR" 필터 — 한국(Korea/Seoul) 공고만 반환
# ---------------------------------------------------------------------------


def _make_mock_client(fixture_path: Path) -> MagicMock:
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = data
    mock_resp.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    return mock_client


def test_AC_2_location_filter_lever_korea_only():
    """AC-2 (lever): location="KR" → 한국 공고만 반환, 해외 공고 제외."""
    from crawler.adapters.lever import LeverAdapter

    client = _make_mock_client(FIXTURES_DIR / "lever_jobs.json")
    adapter = LeverAdapter(company_slug="acme", client=client)
    jobs = adapter.fetch_jobs(location="KR")

    # fixture에 서울/해외 혼합 — 한국만 통과해야 함
    for job in jobs:
        loc = job.get("location", "").lower()
        # location이 비어있거나(raw_text 파싱), korea/seoul 포함이어야 함
        assert any(kw in loc for kw in ("korea", "seoul", "한국", "서울")) or loc == ""


def test_AC_2_location_filter_ashby_korea_only():
    """AC-2 (ashby): location="KR" → 한국 공고만 반환, 해외 공고 제외."""
    from crawler.adapters.ashby import AshbyAdapter

    client = _make_mock_client(FIXTURES_DIR / "ashby_jobs.json")
    adapter = AshbyAdapter(company_slug="acme", client=client)
    jobs = adapter.fetch_jobs(location="KR")

    for job in jobs:
        loc = job.get("location", "").lower()
        assert any(kw in loc for kw in ("korea", "seoul", "한국", "서울")) or loc == ""


def test_AC_2_location_filter_greeting_korea_only():
    """AC-2 (greeting): location="KR" → 한국 공고만 반환(greeting은 한국 전용 ATS)."""
    from crawler.adapters.greeting import GreetingAdapter

    adapter = GreetingAdapter(company="bbank", client=_greeting_mock_client())
    jobs = adapter.fetch_jobs(location="KR")

    # greeting은 한국 스타트업 전용 → 파싱된 공고 모두 반환(별도 location 필터 없음)
    assert isinstance(jobs, list)
    assert len(jobs) == 1


def test_AC_2_location_filter_workday_korea_only():
    """AC-2 (workday): location="KR" → 한국 공고만 반환, 해외 공고 제외."""
    from crawler.adapters.workday import WorkdayAdapter

    client = _make_mock_client(FIXTURES_DIR / "workday_jobs.json")
    adapter = WorkdayAdapter(tenant="nvidia", client=client)
    jobs = adapter.fetch_jobs(location="KR")

    for job in jobs:
        loc = job.get("location", "").lower()
        assert any(kw in loc for kw in ("korea", "seoul", "한국", "서울")) or loc == ""


# ---------------------------------------------------------------------------
# AC-3: WorkdayAdapter — 구현 시 fixture 동작, 미구현 시 unsupported 명시
# ---------------------------------------------------------------------------


def test_AC_3_workday_or_unsupported():
    """AC-3: WorkdayAdapter가 구현되면 fixture 동작, 아니면 unsupported를 명시적으로 표시."""
    try:
        from crawler.adapters.workday import WorkdayAdapter  # noqa: F401

        # 구현된 경우: fixture 기반 동작 확인
        fixture_data = json.loads(
            (FIXTURES_DIR / "workday_jobs.json").read_text(encoding="utf-8")
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fixture_data
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp

        adapter = WorkdayAdapter(tenant="nvidia", client=mock_client)
        jobs = adapter.fetch_jobs()
        assert isinstance(jobs, list)

    except ImportError:
        # 미구현 — registry에 status=unsupported 등록 확인
        from crawler.sources.registry import SourceRegistry

        registry = SourceRegistry()
        unsupported = [e for e in registry.all_sources() if e.status == "unsupported"]
        assert any("workday" in e.company.lower() for e in unsupported), (
            "WorkdayAdapter 미구현 시 registry에 status=unsupported 엔트리가 있어야 한다"
        )
