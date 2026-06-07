# T-063-source-registry-and-coverage-panel

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
T-070 `registry_seed` + T-071/T-072~076 어댑터 위에서, **전 tier(T-073~076)에서 수집된 소스를 레지스트리에 등록·수집**하고, 수집 상태(소스별 마지막 성공 시각·실패/로그인 사유)를 커버리지 패널 UI에 **투명 노출**한다(F-020 FAC-2 수집 + FAC-4 상태 투명 달성).

## 2. 작업 범위
- 소스 레지스트리에 공식 IT기업 소스 ≥3개 등록(Greenhouse 어댑터 경유 ≥1개 포함, 기존 toss·karrot 포함 카운트 가능).
- 소스별 수집 결과를 **crawler(Collector) 소유 상태 테이블**에 기록(DDL=Prisma, DML=crawler, api read-only 서빙 — ARCH §3-2 write-owner): `source_id`, `method`, `last_success_at`, `last_error`, `status` — taxonomy: `active`/`blocked`/`captcha`/`login-required`/`no-korea-jobs`/`unsupported`. **T-070 discovery seed의 ats-ready/custom-ready 소스를 등록 가능한 만큼**(Greenhouse·Lever·Ashby + Tier1 커스텀 우선), 미구현·실패도 status로 남김.
- 커버리지 패널 API(기존 NestJS `coverage` 모듈 확장 — `coverage.controller.ts`+`coverage.service.ts`, ARCH §7-1): `GET /api/v1/coverage`가 소스별 `{name, tier, status, last_success_at}` 반환.
- 커버리지 패널 UI 컴포넌트(`CoveragePanel`, `podo/apps/web/components/`): 소스별 상태 + 마지막 성공 시각 표시. 수집 실패 소스는 "수집 실패/지연"으로 명시(부분 커버리지 정직 고지 — FAC-3).
- 오프라인 fixture/mock 기반 E2E 보존(M2 패턴).

## 3. 구현 항목
1. `podo/apps/api/prisma/` Prisma migration — `source_crawl_status` 테이블 신설: `source_id TEXT PK`, `tier TEXT`, `method TEXT`, `status TEXT`(active/blocked/captcha/login-required/no-korea-jobs/unsupported), `last_success_at TIMESTAMPTZ`, `last_error TEXT`. → 확인: `pnpm --filter @podo/api prisma migrate dev` 성공 (AC-1)
2. `crawler/src/crawler/run_sources.py` — 신설 or 기존 runner 확장. 레지스트리의 active 소스를 순회 → `gate_check()` → pass 시 `fetch_jobs()` → `job_postings` upsert → `source_crawl_status` 갱신(last_success_at, status=active). 실패/미수집 시 taxonomy status(blocked/captcha/login-required/no-korea-jobs/unsupported) + last_error 기록. → 확인: fixture 실행 후 DB 상태 확인 (AC-1, AC-2)
3. `podo/apps/api/src/coverage/coverage.controller.ts`+`coverage.service.ts`(기존 모듈 확장) — `GET /api/v1/coverage`: `source_crawl_status` 조회 → `{sources: [{name, tier, status, last_success_at}]}` 반환. → 확인: vitest supertest (AC-1, AC-2)
4. `podo/apps/web/components/CoveragePanel.tsx` — 소스별 상태 카드: `active` → 토큰색 + 시각, `blocked/captcha` → 빨강 "차단", `login-required` → 회색 "로그인 필요(미수집)", `no-korea-jobs/unsupported` → 회색 "해당없음/미지원". 전체 성공 거짓 인상 없음 — "N/M 소스 수집 중" 요약. → 확인: vitest fixture mock 시나리오 (AC-2, AC-3)
5. **T-070 `registry_seed`의 ats-ready/custom-ready 소스를 레지스트리에 등록**(Greenhouse·Lever·Ashby ATS[T-071] + Tier1 커스텀[T-072] — 가능한 많이, Tier1 우선). 실패/미지원 소스도 status로 남김(조용한 누락 0). → 확인: 등록 소스 수 ≥ discovery ats/custom-ready 카운트 + 상태 분포 assert (AC-1)
6. `애그리게이터 없음` 회귀 — **T-062:AC-3(registry가 애그리게이터 등록 시 ValueError)이 F-020 FAC-4를 커버**하므로 본 task는 별도 AC 불필요(중복 회귀만 옵션). → 확인: T-062:AC-3.

## 4. 제외 항목
- 실 배포 cron 실가동 — M6.
- CoveragePanel을 피드 메인 페이지에 노출 여부 — UI 배치는 M4 기존 nav 구조 범위 내 최소 삽입(별도 페이지 또는 설정 섹션).
- 소스별 공고 수 통계 — M6 운영 지표.

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/prisma/migrations/` (신규 migration)
- `crawler/src/crawler/run_sources.py` (신설 또는 확장)
- `crawler/src/crawler/sources/registry.py` (소스 ≥3 등록 추가)
- `podo/apps/api/src/coverage/coverage.controller.ts`·`coverage.service.ts` (기존 모듈 확장)
- `podo/apps/web/components/CoveragePanel.tsx` (신설 또는 확장)
- `crawler/tests/test_run_sources.py` (신설)
- `podo/apps/api/test/coverage.spec.ts` (신설)

## 5. 완료 조건
ATS 어댑터 ≥1종 포함 공식 소스 ≥3개에서 공고가 `job_postings`에 수집되고, 커버리지 패널에 소스별 마지막 성공 시각과 실패 소스 구분이 표시된다.

## 6. Acceptance Criteria
- AC-1 [Given] 소스 레지스트리에 공식 소스 ≥3개(ATS 어댑터 ≥1종 포함) 등록, fixture/mock 수집 실행 [When] `run_sources` 실행 [Then] 각 소스의 공고가 `job_postings`에 upsert되고 `source_crawl_status`에 `last_success_at`이 기록되며 `GET /api/v1/coverage`가 소스별 status를 반환한다.
- AC-2 [Given] 특정 소스가 gate 실패(HTTP 403 fixture) [When] 해당 소스 수집 [Then] 그 소스만 `status=blocked`/`last_error` 기록되고 나머지 소스는 정상 수집된다(부분 실패 격리).
- AC-3 [Given] CoveragePanel UI [When] 소스 혼합 상태(일부 blocked·login-required) 응답 [Then] 사유별 status가 명시되고 "전부 수집" 거짓 인상 없이 "N/M 소스 수집 중" 요약이 표시된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_run_sources.py::test_AC_1_sources_upsert_and_coverage_status
- AC-2 → pytest::crawler/tests/test_run_sources.py::test_AC_2_partial_failure_isolation
- AC-3 → vitest::podo/apps/web/test/coverage_panel.spec.tsx::test_AC_3_coverage_panel_partial_failure_display (web 컴포넌트 — UI 렌더 검증이라 web test로)

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-020-source-coverage-expansion](../features/F-020-source-coverage-expansion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §3 Collector)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1), [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components) (CoveragePanel)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 8. 메모
- CoveragePanel은 기존 F-018 CoveragePanel 참조(이미 M4 범위에 언급). M4 구현 여부에 따라 기존 컴포넌트 확장 or 신설 결정(builder가 파일 확인 후 판단).
- 열린 질문: Lever/Workday/Ashby 추가 회사 우선순위는 사용자 결정 — 본 task는 ≥3 최소치만 달성.

## 9. 의존성
- depends_on: [T-070, T-071, T-072, T-073, T-074, T-075, T-076]
- read_set: ["crawler/src/crawler/adapters/**", "crawler/src/crawler/gate.py", "crawler/src/crawler/sources/registry.py", "crawler/src/crawler/sources/registry_seed.py", "podo/apps/api/src/coverage/**", "podo/apps/web/components/**"]
- write_set: ["podo/apps/api/prisma/migrations/**", "crawler/src/crawler/run_sources.py", "podo/apps/api/src/coverage/coverage.controller.ts", "podo/apps/api/src/coverage/coverage.service.ts", "podo/apps/web/components/CoveragePanel.tsx"]
- assumptions: ["T-070(registry_seed)·T-071(ATS)·T-072~076(Tier1~5 어댑터/등록) 완료 — 전 tier 소스·어댑터 존재"]
- verifier: "uv run pytest crawler/tests/test_run_sources.py && pnpm --filter @podo/api test coverage && pnpm --filter @podo/web test coverage_panel"
