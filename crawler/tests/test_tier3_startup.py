"""T-074 Tier3 스타트업 소스 테스트 — AC-1, AC-2, AC-3.

어댑터: Tier3 custom 8사(BaseCustomAdapter) + 그리팅 7사·workday 2사(공유 어댑터).
fixture 기반 오프라인 테스트 — 실 네트워크 불필요.
"""

from __future__ import annotations

from unittest.mock import MagicMock


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
# AC-1: Tier3 custom 8사 어댑터 → BaseCustomAdapter 상속 + RawJob upsert
# ---------------------------------------------------------------------------

_STARTUP_JOB_FIXTURE = {
    "jobs": [
        {
            "id": "startup-001",
            "title": "Software Engineer",
            "url": "https://example.com/jobs/startup-001",
            "location": "Seoul",
            "description": "스타트업 개발자 포지션.",
        }
    ]
}


def test_AC_1_custom_startups_collected():
    """AC-1: Tier3 custom 8사 어댑터가 BaseCustomAdapter를 상속하고 RawJob list를 반환."""
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.startup_bithumb import BithumbAdapter
    from crawler.adapters.startup_bucketplace import BucketplaceAdapter
    from crawler.adapters.startup_class101 import Class101Adapter
    from crawler.adapters.startup_dunamu import DunamuAdapter
    from crawler.adapters.startup_megazone import MegazoneAdapter
    from crawler.adapters.startup_socar import SocarAdapter
    from crawler.adapters.startup_tridge import TridgeAdapter
    from crawler.adapters.startup_zigbang import ZigbangAdapter

    adapters_to_test = [
        DunamuAdapter,
        ZigbangAdapter,
        BucketplaceAdapter,
        SocarAdapter,
        BithumbAdapter,
        TridgeAdapter,
        MegazoneAdapter,
        Class101Adapter,
    ]

    for cls in adapters_to_test:
        assert issubclass(cls, BaseCustomAdapter), (
            f"{cls.__name__} must subclass BaseCustomAdapter"
        )

    # 각 어댑터가 RawJob list를 반환하는지 확인
    for cls in adapters_to_test:
        client = _make_mock_client(_STARTUP_JOB_FIXTURE)
        adapter = cls(client=client)
        jobs = adapter.fetch_jobs(location="KR")
        assert isinstance(jobs, list), f"{cls.__name__}: fetch_jobs must return list"
        assert len(jobs) >= 1, (
            f"{cls.__name__}: should return at least 1 job from fixture"
        )
        for job in jobs:
            assert "job_id" in job, f"{cls.__name__}: missing job_id"
            assert "company" in job, f"{cls.__name__}: missing company"
            assert "title" in job, f"{cls.__name__}: missing title"
            assert "url" in job, f"{cls.__name__}: missing url"
            assert "raw_text" in job, f"{cls.__name__}: missing raw_text"


def test_AC_1_tier3_custom_registry_mapping():
    """AC-1: registry_seed Tier3 custom-ready 소스가 어댑터와 매핑된다."""
    from crawler.sources.registry_seed import SOURCE_SPECS

    tier3_custom_ready = [
        s
        for s in SOURCE_SPECS
        if s.tier == 3 and s.method == "custom" and s.status == "custom-ready"
    ]
    # dunamu·zigbang·bucketplace·socar·bithumb·toss·tridge·megazone·class101 = 9사
    assert len(tier3_custom_ready) >= 8, (
        f"Expected >=8 Tier3 custom-ready sources, got {len(tier3_custom_ready)}"
    )
    company_names = {s.company for s in tier3_custom_ready}
    for expected in (
        "dunamu",
        "zigbang",
        "bucketplace",
        "socar",
        "bithumb",
        "tridge",
        "megazone",
        "class101",
    ):
        assert expected in company_names, f"Missing Tier3 custom source: {expected}"


# ---------------------------------------------------------------------------
# AC-2: 그리팅 7사·workday 2사 → 공유 어댑터 재사용 (신규 어댑터 0)
# ---------------------------------------------------------------------------


def test_AC_2_greeting_workday_shared_adapter():
    """AC-2: Tier3 그리팅 7사·workday 2사가 공유 어댑터로 수집(신규 어댑터 구현 없음)."""
    from crawler.adapters.greeting import GreetingAdapter
    from crawler.adapters.workday import WorkdayAdapter
    from crawler.sources.registry_seed import SOURCE_SPECS

    tier3_greeting = [
        s
        for s in SOURCE_SPECS
        if s.tier == 3 and s.method == "greeting" and s.status == "ats-ready"
    ]
    tier3_workday = [
        s
        for s in SOURCE_SPECS
        if s.tier == 3 and s.method == "workday" and s.status == "ats-ready"
    ]

    assert len(tier3_greeting) == 7, (
        f"Expected 7 Tier3 greeting sources, got {len(tier3_greeting)}"
    )
    assert len(tier3_workday) == 2, (
        f"Expected 2 Tier3 workday sources, got {len(tier3_workday)}"
    )

    greeting_fixture = {
        "data": [
            {
                "id": "g-001",
                "title": "Software Engineer",
                "url": "https://kurly.career.greetinghr.com/jobs/g-001",
                "location": "서울",
                "description": "백엔드 개발자.",
            }
        ]
    }
    workday_fixture = {
        "jobPostings": [
            {
                "id": "wd-001",
                "title": "Backend Engineer",
                "externalUrl": "https://yanolja.wd102.myworkdayjobs.com/wd-001",
                "locationsText": "Seoul, South Korea",
                "briefDescription": "야놀자 서버 개발자.",
            }
        ]
    }

    # 그리팅 어댑터로 각 slug 수집
    for spec in tier3_greeting:
        client = _make_mock_client(greeting_fixture)
        adapter = GreetingAdapter(company=spec.ats_slug, client=client)
        jobs = adapter.fetch_jobs(location="KR")
        assert isinstance(jobs, list), f"greeting {spec.company}: must return list"

    # workday 어댑터로 각 slug 수집
    for spec in tier3_workday:
        client = _make_mock_client(workday_fixture)
        adapter = WorkdayAdapter(tenant=spec.ats_slug, client=client)
        jobs = adapter.fetch_jobs(location="KR")
        assert isinstance(jobs, list), f"workday {spec.company}: must return list"


# ---------------------------------------------------------------------------
# AC-3: 구조변경 fixture(parse 실패율 ≥30%) → gate_check → status blocked/unsupported
# ---------------------------------------------------------------------------


def test_AC_3_gate_failure_status():
    """AC-3: parse 실패율 ≥30% fixture → GateResult(ok=False) + 상태 명시."""
    from crawler.adapters.base import GateResult
    from crawler.adapters.startup_dunamu import DunamuAdapter

    # 필수 필드 없는 broken fixture (4개 중 3개 실패 = 75%)
    broken_fixture = {
        "jobs": [
            {"broken": "no id no title"},
            {"broken": "no id no title"},
            {"broken": "no id no title"},
            {
                "id": "ok-1",
                "title": "Backend Engineer",
                "url": "https://careers.dunamu.com/ok-1",
            },
        ]
    }
    client = _make_mock_client(broken_fixture)
    adapter = DunamuAdapter(client=client)
    result = adapter.gate_check()

    assert isinstance(result, GateResult)
    assert result.ok is False
    assert "parse failure" in result.reason.lower() or "%" in result.reason


def test_AC_3_blocked_403():
    """AC-3: 403 응답 → GateResult(ok=False, reason에 '403' 포함)."""
    from crawler.adapters.base import GateResult
    from crawler.adapters.startup_socar import SocarAdapter

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    adapter = SocarAdapter(client=mock_client)
    result = adapter.gate_check()

    assert isinstance(result, GateResult)
    assert result.ok is False
    assert "403" in result.reason or "block" in result.reason.lower()


def test_AC_3_gate_ok_when_valid_structure():
    """AC-3 (정상 구조): 정상 fixture → GateResult(ok=True) — 조용한 누락 없음."""
    from crawler.adapters.base import GateResult
    from crawler.adapters.startup_tridge import TridgeAdapter

    valid_fixture = {
        "jobs": [
            {
                "id": "t-001",
                "title": "Software Engineer",
                "url": "https://careers.tridge.com/t-001",
            },
            {
                "id": "t-002",
                "title": "Backend Developer",
                "url": "https://careers.tridge.com/t-002",
            },
        ]
    }
    client = _make_mock_client(valid_fixture)
    adapter = TridgeAdapter(client=client)
    result = adapter.gate_check()

    assert isinstance(result, GateResult)
    assert result.ok is True
