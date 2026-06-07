"""T-073 Tier2 외국계 한국 채용 어댑터 테스트 — AC-1, AC-2, AC-3.

어댑터: ForeignCustomAdapter (글로벌 custom 소스 공통) + Workday/Greenhouse(location=KR).
fixture 기반 오프라인 테스트 — 실 네트워크 불필요.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_mock_client(fixture_data: dict, status_code: int = 200) -> MagicMock:
    """dict fixture를 반환하는 mock httpx client 생성."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = fixture_data
    mock_resp.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    return mock_client


# ---------------------------------------------------------------------------
# AC-1: Tier2 registry_seed ATS + custom 어댑터 수집 → job_postings upsert
# ---------------------------------------------------------------------------


def test_AC_1_tier2_sources_collected_workday():
    """AC-1 (workday tier2): NVIDIA/Intel/Salesforce WorkdayAdapter → RawJob list.

    registry_seed Tier2 workday 소스가 WorkdayAdapter로 수집된다.
    """
    from crawler.adapters.workday import WorkdayAdapter
    from crawler.sources.registry_seed import SOURCE_SPECS

    tier2_workday = [s for s in SOURCE_SPECS if s.tier == 2 and s.method == "workday"]
    assert len(tier2_workday) >= 3  # NVIDIA·Intel·Salesforce 최소 3개

    fixture = json.loads(
        (FIXTURES_DIR / "workday_jobs.json").read_text(encoding="utf-8")
    )
    client = _make_mock_client(fixture)

    for spec in tier2_workday:
        if spec.status not in ("ats-ready", "custom-ready"):
            continue
        adapter = WorkdayAdapter(tenant=spec.ats_slug or spec.company, client=client)
        jobs = adapter.fetch_jobs(location="KR")
        assert isinstance(jobs, list), f"{spec.company}: fetch_jobs must return list"


def test_AC_1_tier2_sources_collected_greenhouse():
    """AC-1 (greenhouse tier2): Moloco/Sendbird/Databricks GreenhouseAdapter → RawJob list.

    registry_seed Tier2 greenhouse 소스가 GreenhouseAdapter로 수집된다.
    """
    from crawler.adapters.greenhouse import GreenhouseAdapter
    from crawler.sources.registry_seed import SOURCE_SPECS

    tier2_gh = [s for s in SOURCE_SPECS if s.tier == 2 and s.method == "greenhouse"]
    assert len(tier2_gh) >= 3  # moloco·sendbird·databricks

    fixture = json.loads(
        (FIXTURES_DIR / "greenhouse_jobs.json").read_text(encoding="utf-8")
    )
    client = _make_mock_client(fixture)

    for spec in tier2_gh:
        if spec.status not in ("ats-ready",):
            continue
        adapter = GreenhouseAdapter(company_slug=spec.ats_slug, client=client)
        jobs = adapter.fetch_jobs(location="KR")
        assert isinstance(jobs, list), f"{spec.company}: fetch_jobs must return list"


def test_AC_1_tier2_custom_global_adapters_collected():
    """AC-1 (custom global): ForeignCustomAdapter 서브클래스들 → RawJob list.

    Google·Amazon·Meta 등 글로벌 custom 소스 어댑터가 BaseCustomAdapter 상속하고
    fetch_jobs() → RawJob list를 반환한다.
    """
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.foreign_amazon import AmazonAdapter
    from crawler.adapters.foreign_google import GoogleAdapter
    from crawler.adapters.foreign_meta import MetaAdapter

    for cls in (GoogleAdapter, AmazonAdapter, MetaAdapter):
        assert issubclass(cls, BaseCustomAdapter), (
            f"{cls.__name__} must subclass BaseCustomAdapter"
        )

    # Google fixture
    google_fixture = {
        "jobs": [
            {
                "id": "google-001",
                "title": "Software Engineer",
                "url": "https://careers.google.com/jobs/results/google-001",
                "location": "Seoul, South Korea",
                "description": "Google Korea engineering team.",
            }
        ]
    }
    client = _make_mock_client(google_fixture)
    jobs = GoogleAdapter(client=client).fetch_jobs(location="KR")
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert "job_id" in job
        assert "company" in job
        assert "title" in job
        assert "url" in job
        assert "raw_text" in job


def test_AC_1_tier2_custom_more_adapters():
    """AC-1 (더 많은 custom): Microsoft/Apple/Uber 어댑터 → RawJob list."""
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.foreign_apple import AppleAdapter
    from crawler.adapters.foreign_microsoft import MicrosoftAdapter
    from crawler.adapters.foreign_uber import UberAdapter

    for cls in (MicrosoftAdapter, AppleAdapter, UberAdapter):
        assert issubclass(cls, BaseCustomAdapter), (
            f"{cls.__name__} must subclass BaseCustomAdapter"
        )

    ms_fixture = {
        "operationResult": {
            "result": {
                "jobs": [
                    {
                        "jobId": "ms-001",
                        "title": "Software Engineer",
                        "jobDetailsUrl": "/en/jobs/ms-001",
                        "primaryWorkLocation": "Seoul, South Korea",
                        "descriptionTeaser": "Microsoft Korea engineering role.",
                    }
                ]
            }
        }
    }
    client = _make_mock_client(ms_fixture)
    jobs = MicrosoftAdapter(client=client).fetch_jobs(location="KR")
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert "job_id" in job
        assert "title" in job
        assert "url" in job


# ---------------------------------------------------------------------------
# AC-2: location 혼합 fixture → KR 공고만 수집
# ---------------------------------------------------------------------------


def test_AC_2_korea_location_filter_google():
    """AC-2 (google): 서울/해외 혼합 fixture → Seoul 공고만 수집."""
    from crawler.adapters.foreign_google import GoogleAdapter

    mixed_fixture = {
        "jobs": [
            {
                "id": "g-kr-001",
                "title": "Software Engineer",
                "url": "https://careers.google.com/jobs/g-kr-001",
                "location": "Seoul, South Korea",
                "description": "Seoul engineering role.",
            },
            {
                "id": "g-us-001",
                "title": "Backend Engineer",
                "url": "https://careers.google.com/jobs/g-us-001",
                "location": "Mountain View, CA, USA",
                "description": "MTV engineering role.",
            },
            {
                "id": "g-kr-002",
                "title": "Platform Engineer",
                "url": "https://careers.google.com/jobs/g-kr-002",
                "location": "Korea",
                "description": "Korea platform team.",
            },
        ]
    }
    client = _make_mock_client(mixed_fixture)
    jobs = GoogleAdapter(client=client).fetch_jobs(location="KR")

    assert isinstance(jobs, list)
    # 미국 공고(Mountain View)는 제외되어야 함
    for job in jobs:
        loc = job.get("location", "").lower()
        assert any(kw in loc for kw in ("korea", "seoul", "한국", "서울")), (
            f"Non-KR job leaked: {job}"
        )


def test_AC_2_korea_location_filter_amazon():
    """AC-2 (amazon): 서울/해외 혼합 fixture → KR 공고만 수집."""
    from crawler.adapters.foreign_amazon import AmazonAdapter

    mixed_fixture = {
        "jobs": [
            {
                "id": "amz-kr-001",
                "title": "Software Development Engineer",
                "url": "https://www.amazon.jobs/en/jobs/amz-kr-001",
                "location": "Seoul, South Korea",
                "description": "AWS Korea team.",
            },
            {
                "id": "amz-us-001",
                "title": "Software Engineer",
                "url": "https://www.amazon.jobs/en/jobs/amz-us-001",
                "location": "Seattle, WA, United States",
                "description": "Seattle team.",
            },
        ]
    }
    client = _make_mock_client(mixed_fixture)
    jobs = AmazonAdapter(client=client).fetch_jobs(location="KR")

    assert isinstance(jobs, list)
    for job in jobs:
        loc = job.get("location", "").lower()
        assert any(kw in loc for kw in ("korea", "seoul", "한국", "서울")), (
            f"Non-KR job leaked: {job}"
        )


def test_AC_2_korea_location_filter_workday_tier2():
    """AC-2 (workday tier2): locationsText 혼합 → 한국 공고만 수집."""
    from crawler.adapters.workday import WorkdayAdapter

    mixed_fixture = {
        "jobPostings": [
            {
                "id": "wd-kr-001",
                "title": "Software Engineer",
                "externalUrl": "https://nvidia.wd5.myworkdayjobs.com/kr-001",
                "locationsText": "Seoul, South Korea",
                "briefDescription": "NVIDIA Korea role.",
            },
            {
                "id": "wd-us-001",
                "title": "Backend Engineer",
                "externalUrl": "https://nvidia.wd5.myworkdayjobs.com/us-001",
                "locationsText": "Santa Clara, CA, USA",
                "briefDescription": "NVIDIA HQ role.",
            },
        ]
    }
    client = _make_mock_client(mixed_fixture)
    adapter = WorkdayAdapter(tenant="nvidia", client=client)
    jobs = adapter.fetch_jobs(location="KR")

    assert isinstance(jobs, list)
    # 미국 공고 제외 확인
    job_ids = [j["job_id"] for j in jobs]
    assert not any("us-001" in jid for jid in job_ids), "US job must be filtered out"
    assert any("kr-001" in jid for jid in job_ids), "KR job must be included"


# ---------------------------------------------------------------------------
# AC-3: 한국 채용 0 소스 → status=no-korea-jobs
# ---------------------------------------------------------------------------


def test_AC_3_no_korea_jobs_status():
    """AC-3: 한국 공고 0건 fixture → fetch_jobs()가 빈 리스트 반환하고,
    상태는 no-korea-jobs로 기록된다(레지스트리 status 확인).
    """
    from crawler.adapters.foreign_google import GoogleAdapter

    # 전부 해외 공고 fixture
    all_foreign_fixture = {
        "jobs": [
            {
                "id": "g-us-001",
                "title": "Software Engineer",
                "url": "https://careers.google.com/jobs/g-us-001",
                "location": "Mountain View, CA, USA",
                "description": "MTV engineering.",
            },
            {
                "id": "g-uk-001",
                "title": "Backend Engineer",
                "url": "https://careers.google.com/jobs/g-uk-001",
                "location": "London, United Kingdom",
                "description": "London engineering.",
            },
        ]
    }
    client = _make_mock_client(all_foreign_fixture)
    adapter = GoogleAdapter(client=client)
    jobs = adapter.fetch_jobs(location="KR")

    # 한국 공고 없음 → 빈 리스트
    assert isinstance(jobs, list)
    assert len(jobs) == 0, "All non-KR jobs should be filtered out"


def test_AC_3_no_korea_jobs_status_recorded():
    """AC-3: fetch_jobs_with_status()가 한국 공고 0건일 때 status=no-korea-jobs를 반환."""
    from crawler.adapters.foreign_google import GoogleAdapter, fetch_jobs_with_status

    all_foreign_fixture = {
        "jobs": [
            {
                "id": "g-us-001",
                "title": "Software Engineer",
                "url": "https://careers.google.com/jobs/g-us-001",
                "location": "Mountain View, CA, USA",
                "description": "MTV engineering.",
            },
        ]
    }
    client = _make_mock_client(all_foreign_fixture)
    adapter = GoogleAdapter(client=client)
    jobs, status = fetch_jobs_with_status(adapter, location="KR")

    assert jobs == []
    assert status == "no-korea-jobs"


def test_AC_3_active_source_has_status_when_jobs_exist():
    """AC-3: 한국 공고 있으면 status=active(조용한 누락 없음)."""
    from crawler.adapters.foreign_google import GoogleAdapter, fetch_jobs_with_status

    kr_fixture = {
        "jobs": [
            {
                "id": "g-kr-001",
                "title": "Software Engineer",
                "url": "https://careers.google.com/jobs/g-kr-001",
                "location": "Seoul, South Korea",
                "description": "Seoul engineering.",
            },
        ]
    }
    client = _make_mock_client(kr_fixture)
    adapter = GoogleAdapter(client=client)
    jobs, status = fetch_jobs_with_status(adapter, location="KR")

    assert len(jobs) >= 1
    assert status == "active"
