"""T-063 소스 레지스트리 실행 — registry_seed 소스 순회 수집 + 상태 기록.

각 소스: gate_check → pass 시 fetch_jobs → job_postings upsert → source_crawl_status
active 갱신. gate 실패/미수집은 taxonomy status(blocked/captcha/unsupported) +
last_error 기록. 부분 실패는 격리한다(한 소스 실패가 전체 수집을 중단시키지 않음).

crawler 단일 writer(ARCH §3-2): job_postings·source_crawl_status에만 write. DDL=Prisma,
DML=여기. 시간은 호출자 주입 가능(결정성 — Date.now 직접 X).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from crawler.adapters.base import BaseCrawlerAdapter
from crawler.persistence import upsert_jobs
from crawler.sources.registry_seed import (
    SOURCE_SPECS,
    SourceSpec,
    method_family,
)

logger = logging.getLogger(__name__)

# active 승격 후보 status(수집 시도 대상)
_COLLECTABLE = frozenset({"ats-ready", "custom-ready"})


def _gate_status(reason: str) -> str:
    """gate 실패 reason → source_crawl_status taxonomy."""
    low = reason.lower()
    if "captcha" in low:
        return "captcha"
    if "parse failure" in low or "structure" in low:
        return "unsupported"
    return "blocked"  # 403/429/기타 차단


@contextmanager
def _get_connection() -> Iterator[Any]:
    """crawler DB 연결 컨텍스트(테스트는 patch). 정상 종료 시 commit."""
    from core import db

    conn = db.connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def record_source_crawl_status(
    conn: Any,
    source_id: str,
    *,
    status: str,
    last_success_at: datetime | None = None,
    last_error: str | None = None,
    tier: str = "",
    method: str = "",
) -> None:
    """source_crawl_status 멱등 upsert(crawler 단일 writer, §3-2).

    last_success_at은 성공 시에만 갱신(실패가 직전 성공 시각을 지우지 않게 COALESCE).
    """
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO source_crawl_status "
            "(source_id, tier, method, status, last_success_at, last_error) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (source_id) DO UPDATE SET "
            "tier = EXCLUDED.tier, method = EXCLUDED.method, "
            "status = EXCLUDED.status, "
            "last_success_at = COALESCE("
            "EXCLUDED.last_success_at, source_crawl_status.last_success_at), "
            "last_error = EXCLUDED.last_error",
            (source_id, tier, method, status, last_success_at, last_error),
        )


# ---------------------------------------------------------------------------
# 어댑터 빌드 — method 패밀리별 디스패치(테스트는 patch)
# ---------------------------------------------------------------------------


def _build_ats_adapter(spec: SourceSpec) -> BaseCrawlerAdapter | None:
    """표준 ATS method → slug 기반 어댑터."""
    slug = spec.ats_slug or spec.company
    if spec.method == "greenhouse":
        from crawler.adapters.greenhouse import GreenhouseAdapter

        return GreenhouseAdapter(company_slug=slug)
    if spec.method == "lever":
        from crawler.adapters.lever import LeverAdapter

        return LeverAdapter(company_slug=slug)
    if spec.method == "ashby":
        from crawler.adapters.ashby import AshbyAdapter

        return AshbyAdapter(company_slug=slug)
    if spec.method == "workday":
        from crawler.adapters.workday import WorkdayAdapter

        return WorkdayAdapter(tenant=slug)
    if spec.method == "greeting":
        from crawler.adapters.greeting import GreetingAdapter

        return GreetingAdapter(company=slug)
    return None


def _build_saas_adapter(spec: SourceSpec) -> BaseCrawlerAdapter | None:
    """한국 위탁 SaaS method → company+slug 기반 어댑터(곱셈 공유)."""
    slug = spec.ats_slug or spec.company
    if spec.method == "recruiter_co_kr":
        from crawler.adapters.recruiter_co_kr import RecruiterCoKrAdapter

        return RecruiterCoKrAdapter(company=spec.company, slug=slug)
    if spec.method == "incruit":
        from crawler.adapters.incruit import IncruitAdapter

        return IncruitAdapter(company=spec.company, slug=slug)
    if spec.method == "careerlink":
        from crawler.adapters.careerlink import CareerlinkAdapter

        return CareerlinkAdapter(company=spec.company, slug=slug)
    if spec.method == "applyin":
        from crawler.adapters.applyin import ApplyinAdapter

        return ApplyinAdapter(company=spec.company, slug=slug)
    return None


def _build_adapter(spec: SourceSpec) -> BaseCrawlerAdapter | None:
    """SourceSpec → 어댑터 인스턴스. ats/saas는 slug 디스패치, custom은 회사별 클래스.

    미구현 custom·candidate는 None 반환(호출자가 unsupported로 기록 — 조용한 누락 0).
    """
    fam = method_family(spec.method)
    if fam == "ats":
        return _build_ats_adapter(spec)
    if fam == "saas":
        return _build_saas_adapter(spec)
    return _build_custom_adapter(spec)


def _build_custom_adapter(spec: SourceSpec) -> BaseCrawlerAdapter | None:
    """custom 자체사이트 → 회사별 어댑터(구현분만; 미구현은 None)."""
    factory = _CUSTOM_FACTORIES.get(spec.company)
    return factory() if factory is not None else None


def _custom_factories() -> dict[str, Any]:
    """company → 어댑터 팩토리. 구현된 custom 어댑터만 등록(점진 확장)."""
    from crawler.adapters import (
        conglomerate_doosan,
        conglomerate_hanwha,
        conglomerate_hyundai,
        conglomerate_kt,
        conglomerate_lg,
        conglomerate_samsung,
        conglomerate_sk,
        finance_kakaobank,
        finance_nh_nonghyup,
        finance_samsung_fire,
        finance_tossbank,
        foreign_amazon,
        foreign_apple,
        foreign_google,
        foreign_meta,
        foreign_microsoft,
        foreign_uber,
        kakao,
        line,
        naver,
        startup_bithumb,
        startup_bucketplace,
        startup_class101,
        startup_dunamu,
        startup_megazone,
        startup_socar,
        startup_tridge,
        startup_zigbang,
        toss,
        woowa,
    )

    return {
        # Tier1 본사 + 네이버 계열(동일 포털 config 재사용)
        "naver": naver.NaverAdapter,
        "snow": lambda: naver.NaverAdapter(company="snow"),
        "naver-cloud": lambda: naver.NaverAdapter(company="naver-cloud"),
        "naver-financial": lambda: naver.NaverAdapter(company="naver-financial"),
        "works-mobile": lambda: naver.NaverAdapter(company="works-mobile"),
        "kakao": kakao.KakaoAdapter,
        "kakao-games": lambda: kakao.KakaoAdapter(
            company="kakao-games", base_url="https://recruit.kakaogames.com/api/jobs"
        ),
        "line-plus": lambda: line.LineAdapter(company="line-plus"),
        "woowahan": woowa.WoowaAdapter,
        "toss": toss.TossAdapter,
        # Tier2 글로벌 custom
        "google": foreign_google.GoogleAdapter,
        "microsoft": foreign_microsoft.MicrosoftAdapter,
        "amazon": foreign_amazon.AmazonAdapter,
        "meta": foreign_meta.MetaAdapter,
        "apple": foreign_apple.AppleAdapter,
        "uber": foreign_uber.UberAdapter,
        # Tier3 스타트업 custom
        "dunamu": startup_dunamu.DunamuAdapter,
        "zigbang": startup_zigbang.ZigbangAdapter,
        "bucketplace": startup_bucketplace.BucketplaceAdapter,
        "socar": startup_socar.SocarAdapter,
        "bithumb": startup_bithumb.BithumbAdapter,
        "tridge": startup_tridge.TridgeAdapter,
        "megazone": startup_megazone.MegazoneAdapter,
        "class101": startup_class101.Class101Adapter,
        # Tier4 대기업 (그룹 통합포털 + 계열사 필터)
        "samsung-electronics": conglomerate_samsung.SamsungAdapter,
        "samsung-sds": lambda: conglomerate_samsung.SamsungAdapter(
            company="samsung-sds"
        ),
        "samsung-electro-mechanics": lambda: conglomerate_samsung.SamsungAdapter(
            company="samsung-electro-mechanics"
        ),
        "lg-electronics": conglomerate_lg.LGAdapter,
        "lg-cns": lambda: conglomerate_lg.LGAdapter(company="lg-cns"),
        "lg-uplus": lambda: conglomerate_lg.LGAdapter(company="lg-uplus"),
        "sk-cc-ax": conglomerate_sk.SKAdapter,
        "doosan": conglomerate_doosan.DoosanAdapter,
        "hanwha-systems": conglomerate_hanwha.HanwhaAdapter,
        "hyundai-motor": conglomerate_hyundai.HyundaiAdapter,
        "kt": conglomerate_kt.KTAdapter,
        # Tier5 금융 custom
        "kakaobank": finance_kakaobank.KakaoBankAdapter,
        "tossbank": finance_tossbank.TossBankAdapter,
        "nh-nonghyup": finance_nh_nonghyup.NHNonghyupAdapter,
        "samsung-fire": finance_samsung_fire.SamsungFireAdapter,
    }


_CUSTOM_FACTORIES: dict[str, Any] = _custom_factories()


# ---------------------------------------------------------------------------
# 실행 오케스트레이션
# ---------------------------------------------------------------------------


def _resolve_specs(sources: list[str] | None) -> list[SourceSpec]:
    """수집 대상 SourceSpec 목록. sources 미지정 시 collectable 전 소스."""
    by_company = {s.company: s for s in SOURCE_SPECS}
    if sources is None:
        return [s for s in SOURCE_SPECS if s.status in _COLLECTABLE]
    specs: list[SourceSpec] = []
    for name in sources:
        spec = by_company.get(name)
        if spec is None:
            # registry_seed에 없는 임의 소스(테스트/임시) — 최소 spec 합성
            spec = SourceSpec(
                company=name,
                tier=0,
                careers_url="",
                method="custom",
                status="custom-ready",
                view_login=False,
                location_filter="",
            )
        specs.append(spec)
    return specs


def run_all_sources(
    sources: list[str] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """registry_seed 소스를 순회 수집한다(부분 실패 격리).

    각 소스: gate_check → ok면 fetch_jobs + upsert + status=active, 실패면 blocked/
    captcha/unsupported + last_error. 어댑터 미구현(custom None)도 unsupported로 기록.
    반환: {"collected": 성공 수, "failed": 실패 수}.
    """
    run_at = now or datetime.now(timezone.utc)
    specs = _resolve_specs(sources)
    collected = 0
    failed = 0
    # 사유별 집계 — 관측성(Fail #3). 게이트 실패·미구현도 로그에 남김.
    by_status: dict[str, int] = {}

    def _bump(status: str) -> None:
        by_status[status] = by_status.get(status, 0) + 1

    with _get_connection() as conn:
        for spec in specs:
            adapter = _build_adapter(spec)
            tier = str(spec.tier)
            if adapter is None:
                record_source_crawl_status(
                    conn,
                    spec.company,
                    status="unsupported",
                    last_error="adapter not wired",
                    tier=tier,
                    method=spec.method,
                )
                logger.warning(
                    "source_skip company=%s reason=adapter-not-wired", spec.company
                )
                _bump("no-adapter")
                failed += 1
                continue
            try:
                gate = adapter.gate_check()
                if not gate.ok:
                    gate_st = _gate_status(gate.reason)
                    record_source_crawl_status(
                        conn,
                        spec.company,
                        status=gate_st,
                        last_error=gate.reason,
                        tier=tier,
                        method=spec.method,
                    )
                    logger.warning(
                        "source_gate_fail company=%s status=%s reason=%s",
                        spec.company,
                        gate_st,
                        gate.reason,
                    )
                    _bump(gate_st)
                    failed += 1
                    continue
                jobs = adapter.fetch_jobs(location=spec.location_filter or "KR")
                upsert_jobs(conn, spec.company, jobs, now=run_at)
                record_source_crawl_status(
                    conn,
                    spec.company,
                    status="active",
                    last_success_at=run_at,
                    last_error=None,
                    tier=tier,
                    method=spec.method,
                )
                _bump("active")
                collected += 1
            except Exception as exc:  # 시스템 경계 — 소스 실패 격리(전체 중단 X)
                logger.error("source_failed company=%s error=%s", spec.company, exc)
                record_source_crawl_status(
                    conn,
                    spec.company,
                    status="blocked",
                    last_error=str(exc),
                    tier=tier,
                    method=spec.method,
                )
                _bump("fetch-error")
                failed += 1

    # 전체 사유 분포 한 줄 — warning이라 CloudWatch 노출(로그만으로 분류 가능).
    logger.warning(
        "crawl_status_breakdown collected=%s failed=%s by_status=%s",
        collected,
        failed,
        by_status,
    )
    return {"collected": collected, "failed": failed}
