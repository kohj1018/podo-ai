"""T-076 Tier5 금융권 + IT 자회사 수집 테스트 — AC-1, AC-2, AC-3.

어댑터: incruit·careerlink·applyin(신설 SaaS) + finance_*(custom 인터넷은행·증권)
        + recruiter_co_kr(T-075 재사용) + greeting(T-071 재사용)
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
# AC-1: list-public 위탁SaaS·custom 소스 공고 upsert + 미수집 status 기록
# ---------------------------------------------------------------------------

_INCRUIT_FIXTURE = {
    "list": [
        {
            "jobNo": "ibk-001",
            "title": "Software Engineer",
            "url": "https://ibk.incruit.com/jobs/ibk-001",
            "description": "IBK 기업은행 개발자 채용.",
        }
    ]
}

_CAREERLINK_FIXTURE = {
    "jobs": [
        {
            "jobId": "woori-001",
            "title": "Backend Developer",
            "applyUrl": "https://woori.careerlink.kr/jobs/woori-001",
            "jobContent": "우리은행 백엔드 개발.",
        }
    ]
}

_APPLYIN_FIXTURE = {
    "recruitList": [
        {
            "recNo": "ksc-001",
            "recTitle": "Data Engineer",
            "applyUrl": "https://koscom.applyin.co.kr/jobs/ksc-001",
            "recContent": "코스콤 데이터 엔지니어.",
        }
    ]
}

_FINANCE_CUSTOM_FIXTURE = {
    "data": [
        {
            "id": "kb-001",
            "title": "iOS Developer",
            "url": "https://recruit.kakaobank.com/jobs/kb-001",
            "description": "카카오뱅크 iOS 개발.",
        }
    ]
}


def test_AC_1_public_finance_collected():
    """AC-1: list-public Tier5 위탁SaaS·custom 어댑터가 BaseCustomAdapter를 상속하고 RawJob list를 반환."""
    from crawler.adapters.applyin import ApplyinAdapter
    from crawler.adapters.careerlink import CareerlinkAdapter
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.incruit import IncruitAdapter

    # SaaS 어댑터 상속 검증
    for cls in (IncruitAdapter, CareerlinkAdapter, ApplyinAdapter):
        assert issubclass(cls, BaseCustomAdapter), (
            f"{cls.__name__} must subclass BaseCustomAdapter"
        )

    # incruit
    client = _make_mock_client(_INCRUIT_FIXTURE)
    adapter = IncruitAdapter(company="ibk", slug="ibk", client=client)
    jobs = adapter.fetch_jobs(location="KR")
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert "job_id" in job
        assert "company" in job
        assert job["company"] == "ibk"
        assert "title" in job
        assert "url" in job
        assert "raw_text" in job

    # careerlink
    client2 = _make_mock_client(_CAREERLINK_FIXTURE)
    adapter2 = CareerlinkAdapter(company="woori-bank", slug="woori", client=client2)
    jobs2 = adapter2.fetch_jobs(location="KR")
    assert isinstance(jobs2, list)
    assert len(jobs2) >= 1
    for job in jobs2:
        assert "job_id" in job
        assert job["company"] == "woori-bank"

    # applyin
    client3 = _make_mock_client(_APPLYIN_FIXTURE)
    adapter3 = ApplyinAdapter(company="koscom", slug="koscom", client=client3)
    jobs3 = adapter3.fetch_jobs(location="KR")
    assert isinstance(jobs3, list)
    assert len(jobs3) >= 1
    for job in jobs3:
        assert "job_id" in job
        assert job["company"] == "koscom"


def test_AC_1_finance_custom_adapters_collected():
    """AC-1: custom 인터넷은행·증권 어댑터가 BaseCustomAdapter를 상속하고 RawJob list를 반환."""
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.finance_kakaobank import KakaoBankAdapter
    from crawler.adapters.finance_nh_nonghyup import NHNonghyupAdapter
    from crawler.adapters.finance_samsung_fire import SamsungFireAdapter
    from crawler.adapters.finance_tossbank import TossBankAdapter

    for cls in (
        KakaoBankAdapter,
        TossBankAdapter,
        NHNonghyupAdapter,
        SamsungFireAdapter,
    ):
        assert issubclass(cls, BaseCustomAdapter), (
            f"{cls.__name__} must subclass BaseCustomAdapter"
        )

    for cls in (
        KakaoBankAdapter,
        TossBankAdapter,
        NHNonghyupAdapter,
        SamsungFireAdapter,
    ):
        client = _make_mock_client(_FINANCE_CUSTOM_FIXTURE)
        adapter = cls(client=client)
        jobs = adapter.fetch_jobs(location="KR")
        assert isinstance(jobs, list), f"{cls.__name__}: fetch_jobs must return list"
        assert len(jobs) >= 1, f"{cls.__name__}: should return at least 1 job"
        for job in jobs:
            assert "job_id" in job
            assert "company" in job
            assert "title" in job
            assert "url" in job
            assert "raw_text" in job


def test_AC_1_tier5_registry_mapping():
    """AC-1: registry_seed Tier5 custom-ready 소스가 어댑터와 매핑된다."""
    from crawler.sources.registry_seed import SOURCE_SPECS

    tier5_sources = [s for s in SOURCE_SPECS if s.tier == 5]
    # incruit 3사 + careerlink 2사 + applyin 1사 + custom 7사 = 13사 custom-ready + greeting 1
    tier5_custom_ready = [s for s in tier5_sources if s.status == "custom-ready"]
    assert len(tier5_custom_ready) >= 10, (
        f"Expected >=10 Tier5 custom-ready sources, got {len(tier5_custom_ready)}"
    )

    # incruit 소스 확인
    tier5_incruit = [s for s in tier5_sources if s.method == "incruit"]
    assert len(tier5_incruit) >= 3, (
        f"Expected >=3 Tier5 incruit sources, got {len(tier5_incruit)}"
    )

    # careerlink 소스 확인
    tier5_careerlink = [s for s in tier5_sources if s.method == "careerlink"]
    assert len(tier5_careerlink) >= 2, (
        f"Expected >=2 Tier5 careerlink sources, got {len(tier5_careerlink)}"
    )


# ---------------------------------------------------------------------------
# AC-2: 위탁SaaS 어댑터 1개로 여러 회사 곱셈 수집 (최소 신규 어댑터)
# ---------------------------------------------------------------------------


def test_AC_2_saas_adapter_multiplexes_companies():
    """AC-2: 같은 SaaS 어댑터 인스턴스(slug만 변경)가 여러 회사를 수집한다."""
    from crawler.adapters.incruit import IncruitAdapter

    # incruit 어댑터 — KB국민은행·IBK·신한카드 3사 재사용
    companies = [
        ("kb-bank", "kbstar"),
        ("ibk", "ibk"),
        ("shinhan-card", "shinhancard"),
    ]
    for company, slug in companies:
        client = _make_mock_client(_INCRUIT_FIXTURE)
        adapter = IncruitAdapter(company=company, slug=slug, client=client)
        jobs = adapter.fetch_jobs(location="KR")
        assert isinstance(jobs, list), f"{company}: must return list"
        assert len(jobs) >= 1, f"{company}: should return at least 1 job"
        for job in jobs:
            assert job["company"] == company, (
                f"Expected company={company}, got {job['company']}"
            )


def test_AC_2_careerlink_adapter_multiplexes_companies():
    """AC-2: careerlink 어댑터가 우리은행·우리에프아이에스 2사를 1어댑터로 수집."""
    from crawler.adapters.careerlink import CareerlinkAdapter

    companies = [
        ("woori-bank", "woori"),
        ("woori-fis", "woorifis"),
    ]
    for company, slug in companies:
        client = _make_mock_client(_CAREERLINK_FIXTURE)
        adapter = CareerlinkAdapter(company=company, slug=slug, client=client)
        jobs = adapter.fetch_jobs(location="KR")
        assert isinstance(jobs, list), f"{company}: must return list"
        assert len(jobs) >= 1
        for job in jobs:
            assert job["company"] == company


def test_AC_2_tier5_registry_saas_count():
    """AC-2: registry_seed Tier5 SaaS 소스가 recruiter_co_kr·incruit·careerlink·applyin을 포함한다."""
    from crawler.sources.registry_seed import SOURCE_SPECS

    tier5 = [s for s in SOURCE_SPECS if s.tier == 5]
    saas_methods = {"recruiter_co_kr", "incruit", "careerlink", "applyin"}
    tier5_saas = [s for s in tier5 if s.method in saas_methods]

    # recruiter_co_kr 5사 + incruit 3사 + careerlink 2사 + applyin 1사 = 11사
    assert len(tier5_saas) >= 8, (
        f"Expected >=8 Tier5 SaaS sources, got {len(tier5_saas)}"
    )

    # 각 SaaS 메서드가 최소 1개 이상 존재
    for method in ("incruit", "careerlink", "applyin"):
        count = sum(1 for s in tier5_saas if s.method == method)
        assert count >= 1, f"Expected >=1 Tier5 source with method={method}"


# ---------------------------------------------------------------------------
# AC-3: list-login 소스 → 크롤링 시도 없이 status=login-required 기록
# ---------------------------------------------------------------------------


def test_AC_3_login_required_cataloged_not_crawled():
    """AC-3: view_login=True 소스는 크롤링 시도 없이 login-required로 기록된다."""
    from crawler.sources.registry_seed import SOURCE_SPECS

    login_required_sources = [s for s in SOURCE_SPECS if s.status == "login-required"]
    view_login_true_sources = [s for s in SOURCE_SPECS if s.view_login]

    # login-required status인 소스는 view_login=True여야 한다
    for s in login_required_sources:
        assert s.view_login is True, (
            f"{s.company}: status=login-required but view_login=False"
        )
    # 역방향: view_login=True 소스는 status=login-required여야 한다
    for s in view_login_true_sources:
        assert s.status == "login-required", (
            f"{s.company}: view_login=True but status={s.status}"
        )


def test_AC_3_login_required_handler_finance():
    """AC-3: LoginRequiredSource는 fetch_jobs() 빈 list + status=login-required."""
    from crawler.adapters.conglomerate_login_required import LoginRequiredSource

    # Tier5 금융권 목록 로그인 소스 예시
    source = LoginRequiredSource(company="finance-login-test")
    jobs = source.fetch_jobs(location="KR")
    assert jobs == [], "login-required 소스는 공고를 수집하면 안 된다"

    status = source.get_status()
    assert status == "login-required", f"Expected 'login-required', got {status!r}"


def test_AC_3_tier5_no_login_required_in_registry():
    """AC-3: Tier5 registry_seed에 list-login 소스가 있다면 status=login-required로 기록된다."""
    from crawler.sources.registry_seed import SOURCE_SPECS

    tier5 = [s for s in SOURCE_SPECS if s.tier == 5]

    # view_login=True인 Tier5 소스는 status=login-required여야 한다
    for s in tier5:
        if s.view_login:
            assert s.status == "login-required", (
                f"Tier5 {s.company}: view_login=True but status={s.status}"
            )

    # coverage panel: Tier5 전체가 기록됨 (status=custom-ready or ats-ready or login-required 등)
    for s in tier5:
        assert s.status != "", f"Tier5 {s.company}: status must not be empty"
