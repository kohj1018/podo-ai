# T-062-ats-adapter-infrastructure

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
공식 채용 페이지 커버리지를 ATS별 어댑터 구조로 확장하기 위한 기반을 신설한다. 현재 크롤러는 토스·당근 bespoke 구현만 있고 공통 인터페이스가 없다. 본 task가 **ATS 어댑터 공통 인터페이스 + Greenhouse 어댑터 ≥1종(최소 달성 기준)**을 구현하고, 신규 소스가 A-1형 게이트(차단/구조변경/캡차 감지)를 통과해야 "수집 중"으로 승격되는 레지스트리·게이트 검사 경로를 확립한다. 이는 F-020의 "ATS 어댑터 전략으로 커버리지 곱셈 확장" 목표를 구조적으로 받쳐주는 선행 enabler다(DISCOVERY A-1·A-11, F-020 FAC-1~FAC-4).

## 2. 작업 범위
- `crawler/src/crawler/adapters/base.py` — ATS 어댑터 공통 인터페이스(`BaseCrawlerAdapter`: `fetch_jobs(location: str = "KR") -> list[RawJob]`(**RawJob=`dict[str,str]` — `persistence.upsert_jobs`가 소비, JobPosting 아님**), `gate_check() -> GateResult`). **location 1급 파라미터**(외국계 한국 채용 필터 — 구체 적용은 T-071 ATS·T-072 custom).
- `crawler/src/crawler/adapters/greenhouse.py` — Greenhouse Jobs API v1 어댑터 구현(httpx 기반, 페이지네이션).
- `crawler/src/crawler/sources/registry.py` — 소스 레지스트리(회사↔어댑터↔ATS 매핑). 티어(대기업/외국계/스타트업) 필드 포함.
- `crawler/src/crawler/gate.py` — A-1형 게이트 검사 로직(차단 감지: HTTP 403/429/캡차 응답 패턴; 구조변경 감지: 필수 필드 parse 실패율 ≥30%).
- **기존 소스 실태(2026-06-08 코드 확인)**: `crawler/src/crawler/fetch_jobs.py`의 `fetch_toss_jobs`/`fetch_daangn_jobs` *함수*(별도 `sources/` 파일 없음, RawJob dict 반환)를 어댑터 클래스로 리팩토링(동작 불변, ADR-101#amend). **당근(daangn)은 이미 Greenhouse board API**(`boards-api.greenhouse.io/v1/boards/daangn`) → `GreenhouseAdapter`로 일반화. **toss는 custom API**(`api-public.toss.im`) → toss 커스텀 어댑터. ("karrot"은 daangn=당근의 오기 — 별개 소스 아님.)
- 오프라인 fixture 테스트(`crawler/tests/fixtures/greenhouse_*.json`) — 무키 E2E 보존(M2 패턴).

## 3. 구현 항목
1. `crawler/src/crawler/adapters/base.py` — 신설. `BaseCrawlerAdapter(ABC)`: `fetch_jobs(location: str = "KR") -> list[RawJob]`(RawJob=dict), `gate_check() -> GateResult(ok: bool, reason: str)`. `GateResult` dataclass 정의. location은 어댑터별(ATS/custom) 구현 — base는 시그니처만. → 확인: mypy 통과 (AC-1)
2. `crawler/src/crawler/adapters/greenhouse.py` — 신설. `GreenhouseAdapter(BaseCrawlerAdapter)`: `company_slug` + `base_url=https://boards-api.greenhouse.io/v1/boards/{slug}/jobs` httpx GET, 페이지네이션, RawJob(dict) 변환. **기존 `fetch_daangn_jobs`(이미 이 API 사용)를 일반화**(daangn=slug 1 사례). `gate_check()`: 2xx 이외 or parse 실패율 ≥30% → `ok=False`. → 확인: fixture 단위 테스트 pass (AC-1)
3. `crawler/src/crawler/gate.py` — 신설. `run_gate_check(adapter: BaseCrawlerAdapter) -> GateResult`. 차단 패턴(HTTP 403/429/CAPTCHA body 키워드), 구조변경(필수 필드 parse 실패율) 감지. → 확인: 단위 테스트 (AC-2)
4. `crawler/src/crawler/sources/registry.py` — 신설. `SourceRegistry`: `sources: list[SourceEntry(company, adapter_cls, tier, status)]`. `register(entry)`, `get_active_sources() -> list[SourceEntry]`. 초기 등록: toss(custom 어댑터), daangn(GreenhouseAdapter), greenhouse 회사 ≥1(예: Moloco). → 확인: registry 조회 테스트 (AC-1)
5. `crawler/src/crawler/adapters/toss.py` — `fetch_jobs.py`의 toss 로직 이전(custom 어댑터, RawJob 반환). daangn은 GreenhouseAdapter로 흡수(별도 파일 불요). `fetch_jobs.py`는 어댑터 호출로 정리(외부 행동 불변). → 확인: 기존 `crawler/tests/test_fetch.py` 회귀 없음 (AC-1)
6. `crawler/tests/fixtures/greenhouse_jobs.json` — Greenhouse API 응답 형태의 fixture (최소 3개 공고). → 확인: fixture 기반 테스트가 외부 호출 없이 pass (AC-1)
7. `애그리게이터 차단 가드` — `registry.py`에 `AggregatorGuard`: `BANNED_DOMAINS = {"jobkorea.co.kr", "saramin.co.kr", "wanted.co.kr", ...}`. 등록 시 도메인 검사 → 해당 도메인 `register()` 호출 시 `ValueError` raise. → 확인: 단위 테스트 (AC-3)

## 4. 제외 항목
- Lever/Workday/Ashby 어댑터 구현 — T-063에서 소스 추가 시 동일 패턴 확장(본 task는 Greenhouse 1종으로 패턴 확립).
- 커버리지 패널 UI — T-063.
- 실 배포 cron 실가동 — M6 비범위.
- 애그리게이터 소스 자체 — 영구 비범위.

## 4-1. 변경 예정 파일/경로
- `crawler/src/crawler/adapters/base.py` (신설)
- `crawler/src/crawler/adapters/greenhouse.py` (신설)
- `crawler/src/crawler/gate.py` (신설)
- `crawler/src/crawler/sources/registry.py` (신설)
- `crawler/src/crawler/adapters/toss.py` (신설 — fetch_jobs.py toss 로직 이전)
- `crawler/src/crawler/fetch_jobs.py` (어댑터 호출로 리팩토링; daangn은 GreenhouseAdapter 흡수)
- `crawler/tests/fixtures/greenhouse_jobs.json` (신설)
- `crawler/tests/test_ats_adapter.py` (신설)
- `crawler/tests/test_gate.py` (신설)

## 5. 완료 조건
Greenhouse 어댑터 ≥1종이 구현되고 fixture 기반 오프라인 테스트가 pass되며, A-1형 게이트 검사 로직과 소스 레지스트리(애그리게이터 차단 포함)가 작동한다.

## 6. Acceptance Criteria
- AC-1 [Given] Greenhouse fixture JSON(daangn slug) [When] `GreenhouseAdapter.fetch_jobs()` 호출 [Then] RawJob(dict) list를 반환하고 레지스트리에 tier·status 포함 등록되며, 기존 toss·daangn fetch가 어댑터 인터페이스로 동작한다(`test_fetch.py` 회귀 0).
- AC-2 [Given] 차단 응답(HTTP 403) 또는 필수 필드 parse 실패율 ≥30% fixture [When] `run_gate_check()` 호출 [Then] `GateResult(ok=False, reason=...)` 반환하고 소스 status가 "수집 실패"로 기록된다.
- AC-3 [Given] 애그리게이터 도메인(`jobkorea.co.kr` 등)을 registry에 등록 시도 [When] `registry.register()` 호출 [Then] `ValueError`가 raise되고 소스가 등록되지 않는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_ats_adapter.py::test_AC_1_greenhouse_adapter_fetch_and_registry
- AC-2 → pytest::crawler/tests/test_gate.py::test_AC_2_gate_check_blocked_response
- AC-3 → pytest::crawler/tests/test_ats_adapter.py::test_AC_3_aggregator_registration_raises

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-020-source-coverage-expansion](../features/F-020-source-coverage-expansion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §3 Collector)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (크롤링 방식)

## 8. 메모
- `BaseCrawlerAdapter` 공통 인터페이스는 3회 반복(toss·daangn·greenhouse) 확인 시점 도입 — YAGNI 충족(ADR-006).
- **(정정 2026-06-08, 코드 실측)** task 가정 수정: ① 어댑터 반환형 `JobPosting`→**`RawJob`(dict[str,str])** (persistence가 소비; JobPosting=ai/core 스코어링 모델, crawler 미사용) ② 기존 소스=`fetch_jobs.py` *함수*(sources/ 파일·toss.py·karrot.py 없음) ③ "karrot"→**daangn(당근)**, 이미 Greenhouse board API 사용 → GreenhouseAdapter로 일반화.
- 본 task는 레지스트리 *메커니즘* + Greenhouse 패턴 + location 시그니처 확립까지. 전 target 목록(seed)은 **T-070 discovery**, 추가 ATS(Lever/Ashby/Workday)는 **T-071**, 커스텀은 **T-072**, 전체 등록·상태·패널은 **T-063**.
- Greenhouse `boards-api`는 인증 불필요(public). location 필터 실제 적용은 T-071(ATS)·T-072(custom)가 method별로.
- repair-workitem 2026-06-08 P1 test-coverage: Adopt — 구현 #4 seed(build_default_registry) 검증 테스트 추가(toss=TossAdapter/daangn=Greenhouse/moloco 활성).

## 9. 의존성
- depends_on: []
- read_set: ["crawler/src/crawler/", "ai/core/src/core/models.py"]
- write_set: ["crawler/src/crawler/adapters/**", "crawler/src/crawler/gate.py", "crawler/src/crawler/sources/registry.py", "crawler/tests/test_ats_adapter.py", "crawler/tests/test_gate.py"]
- assumptions: ["어댑터 반환형=RawJob(dict[str,str], `persistence.upsert_jobs` 소비) — JobPosting(ai/core)은 스코어링 모델이라 crawler 미사용", "기존 `fetch_jobs.py`(toss/daangn) + `crawler/tests/test_fetch.py` 통과 상태"]
- verifier: "uv run pytest crawler/tests/test_ats_adapter.py crawler/tests/test_gate.py"
