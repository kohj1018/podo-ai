# T-070-source-discovery-and-method-mapping

## 0. Status
done

## 0-1. Type
research-spike

## 1. 작업 목적
M5 커버리지 확대의 *선행 discovery*. Target universe **Tier1~5**(네카라쿠배+계열사 / 외국계 / 스타트업 / 대기업+IT계열사 / 금융권+IT자회사)의 각 회사에 대해 **공식 채용 URL · 수집 방식(표준 ATS 종류 vs 커스텀) · 한국 location 필터 · view-vs-apply 로그인 · 사전 차단**을 조사해 **소스 레지스트리 seed config**로 기록한다. 이게 있어야 T-071(ATS 어댑터)·T-072(커스텀 어댑터)·T-063(레지스트리·패널)이 정확히 구현된다. graduation line의 "모든 target을 상태와 함께 레지스트리에 기록"을 달성한다(F-020 FAC-1).

## 2. 작업 범위
- **Target 회사 목록은 per-tier 구현 task에 명시**(Tier1=T-072 · Tier2=T-073 · Tier3=T-074 · Tier4=T-075 · Tier5=T-076, ~85개사 웹검색 실측 2026-06-08). 본 task는 그 목록을 *per-source 검증*(careers_url 동작·method 확정·**view-vs-apply 로그인**·location 필터)하고 **`registry_seed`(master data — 코드, 문서 아님)로 확정**한다 — 회사별 `SourceSpec`. 자체 공식사이트 한정, 애그리게이터 영구 제외.
- **각 회사 method 분류**: 표준 ATS(greenhouse/lever/ashby/workday) · **한국 ATS/SaaS(그리팅 greetinghr·recruiter.co.kr·incruit·careerlink·applyin)** · 커스텀(자체 SPA/내부 API). ATS면 slug/endpoint, 커스텀이면 목록 URL + 내부 API 추정.
- **한국 location 필터 실측**(특히 외국계): location 필드(Korea/Seoul/KR)·쿼리로 한국 공고만 거를 수 있는지 확인. 불가 시 status=`no-korea-jobs`.
- **view-vs-apply 로그인 경계 확인 (Tier4/5 핵심, behavioral)**: 공고 *목록*이 공개인지 vs 로그인 필요인지 판별 — **이건 web search로 안 나오는 behavioral 데이터라, 각 careers_url을 httpx로 실제 fetch해 "목록 렌더 vs 로그인 redirect"로 판정**. 목록 로그인이면 status=`login-required`(공개수집 정책상 미수집·패널 투명 노출), 목록 공개·지원만 로그인이면 collectable. (대기업·금융 대부분 "지원 시 로그인"이라 목록 공개 예상 — fetch로 확정.)
- **사전 차단 점검**: robots/ToS·로그인 요구·캡차·구조 파악 가능 여부 → status 후보 분류.
- **산출**: `crawler/src/crawler/sources/registry_seed.py` — 회사별 `SourceSpec(company, tier, careers_url, method, ats_slug?, location_filter, status)` + discovery 리포트(tier별 method 분포·상태 카운트).

## 3. 구현 항목
1. 웹 조사(WebSearch/WebFetch) — 각 target 회사 공식 채용 URL + method 식별. → 확인: 회사별 SourceSpec 채움 (AC-1)
2. `crawler/src/crawler/sources/registry_seed.py` — 신설. `SourceSpec` dataclass + `SOURCE_SPECS: list[SourceSpec]`. status enum: `candidate|ats-ready|custom-ready|blocked|captcha|login-required|no-korea-jobs|unsupported`. → 확인: 필드 완전성·enum 테스트 (AC-1, AC-2)
3. location 필터 실측 — Tier2 각 소스의 한국 필터 방법(또는 불가 사유)을 `SourceSpec.location_filter`에 기록. → 확인: Tier2 항목에 location_filter 또는 status=no-korea-jobs (AC-3)
4. discovery 리포트 — tier별 method 분포(ATS 종류별·custom)·차단 현황·status 카운트 요약.
5. `crawler/tests/test_registry_seed.py` — SourceSpec 필드 완전성 + status enum 유효성 + Tier1 본사 전원 포함 assert. → 확인: pytest (AC-1, AC-2)

## 4. 제외 항목
- 실제 어댑터 구현 — T-071(ATS)·T-072(커스텀).
- 실 수집·cron — T-063/M6.
- 애그리게이터 — 영구 비범위.

## 4-1. 변경 예정 파일/경로
- `crawler/src/crawler/sources/registry_seed.py` (신설 — **SSOT, 커밋**; discovery 요약은 이 모듈 docstring에 인라인 — 별도 리포트 파일·gitignore 불요)
- `crawler/tests/test_registry_seed.py` (신설)

## 5. 완료 조건
Target universe **Tier1~5 전 회사**가 (공식 URL·method·**view-vs-apply 로그인**·location·status)로 registry seed에 기록되고, Tier1 전원 + 외국계 location + **Tier4/5 view_login** 실태가 분류된다. ats-ready/custom-ready/실패 사유별 status가 명시된다.

## 6. Acceptance Criteria
- AC-1 [Given] target 회사 목록(Tier1~5, ~85개사) [When] discovery 수행 [Then] 각 회사가 `SOURCE_SPECS`에 (company·tier·careers_url·method·**view_login**·location·status) 필수 필드로 기록되고 Tier1~5가 모두 포함된다(Tier4/5 view_login 판정 포함).
- AC-2 [Given] registry seed [When] 검증 [Then] 모든 `SourceSpec.status`가 정의된 enum(candidate/ats-ready/custom-ready/blocked/captcha/login-required/no-korea-jobs/unsupported) 중 하나이고, method가 ats(종류 명시) 또는 custom으로 분류된다.
- AC-3 [Given] Tier2 외국계 소스 [When] 한국 location 필터 실측 [Then] location_filter 방법이 기록되거나, 불가 시 status=no-korea-jobs로 사유와 함께 남는다(조용한 누락 0).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_registry_seed.py::test_AC_1_all_tiers_recorded_with_view_login
- AC-2 → pytest::crawler/tests/test_registry_seed.py::test_AC_2_status_and_method_enum_valid
- AC-3 → pytest::crawler/tests/test_registry_seed.py::test_AC_3_foreign_location_filter_or_status

## 6-2. TDD opt-out
- 사유: 탐색적 discovery spike(웹 조사 결과 의존). 산출물(registry_seed 스키마·status enum·필드 완전성)은 합성 입력으로 TDD 적용, 실 회사 데이터 채움은 조사 후 1회.
- Follow-up: method 분포 확정 후 T-071/T-072 범위 구체화(어떤 ATS·어떤 커스텀 사이트인지).

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-020-source-coverage-expansion](../features/F-020-source-coverage-expansion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §3 Collector)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (크롤링 방식)

## 8. 메모
- 우선순위: Tier1(네카라쿠배+계열사) 최우선 → Tier2 외국계 → Tier3 스타트업.
- 외국계 location: ATS(greenhouse/lever)는 보통 location 필드 제공 → "Korea/Seoul" 필터. 글로벌 자체 사이트(구글/MS)는 location 쿼리 파라미터 실측 필요(없으면 no-korea-jobs).
- status enum은 T-063 `source_crawl_status`와 정합(blocked/captcha/login-required/no-korea-jobs/unsupported).
- 조사라 외부 네트워크 의존 → 산출 config는 커밋(오프라인 재현). 실 fetch는 T-071/T-072/T-063.

## 9. 의존성
- depends_on: []
- read_set: ["crawler/src/crawler/sources/", "ai/core/src/core/models.py"]
- write_set: ["crawler/src/crawler/sources/registry_seed.py", "crawler/tests/test_registry_seed.py"]
- assumptions: ["WebSearch/WebFetch로 회사 채용사이트 조사 가능", "자체사이트 운영처 한정(애그리게이터 제외)"]
- verifier: "uv run pytest crawler/tests/test_registry_seed.py"
