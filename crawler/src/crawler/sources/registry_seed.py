"""T-070 소스 discovery → registry seed (master data, SSOT — 커밋·오프라인 재현).

M5 커버리지 확대의 선행 discovery. Target universe **Tier1~5(~85개사)** 각 회사의
공식 채용 URL · 수집 method(표준 ATS / 한국 위탁 SaaS / custom) · 한국 location 필터 ·
view-vs-apply 로그인 · status 를 `SourceSpec` 으로 확정한다. T-071(ATS)·T-072(custom)·
T-073~076(tier)·T-063(레지스트리·패널)이 이 seed 를 read-only 로 소비한다.

데이터 출처: M5 planning-phase 웹검색 실측(milestone §7, 2026-06-08) + 본 라운드
spot-verification(greetinghr=KR 1위 ATS·컬리 사용 확인 / NVIDIA=nvidia.wd5 Workday·
Yanolja Workday 확인 / samsungcareers.com 목록 공개·지원시 로그인 확인). **애그리게이터
영구 제외**(잡코리아·사람인·원티드 등 — registry.BANNED_DOMAINS).

view_login 판정(behavioral — web search 불가):
- 일반 패턴 = 목록 view 공개 + 지원 시 로그인 → 기본 view_login=False.
- live httpx 목록-렌더 vs 로그인-redirect 최종 확정은 실수집 게이트(T-063/M6).
- 본 seed 는 planning 실측 + Samsung spot-check 로 전 소스 list-public 판정.
  반례(목록 로그인) 발견 시 그 시점 status=login-required 로 강등.

discovery 리포트 (tier × method 분포 / status 카운트)는 모듈 하단 `discovery_summary()`
로 산출(별도 리포트 파일 불요 — §4-1).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# enum (T-063 source_crawl_status taxonomy 정합)
# ---------------------------------------------------------------------------

# method — 표준 글로벌 ATS / 한국 위탁 SaaS / custom 자체사이트
_ATS_METHODS = frozenset({"greenhouse", "lever", "ashby", "workday", "greeting"})
_SAAS_METHODS = frozenset({"recruiter_co_kr", "incruit", "careerlink", "applyin"})
METHODS: frozenset[str] = _ATS_METHODS | _SAAS_METHODS | frozenset({"custom"})

STATUSES: frozenset[str] = frozenset(
    {
        "candidate",  # 발견·미확정(method/slug TBD)
        "ats-ready",  # 표준 ATS 확정 — 공유 어댑터로 수집 가능
        "custom-ready",  # custom/위탁SaaS 확정 — 어댑터 구현 대상
        "blocked",  # robots/403/429 차단
        "captcha",  # 캡차 게이트
        "login-required",  # 목록 view 로그인 — 공개수집 정책상 미수집(투명 노출)
        "no-korea-jobs",  # 외국계인데 한국 공고/필터 불가
        "unsupported",  # JS 필수 등 현 deps(httpx+bs4)로 불가
    }
)


def method_family(method: str) -> str:
    """method → {ats, saas, custom} 패밀리 분류(어댑터 family 매핑용)."""
    if method in _ATS_METHODS:
        return "ats"
    if method in _SAAS_METHODS:
        return "saas"
    return "custom"


@dataclass(frozen=True)
class SourceSpec:
    """소스 1건 discovery 결과(master data, 불변).

    company: 고유 키 / tier: 1~5 / careers_url: 공식 채용 목록 URL /
    method: METHODS 중 / status: STATUSES 중 / view_login: 목록 view 로그인 필요? /
    location_filter: 한국 공고 필터 방법('all-kr'=국내전용, foreign=facet/쿼리 힌트) /
    ats_slug: ATS/SaaS slug·tenant / note: 비고(계열사 재사용 등).
    """

    company: str
    tier: int
    careers_url: str
    method: str
    status: str
    view_login: bool
    location_filter: str
    ats_slug: str = ""
    note: str = ""


# 국내 전용 소스 location 필터(전부 한국 — 필터 불요)
_KR = "all-kr"

# ---------------------------------------------------------------------------
# Tier1 — 네카라쿠배 + 주요 계열사 (최우선)
# ---------------------------------------------------------------------------
_TIER1: list[SourceSpec] = [
    # 자체사이트 custom (T-072) — 전부 목록 공개
    SourceSpec(
        "naver",
        1,
        "https://recruit.navercorp.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="네이버 자체포털",
    ),
    SourceSpec(
        "snow",
        1,
        "https://recruit.navercorp.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="네이버 계열 포털 config 재사용",
    ),
    SourceSpec(
        "naver-cloud",
        1,
        "https://recruit.navercorp.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="네이버 계열 포털 재사용",
    ),
    SourceSpec(
        "naver-financial",
        1,
        "https://recruit.navercorp.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="네이버 계열 포털 재사용",
    ),
    SourceSpec(
        "works-mobile",
        1,
        "https://recruit.navercorp.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="네이버 계열 포털 재사용",
    ),
    SourceSpec(
        "kakao",
        1,
        "https://careers.kakao.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="카카오 본사",
    ),
    SourceSpec(
        "kakao-games",
        1,
        "https://recruit.kakaogames.com",
        "custom",
        "custom-ready",
        False,
        _KR,
    ),
    SourceSpec(
        "kakao-enterprise",
        1,
        "https://careers.kakao.com",
        "custom",
        "candidate",
        False,
        _KR,
        note="careers/method 확정 필요(카카오 통합 가능성)",
    ),
    SourceSpec(
        "line-plus",
        1,
        "https://careers.linecorp.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="라인플러스",
    ),
    SourceSpec(
        "woowahan",
        1,
        "https://career.woowahan.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="우아한형제들/배민",
    ),
    # ATS 사용 Tier1 — 공유 어댑터 등록(custom 신규 X)
    SourceSpec(
        "coupang",
        1,
        "https://www.coupang.jobs",
        "greenhouse",
        "ats-ready",
        False,
        _KR,
        ats_slug="coupang",
        note="boards.greenhouse.io/coupang",
    ),
    SourceSpec(
        "kakao-pay",
        1,
        "https://kakaopay.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="kakaopay",
    ),
    SourceSpec(
        "kakao-entertainment",
        1,
        "https://kakaoent.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="kakaoent",
    ),
    SourceSpec(
        "kakao-mobility",
        1,
        "https://kakaomobility.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="kakaomobility",
    ),
    SourceSpec(
        "kakao-style",
        1,
        "https://kakaostyle.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="kakaostyle",
    ),
    SourceSpec(
        "naver-webtoon",
        1,
        "https://webtoonscorp.com/careers",
        "lever",
        "ats-ready",
        False,
        _KR,
        ats_slug="webtoon",
        note="lever",
    ),
]

# ---------------------------------------------------------------------------
# Tier2 — 외국계 한국 채용 (location=KR 필터 필수)
# ---------------------------------------------------------------------------
# foreign location 필터 힌트 (workday=locations·greenhouse=offices·custom=쿼리)
_F_WD = "wd:locations~Seoul,South Korea"
_F_GH = "gh:offices~Seoul/Korea"
_TIER2: list[SourceSpec] = [
    # workday (T-071)
    SourceSpec(
        "nvidia",
        2,
        "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        "workday",
        "ats-ready",
        False,
        _F_WD,
        ats_slug="nvidia.wd5",
    ),
    SourceSpec(
        "intel",
        2,
        "https://intel.wd1.myworkdayjobs.com",
        "workday",
        "ats-ready",
        False,
        _F_WD,
        ats_slug="intel.wd1",
    ),
    SourceSpec(
        "salesforce",
        2,
        "https://salesforce.wd1.myworkdayjobs.com",
        "workday",
        "ats-ready",
        False,
        _F_WD,
        ats_slug="salesforce.wd1",
    ),
    SourceSpec(
        "snowflake",
        2,
        "https://careers.snowflake.com",
        "workday",
        "candidate",
        False,
        _F_WD,
        note="workday tenant slug 확정 필요",
    ),
    # greenhouse (T-062)
    SourceSpec(
        "moloco",
        2,
        "https://job-boards.greenhouse.io/moloco",
        "greenhouse",
        "ats-ready",
        False,
        _F_GH,
        ats_slug="moloco",
    ),
    SourceSpec(
        "sendbird",
        2,
        "https://boards.greenhouse.io/sendbird",
        "greenhouse",
        "ats-ready",
        False,
        _F_GH,
        ats_slug="sendbird",
    ),
    SourceSpec(
        "databricks",
        2,
        "https://boards.greenhouse.io/databricks",
        "greenhouse",
        "ats-ready",
        False,
        _F_GH,
        ats_slug="databricks",
    ),
    # custom 글로벌 (BaseCustomAdapter + location=KR)
    SourceSpec(
        "google",
        2,
        "https://www.google.com/about/careers/applications/jobs/results",
        "custom",
        "custom-ready",
        False,
        "q-loc=Seoul, South Korea",
    ),
    SourceSpec(
        "microsoft",
        2,
        "https://careers.microsoft.com/v2/global/en/home.html",
        "custom",
        "custom-ready",
        False,
        "facet-country=Korea",
    ),
    SourceSpec(
        "amazon",
        2,
        "https://www.amazon.jobs/en/search",
        "custom",
        "custom-ready",
        False,
        "loc_query=South Korea",
        note="AWS/Amazon",
    ),
    SourceSpec(
        "meta",
        2,
        "https://www.metacareers.com/jobs",
        "custom",
        "custom-ready",
        False,
        "offices=Seoul",
    ),
    SourceSpec(
        "apple",
        2,
        "https://jobs.apple.com/en-kr/search",
        "custom",
        "custom-ready",
        False,
        "location=korea-KOR",
    ),
    SourceSpec(
        "oracle",
        2,
        "https://careers.oracle.com/jobs",
        "custom",
        "custom-ready",
        False,
        "locationsFacet=Korea",
    ),
    SourceSpec(
        "cisco",
        2,
        "https://jobs.cisco.com/jobs/SearchJobs",
        "custom",
        "custom-ready",
        False,
        "location=Korea",
    ),
    SourceSpec(
        "ibm",
        2,
        "https://www.ibm.com/careers/search",
        "custom",
        "candidate",
        False,
        "field_keyword_05=Korea",
        note="Avature 기반 — 파싱 확정 필요",
    ),
    SourceSpec(
        "uber",
        2,
        "https://www.uber.com/us/en/careers/list",
        "custom",
        "custom-ready",
        False,
        "location=KOR-Seoul",
    ),
    SourceSpec(
        "atlassian",
        2,
        "https://www.atlassian.com/company/careers/all-jobs",
        "custom",
        "candidate",
        False,
        "team/location=Korea",
        note="method TBD(Lever/Workday 가능)",
    ),
    SourceSpec(
        "linkedin",
        2,
        "https://careers.linkedin.com/jobs",
        "custom",
        "candidate",
        False,
        "location=South Korea",
        note="method TBD",
    ),
    SourceSpec(
        "sap",
        2,
        "https://jobs.sap.com",
        "custom",
        "custom-ready",
        False,
        "location=Seoul",
        note="SuccessFactors",
    ),
]

# ---------------------------------------------------------------------------
# Tier3 — Series C+·유니콘 국내 스타트업 (전부 국내)
# ---------------------------------------------------------------------------
_TIER3: list[SourceSpec] = [
    # greetinghr (T-071) — KR 1위 스타트업 ATS
    SourceSpec(
        "kurly",
        3,
        "https://kurly.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="kurly",
        note="컬리(spot-verified greeting)",
    ),
    SourceSpec(
        "ridi",
        3,
        "https://ridi.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="ridi",
    ),
    SourceSpec(
        "banksalad",
        3,
        "https://banksalad.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="banksalad",
    ),
    SourceSpec(
        "goodchoice",
        3,
        "https://gccompany.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="gccompany",
        note="여기어때/GC컴퍼니",
    ),
    SourceSpec(
        "rapportlabs",
        3,
        "https://rapportlabs.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="rapportlabs",
        note="퀸잇",
    ),
    SourceSpec(
        "healingpaper",
        3,
        "https://healingpaper.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="healingpaper",
        note="강남언니",
    ),
    SourceSpec(
        "fastfive",
        3,
        "https://fastfive.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="fastfive",
        note="Workable 병행 가능 — greeting 우선",
    ),
    # workday (T-071)
    SourceSpec(
        "yanolja",
        3,
        "https://yanolja.wd102.myworkdayjobs.com",
        "workday",
        "ats-ready",
        False,
        _KR,
        ats_slug="yanolja.wd102",
        note="spot-verified Workday",
    ),
    SourceSpec(
        "musinsa",
        3,
        "https://musinsa.wd3.myworkdayjobs.com",
        "workday",
        "ats-ready",
        False,
        _KR,
        ats_slug="musinsa.wd3",
    ),
    # custom (T-072 BaseCustomAdapter)
    SourceSpec(
        "dunamu", 3, "https://careers.dunamu.com", "custom", "custom-ready", False, _KR
    ),
    SourceSpec(
        "zigbang", 3, "https://career.zigbang.com", "custom", "custom-ready", False, _KR
    ),
    SourceSpec(
        "bucketplace",
        3,
        "https://bucketplace.com/careers",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="오늘의집",
    ),
    SourceSpec(
        "socar", 3, "https://socarcorp.kr/recruit", "custom", "custom-ready", False, _KR
    ),
    SourceSpec(
        "bithumb",
        3,
        "https://bithumb-careers.com",
        "custom",
        "custom-ready",
        False,
        _KR,
    ),
    SourceSpec(
        "daangn",
        3,
        "https://boards-api.greenhouse.io/v1/boards/daangn",
        "greenhouse",
        "ats-ready",
        False,
        _KR,
        ats_slug="daangn",
        note="당근 — 기수집(T-062)",
    ),
    SourceSpec(
        "toss",
        3,
        "https://toss.im/career",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="기수집(T-062 toss custom)",
    ),
    SourceSpec(
        "watcha",
        3,
        "https://watcha.team/careers",
        "custom",
        "candidate",
        False,
        _KR,
        note="careers_url 확정 필요",
    ),
    SourceSpec(
        "tridge", 3, "https://careers.tridge.com", "custom", "custom-ready", False, _KR
    ),
    SourceSpec(
        "megazone",
        3,
        "https://career.megazone.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="메가존클라우드",
    ),
    SourceSpec(
        "class101", 3, "https://jobs.class101.net", "custom", "custom-ready", False, _KR
    ),
]

# ---------------------------------------------------------------------------
# Tier4 — 국내 대기업 + IT 핵심 계열사 (목록 공개 + 지원시 로그인 패턴)
# ---------------------------------------------------------------------------
_TIER4: list[SourceSpec] = [
    # 그룹 통합포털 custom (계열사 필터)
    SourceSpec(
        "samsung-electronics",
        4,
        "https://www.samsungcareers.com/hr/",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="삼성 통합포털(목록 공개 spot-verified)·계열사 필터",
    ),
    SourceSpec(
        "samsung-sds",
        4,
        "https://www.samsungcareers.com/hr/",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="삼성 통합포털 재사용",
    ),
    SourceSpec(
        "samsung-electro-mechanics",
        4,
        "https://www.samsungcareers.com/hr/",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="삼성전기 — 통합포털 재사용",
    ),
    SourceSpec(
        "lg-electronics",
        4,
        "https://careers.lg.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="LG 통합포털·계열사 필터",
    ),
    SourceSpec(
        "lg-cns",
        4,
        "https://careers.lg.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="LG 통합포털 재사용",
    ),
    SourceSpec(
        "lg-uplus",
        4,
        "https://careers.lg.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="LG U+ — 통합포털 재사용",
    ),
    SourceSpec(
        "sk-cc-ax",
        4,
        "https://www.skcareers.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="SK C&C/AX 통합포털",
    ),
    SourceSpec(
        "skt",
        4,
        "https://careers.sktelecom.com",
        "custom",
        "candidate",
        False,
        _KR,
        note="SKT 별도 — careers_url/method 확정",
    ),
    SourceSpec(
        "sk-hynix",
        4,
        "https://recruit.skhynix.com",
        "custom",
        "candidate",
        False,
        _KR,
        note="하이닉스 별도 — 확정 필요",
    ),
    SourceSpec(
        "doosan", 4, "https://career.doosan.com", "custom", "custom-ready", False, _KR
    ),
    SourceSpec(
        "hanwha-systems",
        4,
        "https://www.hanwhain.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="한화 통합(한화시스템)",
    ),
    # 개별 custom
    SourceSpec(
        "hyundai-motor",
        4,
        "https://talent.hyundai.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="현대차 통합 talent 포털",
    ),
    SourceSpec(
        "hyundai-autoever",
        4,
        "https://talent.hyundai.com",
        "custom",
        "candidate",
        False,
        _KR,
        note="현대오토에버 — 통합포털 여부 확정",
    ),
    SourceSpec(
        "hyundai-mobis",
        4,
        "https://talent.hyundai.com",
        "custom",
        "candidate",
        False,
        _KR,
        note="현대모비스 — 확정 필요",
    ),
    SourceSpec(
        "kia",
        4,
        "https://talent.hyundai.com",
        "custom",
        "candidate",
        False,
        _KR,
        note="기아 — 현대 통합포털 여부 확정",
    ),
    SourceSpec("kt", 4, "https://recruit.kt.com", "custom", "custom-ready", False, _KR),
    SourceSpec(
        "posco-dx",
        4,
        "https://recruit.poscodx.com",
        "custom",
        "candidate",
        False,
        _KR,
        note="포스코DX careers_url 확정",
    ),
    SourceSpec(
        "lotte-innovate",
        4,
        "https://www.lotteinnovate.com/recruit",
        "custom",
        "candidate",
        False,
        _KR,
        note="롯데이노베이트 — 확정 필요",
    ),
    SourceSpec(
        "cj-olivenetworks",
        4,
        "https://recruit.cj.net",
        "custom",
        "candidate",
        False,
        _KR,
        note="CJ올리브네트웍스 — CJ 통합 여부 확정",
    ),
    # 위탁 SaaS (recruiter.co.kr — T-075 신설, T-076 공유)
    SourceSpec(
        "shinsegae-inc",
        4,
        "https://shinsegae.recruiter.co.kr",
        "recruiter_co_kr",
        "custom-ready",
        False,
        _KR,
        ats_slug="shinsegae",
        note="신세계I&C",
    ),
    SourceSpec(
        "kt-ds",
        4,
        "https://ktds.recruiter.co.kr",
        "recruiter_co_kr",
        "custom-ready",
        False,
        _KR,
        ats_slug="ktds",
    ),
]

# ---------------------------------------------------------------------------
# Tier5 — 금융권 + IT 자회사 (위탁 SaaS 주류 + custom 인터넷은행·증권)
# ---------------------------------------------------------------------------
_TIER5: list[SourceSpec] = [
    # recruiter.co.kr 위탁 (T-075 어댑터 재사용)
    SourceSpec(
        "shinhan-bank",
        5,
        "https://shinhan.recruiter.co.kr",
        "recruiter_co_kr",
        "custom-ready",
        False,
        _KR,
        ats_slug="shinhan",
    ),
    SourceSpec(
        "shinhan-ds",
        5,
        "https://shinhands.recruiter.co.kr",
        "recruiter_co_kr",
        "custom-ready",
        False,
        _KR,
        ats_slug="shinhands",
    ),
    SourceSpec(
        "hana-bank",
        5,
        "https://hana.recruiter.co.kr",
        "recruiter_co_kr",
        "custom-ready",
        False,
        _KR,
        ats_slug="hana",
    ),
    SourceSpec(
        "hana-ti",
        5,
        "https://hanati.recruiter.co.kr",
        "recruiter_co_kr",
        "custom-ready",
        False,
        _KR,
        ats_slug="hanati",
        note="하나금융티아이",
    ),
    SourceSpec(
        "hyundai-card",
        5,
        "https://hyundaicard.recruiter.co.kr",
        "recruiter_co_kr",
        "custom-ready",
        False,
        _KR,
        ats_slug="hyundaicard",
    ),
    # incruit 위탁
    SourceSpec(
        "kb-bank",
        5,
        "https://kbstar.incruit.com",
        "incruit",
        "custom-ready",
        False,
        _KR,
        ats_slug="kbstar",
        note="KB국민은행",
    ),
    SourceSpec(
        "ibk",
        5,
        "https://ibk.incruit.com",
        "incruit",
        "custom-ready",
        False,
        _KR,
        ats_slug="ibk",
        note="IBK기업은행",
    ),
    SourceSpec(
        "shinhan-card",
        5,
        "https://shinhancard.incruit.com",
        "incruit",
        "custom-ready",
        False,
        _KR,
        ats_slug="shinhancard",
    ),
    # careerlink 위탁
    SourceSpec(
        "woori-bank",
        5,
        "https://woori.careerlink.kr",
        "careerlink",
        "custom-ready",
        False,
        _KR,
        ats_slug="woori",
        note="우리은행",
    ),
    SourceSpec(
        "woori-fis",
        5,
        "https://woorifis.careerlink.kr",
        "careerlink",
        "custom-ready",
        False,
        _KR,
        ats_slug="woorifis",
        note="우리에프아이에스",
    ),
    # 그리팅 (T-071 재사용)
    SourceSpec(
        "kb-datasystem",
        5,
        "https://kbds.career.greetinghr.com",
        "greeting",
        "ats-ready",
        False,
        _KR,
        ats_slug="kbds",
        note="KB데이타시스템",
    ),
    # applyin / custom
    SourceSpec(
        "koscom",
        5,
        "https://koscom.applyin.co.kr",
        "applyin",
        "custom-ready",
        False,
        _KR,
        ats_slug="koscom",
    ),
    SourceSpec(
        "nh-nonghyup",
        5,
        "https://with.nonghyup.com",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="범농협 통합",
    ),
    # custom 인터넷은행·증권
    SourceSpec(
        "kakaobank",
        5,
        "https://recruit.kakaobank.com",
        "custom",
        "custom-ready",
        False,
        _KR,
    ),
    SourceSpec(
        "kbank",
        5,
        "https://www.kbanker.co.kr/recruit",
        "custom",
        "candidate",
        False,
        _KR,
        note="케이뱅크 careers_url 확정",
    ),
    SourceSpec(
        "tossbank",
        5,
        "https://toss.im/career",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="토스뱅크 — 토스 통합 career",
    ),
    SourceSpec(
        "mirae-asset",
        5,
        "https://recruit.miraeasset.com",
        "custom",
        "candidate",
        False,
        _KR,
        note="미래에셋증권 — 확정 필요",
    ),
    SourceSpec(
        "korea-investment",
        5,
        "https://recruit.truefriend.com",
        "custom",
        "candidate",
        False,
        _KR,
        note="한국투자증권 — 확정 필요",
    ),
    SourceSpec(
        "samsung-fire",
        5,
        "https://www.samsungcareers.com/hr/",
        "custom",
        "custom-ready",
        False,
        _KR,
        note="삼성화재 — 삼성 통합포털",
    ),
]

SOURCE_SPECS: list[SourceSpec] = [*_TIER1, *_TIER2, *_TIER3, *_TIER4, *_TIER5]


def discovery_summary() -> dict[str, object]:
    """tier × method 분포 + status 카운트 요약(discovery 리포트 — §4-1 inline)."""
    return {
        "total": len(SOURCE_SPECS),
        "by_tier": dict(Counter(s.tier for s in SOURCE_SPECS)),
        "by_method": dict(Counter(s.method for s in SOURCE_SPECS)),
        "by_family": dict(Counter(method_family(s.method) for s in SOURCE_SPECS)),
        "by_status": dict(Counter(s.status for s in SOURCE_SPECS)),
        "login_required": sum(1 for s in SOURCE_SPECS if s.view_login),
    }
