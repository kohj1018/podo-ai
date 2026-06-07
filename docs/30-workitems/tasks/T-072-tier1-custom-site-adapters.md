# T-072-tier1-custom-site-adapters

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
표준 ATS를 쓰지 않는 **Tier1(네카라쿠배+주요 계열사) 자체 채용사이트**를 수집한다(최우선 커버리지). 회사마다 구조가 다르므로 **`BaseCustomAdapter` 공통 골격**(내부 API 발견 → 페이지네이션 → 파싱 → A-1 게이트)을 추출하고 회사별 차이만 override해 유지보수를 관리한다. T-070 discovery가 `custom-ready`로 분류한 Tier1 소스를 구현한다.

## 2. 작업 범위
- `crawler/src/crawler/adapters/custom_base.py` — `BaseCustomAdapter(BaseCrawlerAdapter)`: 공통 골격(httpx 우선·필요 시 Playwright headless, 내부 JSON API 우선·실패 시 HTML 파싱, 페이지네이션 추상, parse 실패율 게이트, location 필터).
- **Tier1 custom 어댑터(실측 — 전부 list-public, 목록 열람 로그인 불필요)**: 네이버 자체포털(recruit.navercorp.com — 계열사 스노우·네이버클라우드·네이버파이낸셜·웍스모바일이 *동일 포털 패턴* → config 재사용) · 카카오 본사(careers.kakao.com) · 카카오게임즈(recruit.kakaogames.com) · 카카오엔터프라이즈 · 라인플러스(careers.linecorp.com) · 우아한형제들/배민(career.woowahan.com).
- **Tier1 중 ATS 사용분은 공유 어댑터로 레지스트리 등록(custom 신규 X)**: 쿠팡=greenhouse(T-062, coupang.jobs↔boards.greenhouse.io/coupang) · 카카오페이·카카오엔터테인먼트·카카오모빌리티·카카오스타일=그리팅(T-071) · 네이버웹툰=lever(T-071).
- 계열사는 본사 동일 플랫폼이면 config 재사용(네이버 계열 포털·카카오 그리팅 계열).
- 동적 렌더 필요 소스만 Playwright 승격(ARCH §6, 정적 httpx 우선 — 비용↓).
- 오프라인 fixture(저장 응답 스냅샷)로 무키 재현.

## 3. 구현 항목
1. `adapters/custom_base.py` — `BaseCustomAdapter`: `fetch_jobs(location)` 골격 + 내부 API 발견 helper + parse 실패율 게이트. → 단위 테스트 (AC-1)
2. Tier1 custom 어댑터(discovery custom-ready 회사) — 회사별 `XxxAdapter(BaseCustomAdapter)`: careers endpoint, 파싱 매핑, `JobPosting` 변환. 본사 우선, 계열사는 가능 시 config 재사용. → fixture 테스트 (AC-1, AC-2)
3. 동적 렌더 소스 → Playwright 승격 경로(필요 소스만). → 해당 fixture (AC-1)
4. 실패 소스 status — parse 실패/구조변경 시 게이트가 status(blocked/unsupported) 반환(조용한 누락 0). → 게이트 테스트 (AC-3)
5. fixture(`crawler/tests/fixtures/custom_*.json|html`) + `crawler/tests/test_custom_adapters.py`. AC-1~AC-3.

## 4. 제외 항목
- Tier2/3 커스텀 사이트 — 본 task는 Tier1 우선(graduation). Tier2/3 custom은 점진(후속, target universe엔 포함).
- ATS 사용 회사 — T-071.
- 소스 레지스트리 등록·패널 — T-063.

## 4-1. 변경 예정 파일/경로
- `crawler/src/crawler/adapters/custom_base.py` (신설)
- `crawler/src/crawler/adapters/<tier1_company>.py` (discovery custom-ready 회사별 신설)
- `crawler/tests/fixtures/custom_*` (신설)
- `crawler/tests/test_custom_adapters.py` (신설)

## 5. 완료 조건
`BaseCustomAdapter` 공통 골격이 확립되고, Tier1(네카라쿠배 본사) 자체사이트 중 custom-ready 소스가 fixture 기반으로 수집되며, 실패 소스는 status로 투명 분류된다.

## 6. Acceptance Criteria
- AC-1 [Given] Tier1 custom 회사 fixture(내부 API 또는 HTML 스냅샷) [When] 해당 `XxxAdapter.fetch_jobs(location="KR")` [Then] `JobPosting` list 반환 + `BaseCustomAdapter` 골격 재사용 + 한국 공고 필터.
- AC-2 [Given] 동일 플랫폼 계열사 fixture [When] config 재사용 어댑터 [Then] 본사 어댑터 골격으로 수집된다(중복 bespoke 최소화).
- AC-3 [Given] 구조변경/차단 fixture(parse 실패율 ≥30% 또는 403) [When] custom 어댑터 게이트 [Then] `GateResult(ok=False)` + registry status(blocked/unsupported)로 명시되고 조용히 누락되지 않는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_custom_adapters.py::test_AC_1_tier1_custom_fetch
- AC-2 → pytest::crawler/tests/test_custom_adapters.py::test_AC_2_affiliate_config_reuse
- AC-3 → pytest::crawler/tests/test_custom_adapters.py::test_AC_3_gate_failure_status

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-020-source-coverage-expansion](../features/F-020-source-coverage-expansion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동·headless, §3 Collector)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 8. 메모
- 가장 큰 공수(자체사이트 bespoke). 구현 중 회사 클러스터별로 더 쪼갤 수 있음(예: 네이버/카카오 묶음, 라인/쿠팡/배민 묶음).
- 구체 회사·method는 T-070 discovery `custom-ready` 분류로 확정. ATS 쓰는 Tier1은 T-071.
- 자체사이트는 구조변경 취약 → A-1 게이트 필수(각 어댑터). 동적 렌더만 Playwright(비용 큼 — 정적 우선).

## 9. 의존성
- depends_on: [T-062, T-070]
- read_set: ["crawler/src/crawler/adapters/base.py", "crawler/src/crawler/sources/registry_seed.py", "ai/core/src/core/models.py"]
- write_set: ["crawler/src/crawler/adapters/custom_base.py", "crawler/src/crawler/adapters/**", "crawler/tests/test_custom_adapters.py"]
- assumptions: ["T-062 완료(BaseCrawlerAdapter)", "T-070 discovery로 Tier1 custom 회사·method·careers_url 확정"]
- verifier: "uv run pytest crawler/tests/test_custom_adapters.py"
