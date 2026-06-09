"""T-075 Tier4 대기업 통합포털 + 위탁 SaaS 테스트 — AC-1, AC-2, AC-3.

어댑터: 그룹 통합포털 custom(삼성·LG·SK·두산·한화) + 개별 custom(현대차·KT 등)
        + 위탁 SaaS recruiter.co.kr(T-075 신설, T-076 공유).
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


def _make_post_client(fixture_data: dict, status_code: int = 200) -> MagicMock:
    """POST 응답(resp.json)을 반환하는 mock client — recruiter.co.kr 등 POST API용."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = fixture_data
    mock_resp.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp
    return mock_client


# ---------------------------------------------------------------------------
# AC-1: list-public custom/SaaS 소스 공고 upsert + 그룹 통합포털 계열사 구분
# ---------------------------------------------------------------------------

_CONGLOMERATE_JOB_FIXTURE = {
    "jobs": [
        {
            "id": "cong-001",
            "title": "Software Engineer",
            "url": "https://example.com/jobs/cong-001",
            "company": "삼성전자",
            "location": "서울",
            "description": "대기업 개발자 포지션.",
        }
    ]
}


def test_AC_1_public_conglomerate_collected():
    """AC-1: list-public Tier4 custom 어댑터가 BaseCustomAdapter를 상속하고 RawJob list를 반환."""
    from crawler.adapters.conglomerate_doosan import DoosanAdapter
    from crawler.adapters.conglomerate_hanwha import HanwhaAdapter
    from crawler.adapters.conglomerate_hyundai import HyundaiAdapter
    from crawler.adapters.conglomerate_kt import KTAdapter
    from crawler.adapters.conglomerate_lg import LGAdapter
    from crawler.adapters.conglomerate_samsung import SamsungAdapter
    from crawler.adapters.conglomerate_sk import SKAdapter
    from crawler.adapters.custom_base import BaseCustomAdapter

    adapters_to_test = [
        SamsungAdapter,
        LGAdapter,
        SKAdapter,
        DoosanAdapter,
        HanwhaAdapter,
        HyundaiAdapter,
        KTAdapter,
    ]

    for cls in adapters_to_test:
        assert issubclass(cls, BaseCustomAdapter), (
            f"{cls.__name__} must subclass BaseCustomAdapter"
        )

    for cls in adapters_to_test:
        client = _make_mock_client(_CONGLOMERATE_JOB_FIXTURE)
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


def test_AC_1_group_portal_affiliate_distinction():
    """AC-1: 그룹 통합포털 어댑터가 계열사별로 company 값을 구분해 반환한다."""
    from crawler.adapters.conglomerate_samsung import SamsungAdapter

    for company in ("samsung-electronics", "samsung-sds", "samsung-electro-mechanics"):
        client = _make_mock_client(_CONGLOMERATE_JOB_FIXTURE)
        adapter = SamsungAdapter(company=company, client=client)
        jobs = adapter.fetch_jobs(location="KR")
        assert len(jobs) >= 1, f"{company}: should return at least 1 job"
        for job in jobs:
            assert job["company"] == company, (
                f"Expected company={company}, got {job['company']}"
            )


def test_AC_1_tier4_registry_mapping():
    """AC-1: registry_seed Tier4 custom-ready 소스가 어댑터와 매핑된다."""
    from crawler.sources.registry_seed import SOURCE_SPECS

    tier4_custom_ready = [
        s
        for s in SOURCE_SPECS
        if s.tier == 4 and s.method == "custom" and s.status == "custom-ready"
    ]
    # 삼성3·LG3·SK1·두산1·한화1·현대차1·kt1 = 11사
    assert len(tier4_custom_ready) >= 8, (
        f"Expected >=8 Tier4 custom-ready sources, got {len(tier4_custom_ready)}"
    )

    expected_companies = {
        "samsung-electronics",
        "samsung-sds",
        "lg-electronics",
        "lg-cns",
        "doosan",
        "hanwha-systems",
        "hyundai-motor",
        "kt",
    }
    actual_companies = {s.company for s in tier4_custom_ready}
    for expected in expected_companies:
        assert expected in actual_companies, (
            f"Missing Tier4 custom-ready source: {expected}"
        )


# ---------------------------------------------------------------------------
# AC-2: recruiter.co.kr 어댑터가 공고를 수집하고 T-076 재사용 가능
# ---------------------------------------------------------------------------

# JOBFLEX/JOBDA position-list API 응답 구조(라이브 확인): pagination + list[positionSn,title,...].
_RECRUITER_FIXTURE = {
    "pagination": {"page": 1, "size": 100, "totalCount": 1, "totalPages": 1},
    "list": [
        {
            "positionSn": 12345,
            "title": "Backend Engineer",
            "careerType": "CAREER",
            "classificationCode": "수시",
            "tagList": [{"tagName": "개발"}],
        }
    ],
}


def test_AC_2_recruiter_co_kr_adapter_shared():
    """AC-2: recruiter_co_kr 어댑터가 공고를 수집하고 다른 회사(slug만 변경) 재사용 가능."""
    from crawler.adapters.base import BaseCrawlerAdapter
    from crawler.adapters.recruiter_co_kr import RecruiterCoKrAdapter

    assert issubclass(RecruiterCoKrAdapter, BaseCrawlerAdapter)

    # 신세계 I&C 수집 (POST position-list API mock)
    adapter = RecruiterCoKrAdapter(
        company="shinsegae-inc",
        slug="shinsegae",
        client=_make_post_client(_RECRUITER_FIXTURE),
    )
    jobs = adapter.fetch_jobs(location="KR")
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert "job_id" in job
        assert "company" in job
        assert job["company"] == "shinsegae-inc"
        assert "title" in job
        assert "url" in job
        assert "raw_text" in job

    # kt-ds 재사용(slug만 변경)
    adapter2 = RecruiterCoKrAdapter(
        company="kt-ds", slug="ktds", client=_make_post_client(_RECRUITER_FIXTURE)
    )
    jobs2 = adapter2.fetch_jobs(location="KR")
    assert isinstance(jobs2, list)
    assert len(jobs2) >= 1
    for job in jobs2:
        assert job["company"] == "kt-ds"


def test_AC_2_tier5_recruiter_reuse():
    """AC-2: T-076(Tier5) registry_seed recruiter_co_kr 소스가 동일 어댑터 재사용 가능."""
    from crawler.adapters.recruiter_co_kr import RecruiterCoKrAdapter
    from crawler.sources.registry_seed import SOURCE_SPECS

    tier5_recruiter = [
        s
        for s in SOURCE_SPECS
        if s.tier == 5 and s.method == "recruiter_co_kr" and s.status == "custom-ready"
    ]
    # shinhan-bank·shinhan-ds·hana-bank·hana-ti·hyundai-card = 5사
    assert len(tier5_recruiter) >= 3, (
        f"Expected >=3 Tier5 recruiter_co_kr sources, got {len(tier5_recruiter)}"
    )

    for spec in tier5_recruiter:
        adapter = RecruiterCoKrAdapter(
            company=spec.company,
            slug=spec.ats_slug,
            client=_make_post_client(_RECRUITER_FIXTURE),
        )
        jobs = adapter.fetch_jobs(location="KR")
        assert isinstance(jobs, list), f"{spec.company}: must return list"


# ---------------------------------------------------------------------------
# AC-3: list-login 소스 → 크롤링 시도 없이 status=login-required 기록
# ---------------------------------------------------------------------------


def test_AC_3_login_required_cataloged_not_crawled():
    """AC-3: view_login=True 소스는 크롤링 시도 없이 login-required status로 기록된다."""
    from crawler.sources.registry_seed import SOURCE_SPECS

    # registry_seed의 view_login=True 소스는 status=login-required여야 한다
    login_required_sources = [s for s in SOURCE_SPECS if s.status == "login-required"]
    view_login_true_sources = [s for s in SOURCE_SPECS if s.view_login]

    # login-required status인 소스는 view_login=True여야 한다(둘 다 0이어도 AC 성립)
    for s in login_required_sources:
        assert s.view_login is True, (
            f"{s.company}: status=login-required but view_login=False"
        )
    # 역방향: view_login=True 소스는 status=login-required여야 한다(거짓 완전성 0)
    for s in view_login_true_sources:
        assert s.status == "login-required", (
            f"{s.company}: view_login=True but status={s.status}"
        )


def test_AC_3_login_required_handler():
    """AC-3: LoginRequiredSource는 fetch_jobs() 호출 시 빈 list + status=login-required."""
    from crawler.adapters.conglomerate_login_required import LoginRequiredSource

    source = LoginRequiredSource(company="test-login-company")
    jobs = source.fetch_jobs(location="KR")
    assert jobs == [], "login-required 소스는 공고를 수집하면 안 된다"

    status = source.get_status()
    assert status == "login-required", f"Expected 'login-required', got {status!r}"


def test_AC_3_coverage_panel_transparent():
    """AC-3: login-required 소스가 coverage 패널에 투명 노출(거짓 완전성 0)."""
    from crawler.adapters.base import GateResult
    from crawler.adapters.conglomerate_login_required import LoginRequiredSource

    source = LoginRequiredSource(company="test-login-company")
    result = source.gate_check()
    # gate_check는 GateResult(ok=False, reason='login-required')를 반환해야 한다
    assert isinstance(result, GateResult)
    assert result.ok is False
    assert "login" in result.reason.lower()
