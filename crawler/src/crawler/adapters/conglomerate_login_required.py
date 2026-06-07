"""T-075 login-required 소스 처리 — 크롤링 시도 없이 status 기록.

목록 view가 로그인 게이트인 소스는 수집 시도 없이 status=login-required로 투명 노출.
거짓 완전성 0 — 미수집을 정직하게 표시한다(공개수집 정책·ToS).
"""

from __future__ import annotations

from crawler.adapters.base import BaseCrawlerAdapter, GateResult, RawJob


class LoginRequiredSource(BaseCrawlerAdapter):
    """목록 로그인 소스 — 수집 금지, status=login-required 반환.

    크롤링을 시도하지 않고 패널에 투명 노출만 한다.
    로그인 크롤링은 영구 비범위(공개수집 정책).
    """

    def __init__(self, company: str) -> None:
        self.company = company

    def fetch_jobs(self, location: str = "KR") -> list[RawJob]:
        """수집 시도 없이 빈 list 반환."""
        return []

    def get_status(self) -> str:
        """coverage 패널 노출용 status."""
        return "login-required"

    def gate_check(self) -> GateResult:
        """login-required 소스는 항상 ok=False — 커버리지 패널 투명 노출."""
        return GateResult(ok=False, reason="login-required: 목록 view 로그인 필요")
