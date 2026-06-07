"""T-072 Tier1 custom 어댑터 테스트 — AC-1, AC-2, AC-3.

어댑터: NaverAdapter·KakaoAdapter·LineAdapter·WoowaAdapter + BaseCustomAdapter.
fixture 기반 오프라인 테스트 — 실 네트워크 불필요.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_mock_client(fixture_path: Path, status_code: int = 200) -> MagicMock:
    """fixture JSON 또는 HTML을 반환하는 mock httpx client 생성."""
    data = fixture_path.read_text(encoding="utf-8")
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if fixture_path.suffix == ".json":
        mock_resp.json.return_value = json.loads(data)
    else:
        mock_resp.text = data
    mock_resp.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    return mock_client


# ---------------------------------------------------------------------------
# AC-1: Tier1 custom 어댑터 fetch_jobs() → RawJob list + BaseCustomAdapter 재사용
# ---------------------------------------------------------------------------


def test_AC_1_tier1_custom_fetch_naver():
    """AC-1 (naver): NaverAdapter fixture → RawJob list + BaseCustomAdapter 상속 + 한국 공고."""
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.naver import NaverAdapter

    client = _make_mock_client(FIXTURES_DIR / "custom_naver.json")
    adapter = NaverAdapter(client=client)

    assert issubclass(NaverAdapter, BaseCustomAdapter)

    jobs = adapter.fetch_jobs(location="KR")

    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, dict)
        assert "job_id" in job
        assert "company" in job
        assert "title" in job
        assert "url" in job
        assert "raw_text" in job
        assert job["company"] == "naver"


def test_AC_1_tier1_custom_fetch_kakao():
    """AC-1 (kakao): KakaoAdapter fixture → RawJob list + BaseCustomAdapter 상속."""
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.kakao import KakaoAdapter

    client = _make_mock_client(FIXTURES_DIR / "custom_kakao.json")
    adapter = KakaoAdapter(client=client)

    assert issubclass(KakaoAdapter, BaseCustomAdapter)

    jobs = adapter.fetch_jobs(location="KR")

    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, dict)
        assert "job_id" in job
        assert "company" in job
        assert "title" in job
        assert "url" in job
        assert "raw_text" in job


def test_AC_1_tier1_custom_fetch_line():
    """AC-1 (line): LineAdapter fixture → RawJob list + 한국 공고 필터."""
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.line import LineAdapter

    client = _make_mock_client(FIXTURES_DIR / "custom_line.json")
    adapter = LineAdapter(client=client)

    assert issubclass(LineAdapter, BaseCustomAdapter)

    jobs = adapter.fetch_jobs(location="KR")

    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, dict)
        assert "job_id" in job
        assert "title" in job
        assert "url" in job


def test_AC_1_tier1_custom_fetch_woowa():
    """AC-1 (woowa): WoowaAdapter fixture → RawJob list."""
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.woowa import WoowaAdapter

    client = _make_mock_client(FIXTURES_DIR / "custom_woowa.json")
    adapter = WoowaAdapter(client=client)

    assert issubclass(WoowaAdapter, BaseCustomAdapter)

    jobs = adapter.fetch_jobs(location="KR")

    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, dict)
        assert "job_id" in job
        assert "title" in job
        assert "url" in job


# ---------------------------------------------------------------------------
# AC-2: 계열사 config 재사용 — 네이버 계열사(동일 포털 패턴)
# ---------------------------------------------------------------------------


def test_AC_2_affiliate_config_reuse():
    """AC-2: 네이버 계열사(SNOW)가 NaverAdapter 동일 골격으로 수집된다(config 재사용)."""
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.naver import NaverAdapter

    # 계열사는 company 파라미터만 바꿔 동일 NaverAdapter 사용
    client = _make_mock_client(FIXTURES_DIR / "custom_naver.json")
    adapter = NaverAdapter(company="snow", client=client)

    assert issubclass(NaverAdapter, BaseCustomAdapter)

    jobs = adapter.fetch_jobs(location="KR")

    assert isinstance(jobs, list)
    # 계열사 company 이름 적용 확인
    for job in jobs:
        assert job["company"] == "snow"


def test_AC_2_kakao_games_config_reuse():
    """AC-2: 카카오게임즈가 KakaoAdapter 동일 골격으로 수집된다(company config만 변경)."""
    from crawler.adapters.custom_base import BaseCustomAdapter
    from crawler.adapters.kakao import KakaoAdapter

    client = _make_mock_client(FIXTURES_DIR / "custom_kakao.json")
    adapter = KakaoAdapter(
        company="kakaogames",
        base_url="https://recruit.kakaogames.com/api/jobs",
        client=client,
    )

    assert issubclass(KakaoAdapter, BaseCustomAdapter)

    jobs = adapter.fetch_jobs(location="KR")

    assert isinstance(jobs, list)
    for job in jobs:
        assert job["company"] == "kakaogames"


# ---------------------------------------------------------------------------
# AC-3: 구조변경/차단 fixture → GateResult(ok=False) + status 명시
# ---------------------------------------------------------------------------


def test_AC_3_gate_failure_status_blocked():
    """AC-3 (403 차단): NaverAdapter gate_check → GateResult(ok=False) + blocked reason."""
    from crawler.adapters.base import GateResult
    from crawler.adapters.naver import NaverAdapter

    # 403 응답 mock
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    adapter = NaverAdapter(client=mock_client)
    result = adapter.gate_check()

    assert isinstance(result, GateResult)
    assert result.ok is False
    assert "403" in result.reason or "block" in result.reason.lower()


def test_AC_3_gate_failure_status_structure_change():
    """AC-3 (parse 실패율 ≥30%): 구조변경 fixture → GateResult(ok=False) + 이유 명시."""
    from crawler.adapters.base import GateResult
    from crawler.adapters.naver import NaverAdapter

    # 필수 필드 없는 broken fixture — parse 실패율 ≥30%
    broken_data = {
        "result": [
            {"broken_field": "no id no title"},  # 필수 필드 없음
            {"broken_field": "no id no title"},
            {"broken_field": "no id no title"},
            {"id": "ok1", "title": "Backend Engineer", "url": "https://..."},
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = broken_data
    mock_resp.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    adapter = NaverAdapter(client=mock_client)
    result = adapter.gate_check()

    assert isinstance(result, GateResult)
    assert result.ok is False
    assert "parse failure" in result.reason.lower() or "%" in result.reason


def test_AC_3_gate_ok_when_valid():
    """AC-3 (정상 구조): 정상 fixture → GateResult(ok=True)."""
    from crawler.adapters.base import GateResult
    from crawler.adapters.naver import NaverAdapter

    valid_data = {
        "result": [
            {
                "id": "1",
                "title": "Backend Engineer",
                "url": "https://recruit.navercorp.com/1",
            },
            {
                "id": "2",
                "title": "Frontend Engineer",
                "url": "https://recruit.navercorp.com/2",
            },
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = valid_data
    mock_resp.raise_for_status.return_value = None
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    adapter = NaverAdapter(client=mock_client)
    result = adapter.gate_check()

    assert isinstance(result, GateResult)
    assert result.ok is True
