"""T-062 소스 레지스트리 — 회사↔어댑터↔ATS 매핑 + 애그리게이터 차단 가드.

레지스트리는 *메커니즘*만 둔다(등록·상태·활성 조회). 전 target 목록 seed는 T-070
discovery가, 전체 등록·상태·커버리지 패널은 T-063이 채운다.

Charter §5: 수집은 각 회사 공식 채용 페이지에서만. 애그리게이터(잡코리아·사람인·원티드
등) 도메인은 영구 비범위라 등록 시 ValueError로 차단한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 애그리게이터 도메인(영구 비범위) — 등록 시 차단. 위탁 ATS(recruiter.co.kr 등)는
# 회사 공식 채용을 호스팅하므로 포함하지 않는다.
BANNED_DOMAINS: frozenset[str] = frozenset(
    {
        "jobkorea.co.kr",
        "saramin.co.kr",
        "wanted.co.kr",
        "jumpit.co.kr",
        "rocketpunch.com",
        "indeed.com",
        "jobplanet.co.kr",
    }
)

# get_active_sources가 "수집 중"으로 간주하는 status
_ACTIVE_STATUS = "수집 중"


@dataclass
class SourceEntry:
    """소스 1건: 회사 ↔ 어댑터 클래스 ↔ 티어 ↔ status.

    adapter_kwargs는 adapter_cls(**adapter_kwargs)로 어댑터를 인스턴스화할 인자.
    status: "discovered" / "수집 중" / "수집 실패" / "login-required" 등(T-063 확장).
    """

    company: str
    adapter_cls: type
    tier: str
    status: str = "discovered"
    adapter_kwargs: dict[str, Any] = field(default_factory=dict)


class SourceRegistry:
    """소스 등록·조회. 인스턴스는 빈 상태로 시작(seed는 build_default_registry)."""

    def __init__(self) -> None:
        self._entries: list[SourceEntry] = []

    def register(self, entry: SourceEntry) -> None:
        """소스를 등록한다. 애그리게이터 도메인이면 ValueError로 거부."""
        self._guard_aggregator(entry)
        self._entries.append(entry)

    def get_active_sources(self) -> list[SourceEntry]:
        """status가 "수집 중"인 소스만 반환한다."""
        return [e for e in self._entries if e.status == _ACTIVE_STATUS]

    def all_sources(self) -> list[SourceEntry]:
        """등록된 전체 소스(상태 무관) — 커버리지 패널 투명 노출용(T-063)."""
        return list(self._entries)

    @staticmethod
    def _guard_aggregator(entry: SourceEntry) -> None:
        haystack = " ".join(
            [entry.company, *(str(v) for v in entry.adapter_kwargs.values())]
        ).lower()
        for domain in BANNED_DOMAINS:
            if domain in haystack:
                raise ValueError(
                    f"aggregator domain banned: {domain} "
                    "(Charter §5 — 각 회사 공식 채용 페이지만 수집)"
                )


def build_default_registry() -> SourceRegistry:
    """T-062 초기 seed: toss(custom) · daangn(Greenhouse) · greenhouse 회사 ≥1.

    전체 target 목록은 T-070 discovery가 채운다 — 여기서는 패턴 확립용 최소 seed만.
    """
    from crawler.adapters.greenhouse import GreenhouseAdapter
    from crawler.adapters.toss import TossAdapter

    registry = SourceRegistry()
    registry.register(
        SourceEntry(
            company="toss",
            adapter_cls=TossAdapter,
            tier="스타트업",
            status=_ACTIVE_STATUS,
        )
    )
    registry.register(
        SourceEntry(
            company="daangn",
            adapter_cls=GreenhouseAdapter,
            tier="스타트업",
            status=_ACTIVE_STATUS,
            adapter_kwargs={"company_slug": "daangn"},
        )
    )
    registry.register(
        SourceEntry(
            company="moloco",
            adapter_cls=GreenhouseAdapter,
            tier="외국계",
            status=_ACTIVE_STATUS,
            adapter_kwargs={"company_slug": "moloco"},
        )
    )
    return registry
