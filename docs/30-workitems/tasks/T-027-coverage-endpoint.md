# T-027-coverage-endpoint

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
NestJS가 `GET /api/v1/coverage`를 서빙한다 — `crawl_runs`(run별 1행)에서 채널별 수집/미수집 + `last_success_at`(= `MAX(run_at WHERE success)`)을 반환해 커버리지 투명성 패널(Fail #3 차단)의 데이터원을 만든다.

## 2. 작업 범위
- `GET /api/v1/coverage` — 수집 채널(토스·당근) 각각의 최신 status + `last_success_at` + 미수집 채널 명시.
- read-only(§3-2). error envelope(§7-1).

## 3. 구현 항목
1. `podo/apps/api/src/coverage/coverage.service.ts` — 현재: 없음 → 변경: `getCoverage()` — 채널별 `MAX(run_at) WHERE status='success'` 집계(`crawl_runs`) + 최신 run status. 알려진 채널 목록(토스·당근) 대비 미수집 표시. → 확인: `test_AC_1`이 채널별 last_success_at 반환. (AC-1)
2. `podo/apps/api/src/coverage/coverage.controller.ts` — `@Get('api/v1/coverage')` → `{ channels: [{ name, status, last_success_at }], uncollected: [...] }`. → 확인: 응답 형태. (AC-1)
3. read-only(crawl_runs write 0). → 확인: 정적 점검. (AC-2)

## 4. 제외 항목
- feed endpoint(T-026) · UI 패널(T-029) · 인증 · crawl 로직.

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/src/coverage/coverage.module.ts`, `coverage.controller.ts`, `coverage.service.ts`, `podo/apps/api/test/coverage.spec.ts`

## 5. 완료 조건
`GET /api/v1/coverage`가 채널별 수집 상태 + 마지막 성공 시각 + 미수집 채널을 반환하고, NestJS는 `crawl_runs`에 write하지 않는다.

## 6. Acceptance Criteria
- AC-1 [Given] `crawl_runs`에 여러 run 행(성공/실패 혼재) [When] `GET /api/v1/coverage` [Then] 채널별 `last_success_at` = `MAX(run_at WHERE status='success')`와 최신 status, 미수집 채널 목록을 반환한다.
- AC-2 [Given] Coverage module [When] 정적 점검 [Then] `crawl_runs`에 대한 write 호출이 0이다(read-only).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/api/test/coverage.spec.ts::test_AC_1_last_success_at_per_channel
- AC-2 → vitest::podo/apps/api/test/coverage.spec.ts::test_AC_2_read_only

## 6-2. TDD opt-out
<!-- TDD 적용 — Prisma test DB + supertest. -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-009-api-serving](../features/F-009-api-serving.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§4 CoverageState)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 8. 메모
- 해석 확정: `last_success_at` = run별 1행에서 파생(MAX success) — cross-LLM P1(M2-repair-3) 정합. 채널 목록(토스·당근)은 알려진 상수와 대비해 미수집 표시.

## 9. 의존성
- depends_on: [T-020, T-024]
- read_set: ["podo/apps/api/prisma/schema.prisma"]
- write_set: ["podo/apps/api/src/coverage/**", "podo/apps/api/test/coverage.spec.ts"]
- assumptions: ["T-024가 crawl_runs run행을 채움"]
- verifier: "pnpm --filter api test"
