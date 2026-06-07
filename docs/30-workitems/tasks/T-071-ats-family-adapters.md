# T-071-ats-family-adapters

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
T-062의 `BaseCrawlerAdapter`(+Greenhouse) 위에서 **ATS 어댑터를 그리팅(greetinghr)·Workday·Lever·Ashby로 확장**하고 **location 필터를 어댑터 1급 기능으로 구현**한다. T-070 discovery가 `ats-ready`로 분류한 소스를 *가능한 많이* 수집한다. **실측 반영 우선순위(T-070 discovery): 그리팅(한국 스타트업 ATS 1위)·Workday(외국계 다수: NVIDIA·Intel·Salesforce·Snowflake·야놀자·무신사) > Lever·Ashby.** (한국 채용대행 SaaS recruiter.co.kr·incruit·careerlink는 login 확인 후 후보.)

## 2. 작업 범위
- `crawler/src/crawler/adapters/greeting.py` — **그리팅(greetinghr) 어댑터 (우선 — 한국 스타트업 ATS 1위: 컬리·리디·뱅크샐러드·여기어때·라포랩스·강남언니·패스트파이브·KB데이타시스템)**. `{company}.career.greetinghr.com` 목록.
- `crawler/src/crawler/adapters/workday.py` — **Workday 어댑터 (우선 — 외국계·유니콘 다수)**. `*.myworkdayjobs.com` CxS endpoint + location facet.
- `crawler/src/crawler/adapters/lever.py` — Lever Postings API(`api.lever.co/v0/postings/{company}`) 어댑터. location 필터.
- `crawler/src/crawler/adapters/ashby.py` — Ashby job board API 어댑터. location 필터.
- (후보) 한국 채용대행 SaaS recruiter.co.kr·incruit·careerlink — Tier4/5 다수 래핑하나 login-gated 많음 → T-070이 view-vs-apply 로그인 확인 후 *공개 목록* 플랫폼만 어댑터화(login-gated는 status=login-required).
- `BaseCrawlerAdapter.fetch_jobs(location: str = "KR")` location 1급 파라미터 — ATS별 location 필드/파라미터 매핑(T-070 `location_filter` 사용). 외국계 한국 채용만 거름.
- 각 어댑터 A-1 게이트(parse 실패율·차단) 적용.
- 오프라인 fixture(`crawler/tests/fixtures/{lever,ashby,workday}_*.json`) — 무키 재현.

## 3. 구현 항목
1. `adapters/greeting.py` — `GreetingAdapter`: `{company}.career.greetinghr.com` 목록 API/HTML, 페이지네이션, RawJob(dict) 변환(한국 스타트업 1위 — 우선). → fixture 테스트 (AC-1)
2. `adapters/workday.py` — `WorkdayAdapter`: `*.myworkdayjobs.com` CxS endpoint + location facet(외국계 다수 — 우선). → fixture 테스트 (AC-1, AC-2)
3. `adapters/lever.py` · `adapters/ashby.py` — `LeverAdapter`·`AshbyAdapter`: JSON API, location 필터, 변환. → fixture 테스트 (AC-1)
4. `BaseCrawlerAdapter` location 파라미터 — `fetch_jobs(location="KR")` + ATS별 location 필터 적용. → location 필터 테스트 (AC-2)
5. fixture 신설(greeting/workday/lever/ashby) + `crawler/tests/test_ats_family.py`. AC-1~AC-3. (discovery에 없는 ATS는 미구현 — YAGNI.)

## 4. 제외 항목
- 커스텀 자체사이트 어댑터 — T-072.
- 소스 레지스트리 등록·패널 — T-063.
- 실 cron — M6.

## 4-1. 변경 예정 파일/경로
- `crawler/src/crawler/adapters/greeting.py` (신설 — **우선, 한국 스타트업 1위**) · `workday.py` · `lever.py` · `ashby.py` (신설)
- `crawler/src/crawler/adapters/base.py` (location 파라미터 — T-062와 정합)
- `crawler/tests/fixtures/{greeting,workday,lever,ashby}_jobs.json` (신설)
- `crawler/tests/test_ats_family.py` (신설)

## 5. 완료 조건
**그리팅·Workday(실측 우선)** + Lever·Ashby 어댑터가 fixture 기반으로 동작하고(Workday는 discovery에 있으면 구현/없으면 unsupported), 모든 ATS 어댑터가 location="KR" 필터로 한국 공고만 거른다.

## 6. Acceptance Criteria
- AC-1 [Given] 그리팅·Workday·Lever·Ashby fixture JSON [When] 각 어댑터 `fetch_jobs()` [Then] RawJob(dict) list 반환 + 페이지네이션 처리 + 기존 `BaseCrawlerAdapter` 인터페이스 정합(우선순위 그리팅·Workday).
- AC-2 [Given] location 필드가 섞인 fixture(서울/해외) [When] `fetch_jobs(location="KR")` [Then] 한국(Korea/Seoul) 공고만 반환된다(외국계 한국 채용 필터).
- AC-3 [Given] discovery에 Workday 소스 [When] WorkdayAdapter [Then] 구현 시 fixture 동작, 미구현 시 registry status=unsupported로 명시(조용한 누락 없음).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_ats_family.py::test_AC_1_greeting_workday_lever_ashby_fetch
- AC-2 → pytest::crawler/tests/test_ats_family.py::test_AC_2_location_filter_korea
- AC-3 → pytest::crawler/tests/test_ats_family.py::test_AC_3_workday_or_unsupported

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-020-source-coverage-expansion](../features/F-020-source-coverage-expansion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §3 Collector)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 8. 메모
- 구체 ATS 분포는 T-070 discovery 산출로 확정(없는 ATS 어댑터는 미구현 — YAGNI). 우선 Lever·Ashby, Workday는 소스 있을 때만.
- location 필터는 ATS마다 필드/파라미터 상이 → T-070 `location_filter` 매핑 사용.

## 9. 의존성
- depends_on: [T-062, T-070]
- read_set: ["crawler/src/crawler/adapters/base.py", "crawler/src/crawler/sources/registry_seed.py", "ai/core/src/core/models.py"]
- write_set: ["crawler/src/crawler/adapters/greeting.py", "crawler/src/crawler/adapters/workday.py", "crawler/src/crawler/adapters/lever.py", "crawler/src/crawler/adapters/ashby.py", "crawler/src/crawler/adapters/base.py", "crawler/tests/test_ats_family.py"]
- assumptions: ["T-062 완료(BaseCrawlerAdapter)", "T-070 discovery로 ATS 분포·location 방법 확정"]
- verifier: "uv run pytest crawler/tests/test_ats_family.py"
