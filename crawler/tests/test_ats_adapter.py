"""T-062 ATS 어댑터 인프라 테스트 — AC-1, AC-3."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# AC-1: GreenhouseAdapter.fetch_jobs() → RawJob list + 레지스트리 tier·status
# ---------------------------------------------------------------------------


def test_AC_1_greenhouse_adapter_fetch_and_registry():
    """AC-1: Greenhouse fixture(daangn slug) → RawJob list 반환, 레지스트리 등록 확인."""
    from crawler.adapters.greenhouse import GreenhouseAdapter
    from crawler.sources.registry import SourceEntry, SourceRegistry

    # fixture JSON 로드
    fixture_data = json.loads(
        (FIXTURES_DIR / "greenhouse_jobs.json").read_text(encoding="utf-8")
    )

    # 오프라인 테스트: httpx client를 mock으로 대체
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fixture_data
    mock_resp.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    adapter = GreenhouseAdapter(company_slug="daangn", client=mock_client)
    jobs = adapter.fetch_jobs()

    # RawJob(dict) list 반환 검증
    assert isinstance(jobs, list)
    assert len(jobs) == 3
    for job in jobs:
        assert isinstance(job, dict)
        assert "job_id" in job
        assert "company" in job
        assert "title" in job
        assert "url" in job
        assert "raw_text" in job
        assert job["company"] == "daangn"
        # HTML 태그 제거 확인
        assert "<p>" not in job["raw_text"]

    # 레지스트리 등록 및 tier·status 포함 확인
    registry = SourceRegistry()
    entry = SourceEntry(
        company="daangn",
        adapter_cls=GreenhouseAdapter,
        tier="대기업",
        status="수집 중",
        adapter_kwargs={"company_slug": "daangn"},
    )
    registry.register(entry)

    active = registry.get_active_sources()
    assert len(active) == 1
    assert active[0].company == "daangn"
    assert active[0].tier == "대기업"
    assert active[0].status == "수집 중"


def test_AC_1_toss_adapter_fetch():
    """AC-1: TossAdapter.fetch_jobs() → RawJob list (기존 fetch_toss_jobs 동작 보존)."""
    from crawler.adapters.toss import TossAdapter

    toss_list_fixture = {
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
    toss_detail_fixture = {
        "success": {
            "content": "<p>We are looking for a <b>Frontend Engineer</b></p>",
            "title": "Frontend Engineer",
            "absolute_url": "https://toss.im/jobs/12345",
        }
    }

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        if "jobs/12345" in url and "jobs/12345" != url.split("/")[-1] + "/jobs":
            resp.json.return_value = toss_detail_fixture
        elif url.endswith("/jobs"):
            resp.json.return_value = toss_list_fixture
        else:
            resp.json.return_value = toss_detail_fixture
        return resp

    mock_client = MagicMock()
    mock_client.get.side_effect = mock_get

    adapter = TossAdapter(client=mock_client)
    jobs = adapter.fetch_jobs()

    # 키워드 필터: "Frontend Engineer" 통과, "콘텐츠 마케터" 제외
    assert len(jobs) == 1
    assert jobs[0]["company"] == "toss"
    assert jobs[0]["title"] == "Frontend Engineer"
    assert "<p>" not in jobs[0]["raw_text"]


def test_AC_1_base_adapter_interface():
    """AC-1: BaseCrawlerAdapter 추상 인터페이스가 올바르게 정의됨."""
    import inspect

    from crawler.adapters.base import BaseCrawlerAdapter, GateResult

    # ABC임을 확인 (직접 인스턴스화 불가)
    assert inspect.isabstract(BaseCrawlerAdapter)

    # GateResult dataclass 검증
    result = GateResult(ok=True, reason="success")
    assert result.ok is True
    assert result.reason == "success"

    result_fail = GateResult(ok=False, reason="HTTP 403")
    assert result_fail.ok is False


def test_AC_1_build_default_registry_seeds_sources():
    """AC-1 (구현 #4): build_default_registry가 toss(custom)·daangn(Greenhouse)·greenhouse 회사 ≥1을 활성 등록."""
    from crawler.adapters.greenhouse import GreenhouseAdapter
    from crawler.adapters.toss import TossAdapter
    from crawler.sources.registry import build_default_registry

    registry = build_default_registry()
    active = registry.get_active_sources()

    by_company = {e.company: e for e in active}
    # toss + daangn + greenhouse 회사 ≥1 (총 ≥3)
    assert {"toss", "daangn"} <= by_company.keys()
    assert len(active) >= 3
    # 어댑터 매핑: toss=custom, daangn=Greenhouse
    assert by_company["toss"].adapter_cls is TossAdapter
    assert by_company["daangn"].adapter_cls is GreenhouseAdapter
    # 모든 seed가 tier·status·adapter_cls 보유
    for e in active:
        assert e.tier
        assert e.status == "수집 중"
        assert e.adapter_cls is not None


# ---------------------------------------------------------------------------
# AC-3: 애그리게이터 도메인 등록 시 ValueError
# ---------------------------------------------------------------------------


def test_AC_3_aggregator_registration_raises():
    """AC-3: 애그리게이터 도메인 레지스트리 등록 시 ValueError raise, 소스 미등록."""
    from crawler.adapters.greenhouse import GreenhouseAdapter
    from crawler.sources.registry import SourceEntry, SourceRegistry

    registry = SourceRegistry()

    # 애그리게이터 도메인 등록 시도 — ValueError 예상
    with pytest.raises(ValueError, match="aggregator"):
        entry = SourceEntry(
            company="jobkorea",
            adapter_cls=GreenhouseAdapter,
            tier="대기업",
            status="수집 중",
            adapter_kwargs={
                "company_slug": "jobkorea",
                "base_url": "https://jobkorea.co.kr/jobs",
            },
        )
        registry.register(entry)

    # 등록 실패 후 소스가 없음을 확인
    assert len(registry.get_active_sources()) == 0


@pytest.mark.parametrize(
    "domain",
    [
        "jobkorea.co.kr",
        "saramin.co.kr",
        "wanted.co.kr",
    ],
)
def test_AC_3_all_banned_domains_raise(domain):
    """AC-3: 모든 금지 도메인이 ValueError를 raise한다."""
    from crawler.adapters.greenhouse import GreenhouseAdapter
    from crawler.sources.registry import SourceEntry, SourceRegistry

    registry = SourceRegistry()

    with pytest.raises(ValueError):
        entry = SourceEntry(
            company="test",
            adapter_cls=GreenhouseAdapter,
            tier="스타트업",
            status="수집 중",
            adapter_kwargs={
                "company_slug": "test",
                "base_url": f"https://{domain}/jobs",
            },
        )
        registry.register(entry)
