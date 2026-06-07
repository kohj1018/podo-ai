"""T-062 게이트 검사 테스트 — AC-2."""

from __future__ import annotations

from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# AC-2: run_gate_check() — 차단/실패율 감지 → GateResult(ok=False)
# ---------------------------------------------------------------------------


def test_AC_2_gate_check_blocked_response():
    """AC-2: HTTP 403 응답 시 GateResult(ok=False, reason=...) 반환."""
    from crawler.adapters.base import GateResult
    from crawler.gate import run_gate_check

    mock_adapter = MagicMock()
    mock_adapter.gate_check.return_value = GateResult(
        ok=False, reason="HTTP 403 Forbidden"
    )

    result = run_gate_check(mock_adapter)

    assert isinstance(result, GateResult)
    assert result.ok is False
    assert "403" in result.reason


def test_AC_2_gate_check_high_parse_failure_rate():
    """AC-2: 필수 필드 parse 실패율 ≥30% 시 GateResult(ok=False) 반환."""
    from crawler.adapters.base import GateResult
    from crawler.gate import run_gate_check

    mock_adapter = MagicMock()
    mock_adapter.gate_check.return_value = GateResult(
        ok=False, reason="parse failure rate 40.0% >= 30%"
    )

    result = run_gate_check(mock_adapter)

    assert result.ok is False
    assert "30%" in result.reason or "parse" in result.reason.lower()


def test_AC_2_gate_check_pass():
    """AC-2: 정상 응답 시 GateResult(ok=True) 반환."""
    from crawler.adapters.base import GateResult
    from crawler.gate import run_gate_check

    mock_adapter = MagicMock()
    mock_adapter.gate_check.return_value = GateResult(ok=True, reason="ok")

    result = run_gate_check(mock_adapter)

    assert result.ok is True


def test_AC_2_greenhouse_adapter_gate_check_403():
    """AC-2: GreenhouseAdapter.gate_check() — HTTP 403 → GateResult(ok=False)."""
    import httpx

    from crawler.adapters.greenhouse import GreenhouseAdapter

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "403 Forbidden", request=MagicMock(), response=mock_resp
    )

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    adapter = GreenhouseAdapter(company_slug="test-company", client=mock_client)
    result = adapter.gate_check()

    assert result.ok is False
    assert "403" in result.reason or "block" in result.reason.lower() or result.reason


def test_AC_2_greenhouse_adapter_gate_check_high_failure():
    """AC-2: GreenhouseAdapter.gate_check() — parse 실패율 ≥30% → GateResult(ok=False)."""
    from crawler.adapters.greenhouse import GreenhouseAdapter

    # 필수 필드(id/title/absolute_url) 중 일부 누락된 공고가 30% 이상
    bad_fixture = {
        "jobs": [
            # 정상
            {
                "id": 1,
                "title": "Engineer",
                "absolute_url": "https://example.com/1",
                "content": "",
            },
            # 필수 필드 누락 (id 없음)
            {
                "title": "No ID Job",
                "absolute_url": "https://example.com/2",
                "content": "",
            },
            # 필수 필드 누락 (title 없음)
            {"id": 3, "absolute_url": "https://example.com/3", "content": ""},
            # 필수 필드 누락 (url 없음)
            {"id": 4, "title": "No URL", "content": ""},
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = bad_fixture

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    adapter = GreenhouseAdapter(company_slug="test-company", client=mock_client)
    result = adapter.gate_check()

    assert result.ok is False
    assert "parse" in result.reason.lower() or "30" in result.reason
