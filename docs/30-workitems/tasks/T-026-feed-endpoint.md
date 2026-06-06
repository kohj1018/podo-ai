# T-026-feed-endpoint

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
NestJS가 `GET /api/v1/feed`를 서빙한다 — worker 영속 `recommendations` projection을 `rank_position` 순으로 커서 페이지네이션 + `job_postings` 조인하고, 각 항목 근거(`ranking_runs.result`)를 **파싱 없이 opaque** 첨부한다(cross-LLM P0 회수 — opaque로 정렬 feed 해소). ranking/score 미계산(§3-2).

## 2. 작업 범위
- NestJS Prisma module(read-only) + Feed controller/service.
- `GET /api/v1/feed?cursor=` — `recommendations` ORDER BY `rank_position` + 커서(stable key=`rank_position`) + `job_postings` 조인. 항목별 `result`는 opaque(`unknown`) 첨부.
- error envelope `{ error: { code, message } }`, `ValidationPipe`(쿼리 검증).

## 3. 구현 항목
1. `podo/apps/api/src/feed/feed.service.ts` — 현재: 없음 → 변경: `getFeed(cursor)`:
   - **(a) current run 선택**(cross-LLM P1 회수): seed resume의 최신 `ranking_runs`(`orderBy: { created_at: 'desc' }, take 1`) → `currentRunId`. (rank_position 단독 커서는 run 간 중복이라 stale 혼입 — run 한정 필수.)
   - **(b)** `recommendations.findMany({ where: { run_id: currentRunId, rank_position: { gt: cursor } }, orderBy: { rank_position: 'asc' }, take: N, include: { job_posting: true, ranking_run: { select: { result: true } } } })`. **`result`는 opaque**(DTO `unknown`, 파싱·분기 금지, §7-1). 중복 공고 dedup. **held 행(`fit_level`=null)도 포함**(scored 뒤).
   → 확인: `test_AC_1`이 current run 한정 + rank_position 커서 + 이전 run 행 미혼입. (AC-1)
2. `podo/apps/api/src/feed/feed.controller.ts` — `@Get('api/v1/feed')` + `ValidationPipe`(cursor 쿼리). 응답 = `{ items: [{ posting, fit_level, rank_position, status, evidence: <result opaque> }], nextCursor }`. → 확인: 응답 형태 + opaque 통과. (AC-2)
3. 전역 exception filter — error를 `{ error: { code, message } }` 단일 형태로(§7-1). → 확인: 잘못된 cursor → 400 envelope. (AC-2)
4. Prisma 클라이언트는 `recommendations`/`ranking_runs`/`job_postings`/`crawl_runs`에 **read-only**(write 메서드 미노출, §3-2 규칙1). → 확인: 서비스에 create/update/delete 호출 0(grep). (AC-3)

## 4. 제외 항목
- coverage endpoint(T-027) · UI(T-028/029) · 인증 · ranking/score 계산 · `result` 내부 파싱.

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/src/feed/feed.module.ts`, `feed.controller.ts`, `feed.service.ts`, `podo/apps/api/src/common/error.filter.ts`, `podo/apps/api/test/feed.spec.ts`
- 추가: `podo/apps/api/src/prisma/prisma.service.ts`(NestJS Prisma 래퍼), `podo/apps/api/src/app.module.ts`(FeedModule 배선), `podo/biome.json`(unsafeParameterDecoratorsEnabled — NestJS 파라미터 데코레이터)

## 5. 완료 조건
`GET /api/v1/feed`가 `rank_position` 순 공고 목록을 커서 페이지로 반환하고 근거를 opaque로 첨부하며, NestJS는 어떤 worker 테이블에도 write하지 않는다.

## 6. Acceptance Criteria
- AC-1 [Given] 여러 `ranking_runs`(재채점 포함) + `recommendations` [When] `GET /api/v1/feed?cursor=K` [Then] **최신(current) run**의 `recommendations`만 `rank_position > K` 오름차순 take N 반환하고(이전 run 행 미혼입) `nextCursor`를 주며, held 행(`fit_level`=null)은 scored 뒤에 포함된다(중복 공고 dedup).
- AC-2 [Given] 피드 응답 [When] 항목 직렬화 + 잘못된 cursor 요청 [Then] `result`가 opaque(파싱 없이 그대로 첨부)이고 오류는 `{ error: { code, message } }` 단일 형태(400)다.
- AC-3 [Given] Feed module [When] 코드 정적 점검 [Then] worker/crawler 소유 테이블에 대한 create/update/delete 호출이 0이다(read-only).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/api/test/feed.spec.ts::test_AC_1_current_run_sorted_cursor_no_stale
- AC-2 → vitest::podo/apps/api/test/feed.spec.ts::test_AC_2_result_opaque_and_error_envelope
- AC-3 → vitest::podo/apps/api/test/feed.spec.ts::test_AC_3_read_only_no_writes

## 6-2. TDD opt-out
<!-- TDD 적용 — Prisma test DB(compose PG) + supertest. -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-009-api-serving](../features/F-009-api-serving.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 규칙1·3)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) (경로·envelope·JSONB pass-through·커서)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-CONTRACT)

## 8. 메모
- 해석 확정: 정렬·커서 = `recommendations.rank_position`(cross-LLM P0/M2-repair-1) — `result.final_ranking` 파싱 금지. `result`는 evidence opaque.
- repair-plan 2026-06-06 [default] P1 Plan-ambiguity: Adopt — current run(최신 ranking_runs) 한정 + cursor `(run_id, rank_position)`(stale run 행 미혼입).
- repair-plan 2026-06-06 [default] P0 Plan-FAC-coverage: Adopt-modified — held 행(fit_level null)을 feed에 포함(scored 뒤 → T-029 보류 렌더).
- 구현 노트(2026-06-06): 메인 세션 수동. current run = 최신 `ranking_runs`(orderBy created_at desc). `result`는 `unknown`으로 opaque pass-through(파싱 0). error.filter는 APP_FILTER로 모듈 등록.
- 테스트 전략: Vitest/esbuild가 `emitDecoratorMetadata` 미지원 → NestJS DI 풀부트(Test.createTestingModule)+supertest 불가(swc 미도입 — 리스크 회피). 대신 **FeedService를 실 PrismaService로 직접 인스턴스화**해 AC-1(current run/cursor/no-stale/held) + AC-2 opaque 검증, error envelope는 AllExceptionsFilter.catch() 직접 호출 검증, AC-3는 feed.service.ts 소스 정적 스캔(create/update/delete 0). HTTP 배선(routing/pipe/filter)은 표준 NestJS — 미부트.
- biome `unsafeParameterDecoratorsEnabled: true`(biome.json) — NestJS 파라미터 데코레이터(@Query) 파싱 필수(미설정 시 "Decorators are not valid here").
- prisma.service.ts: PrismaClient 확장(onModuleInit $connect). FeedService는 write 메서드 호출 0(AC-3) — read-only.
- DB 테스트는 DATABASE_URL 없으면 skip(게이트 보호). 라이브: DATABASE_URL 주입 시 api vitest 4 passed(feed 3 + health 1), cleanup으로 멱등.

## 9. 의존성
- depends_on: [T-018, T-020, T-022]
- read_set: ["podo/apps/api/prisma/schema.prisma"]
- write_set: ["podo/apps/api/src/feed/**", "podo/apps/api/src/common/error.filter.ts", "podo/apps/api/test/feed.spec.ts"]
- assumptions: ["T-022가 recommendations/ranking_runs를 채움"]
- verifier: "pnpm --filter api test"
