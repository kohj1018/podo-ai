# T-074-tier3-startup-sources

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
Target universe **Tier3(Series C+·유니콘 국내 스타트업, 20사)** 수집을 구현한다. 한국 ATS **그리팅(greetinghr)** 7사 + Workday 2사는 공유 어댑터(T-071)로, custom 11사는 `BaseCustomAdapter`(T-072) 어댑터로 처리한다. 전부 국내라 location 전체.

## 2. 작업 범위 (대상 20사 — T-070 검증 후 확정)
- **greetinghr**(T-071): 컬리·리디·뱅크샐러드·여기어때(GC컴퍼니)·라포랩스(퀸잇)·강남언니(힐링페이퍼)·패스트파이브.
- **workday**(T-071): 야놀자(yanolja.wd102)·무신사(musinsa.wd3).
- **custom**(BaseCustomAdapter): 두나무(careers.dunamu.com)·직방(career.zigbang.com)·오늘의집(bucketplace.com/careers)·쏘카(socarcorp.kr)·빗썸(bithumb-careers.com)·당근(about.daangn.com/jobs)·토스(toss.im/career)·왓챠·트릿지(careers.tridge.com)·메가존클라우드(career.megazone.com)·클래스101(jobs.class101.net).
- ATS 소스 → 레지스트리 등록. custom 11사 → 사이트별 어댑터(공통 골격 재사용). 오프라인 fixture(무키).

## 3. 구현 항목
1. T-070 `registry_seed`의 Tier3 20사 항목(read-only — seed는 T-070 단일 소유) 기반 method별 어댑터 매핑·수집 검증. → 매핑·수집 assert (AC-1)
2. custom 11사 어댑터(`adapters/startup_*.py`, `BaseCustomAdapter` 재사용). → fixture 테스트 (AC-1)
3. greetinghr 7사·workday 2사는 공유 어댑터로 수집(slug 등록). → 테스트 (AC-2)
4. fixture + `crawler/tests/test_tier3_startup.py`. AC-1~AC-3.

## 4. 제외 항목
- ATS 어댑터 자체 구현(그리팅/workday) — T-071.
- 로그인 뒤 크롤링 — 영구 비범위.
- Tier2/4/5 — 각 task.

## 4-1. 변경 예정 파일/경로
- (`registry_seed.py`는 T-070 소유 read-only — 본 task 미변경)
- `crawler/src/crawler/adapters/startup_*.py` (custom 어댑터)
- `crawler/tests/test_tier3_startup.py`

## 5. 완료 조건
Tier3 20사가 레지스트리에 등록되고, 그리팅·workday + custom 어댑터로 공고가 `job_postings`에 수집된다. 구조변경/실패 소스는 status로 투명.

## 6. Acceptance Criteria
- AC-1 [Given] Tier3 20사 registry_seed [When] 수집 [Then] custom 11사 어댑터가 각 공고를 `job_postings`에 upsert하고 미수집은 status로 기록된다.
- AC-2 [Given] 그리팅 7사·workday 2사 slug [When] 공유 어댑터 수집 [Then] 각 소스 공고가 수집된다(어댑터 재사용 — 신규 어댑터 0).
- AC-3 [Given] 구조변경 fixture(parse 실패율 ≥30%) [When] 게이트 [Then] status=blocked/unsupported로 명시되고 조용히 누락되지 않는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_tier3_startup.py::test_AC_1_custom_startups_collected
- AC-2 → pytest::crawler/tests/test_tier3_startup.py::test_AC_2_greeting_workday_shared_adapter
- AC-3 → pytest::crawler/tests/test_tier3_startup.py::test_AC_3_gate_failure_status

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-020-source-coverage-expansion](../features/F-020-source-coverage-expansion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §3 Collector)

## 8. 메모
- 그리팅이 한국 스타트업 ATS 1위 → 본 tier의 다수가 어댑터 1개 재사용(곱셈). custom 11사가 실제 공수.
- 회사·careers_url·method는 T-070 discovery 확정치 사용. 패스트파이브 등 Workable 병행 인스턴스는 discovery가 우선 method 결정.

## 9. 의존성
- depends_on: [T-070, T-071, T-072]
- read_set: ["crawler/src/crawler/adapters/**", "crawler/src/crawler/sources/registry_seed.py"]
- write_set: ["crawler/src/crawler/adapters/startup_*.py", "crawler/tests/test_tier3_startup.py"]  # registry_seed는 T-070 단일 writer (read-only)
- assumptions: ["T-070(registry_seed)·T-071(greeting/workday)·T-072(BaseCustomAdapter) 완료"]
- verifier: "uv run pytest crawler/tests/test_tier3_startup.py"
