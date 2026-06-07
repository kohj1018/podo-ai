# T-050-application-tracking-api

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
지원/스킵·즐겨찾기 기록 + 처리완료 정리(누락 0)를 위한 user-facing CRUD를 NestJS 소유 테이블로 구현한다(ARCH §3-2). 사용자 격리(본인 기록만). F-019 FAC-1·2·4·5 커버.

## 2. 작업 범위
- Prisma 스키마: `application_events`(api 소유 — `id, user_id, job_posting_id, action(applied|skipped|favorite|unfavorite|unskip), created_at`). 이벤트 로그 형식(상태 컬럼 대신 — GS-3 후속 분석 유리, F-019 §12).
- NestJS `ApplicationsModule`: `POST /api/v1/applications`(action 기록) + `GET /api/v1/applications`(본인 기록) + 피드 쿼리에 처리완료 제외 필터.
- 인가: 모든 조회/쓰기에 `user_id == session.user_id`(F-016 가드 재사용) — 타인 기록 접근 0.
- 처리완료 정리: 기본 피드 쿼리가 `applied`/`skipped` 공고를 제외(즐겨찾기는 별도 보존·재노출).
- schema-contract test: `application_events` 테이블 + `user_id` FK.

## 3. 구현 항목
1. Prisma migration — `application_events` 테이블 + FK + `(user_id, job_posting_id)` 인덱스. → 확인: schema-contract pytest (AC-4)
2. `ApplicationsController`/`Service` — action 기록(멱등: 동일 user×job 최신 action) + 본인 조회. → 확인: vitest (AC-1, AC-2, AC-3)
3. 피드 쿼리 확장 — 처리완료(applied/skipped) 제외 + 즐겨찾기 별도 조회. → 확인: vitest (AC-1)

## 4. 제외 항목
- 무응답/서류결과 피드백 루프 자동화 — Charter §5 비목표.
- 자동지원 — 비목표(원본 채널 링크 이동은 UI T-051).
- GS-3 실데이터 분석(상위군 통과율) — M6 배포 후 트랙.
- UI 액션 버튼·toast — T-051.

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/prisma/schema.prisma` — ApplicationEvent 모델 + User/JobPosting 역참조
- `podo/apps/api/prisma/migrations/20260607133810_add_application_events/migration.sql` (신규)
- `podo/apps/api/src/applications/applications.service.ts` · `applications.controller.ts` · `applications.module.ts` · `dto/create-application.dto.ts` (신규)
- `podo/apps/api/src/app.module.ts` — ApplicationsModule 등록
- `podo/apps/api/src/feed/feed.service.ts` — applied/skipped 공고 피드 제외 필터(즐겨찾기 유지)
- `podo/apps/api/test/applications.spec.ts` (신규)
- `ai/tests/test_schema_contract.py` — application_events 테이블·FK 검증(AC-4)
- `podo/apps/api/vitest.config.ts` — fileParallelism:false (DB 통합 테스트 직렬화 — 아래 메모)

## 5. 완료 조건
지원/스킵 공고가 본인 `user_id`로 기록되고 기본 피드에서 정리되며, 즐겨찾기는 보존되고, 타 사용자 기록에 접근 불가하다.

## 6. Acceptance Criteria
- AC-1 [Given] 인증 사용자 + 공고 [When] `POST /api/v1/applications`에 `{action:'applied'}` *또는* `{action:'skipped'}` 후 피드 조회 [Then] `application_events`에 `user_id` 포함 행이 생성되고 **applied·skipped 둘 다 해당 공고가 기본 피드 목록에서 제외된다**(처리완료 정리, 즐겨찾기는 예외).
- AC-2 [Given] `action:'favorite'` 기록 [When] `GET /api/v1/applications?filter=favorite` [Then] 점수와 무관하게 즐겨찾기 공고가 반환된다.
- AC-3 [Given] 사용자 A의 기록 [When] 사용자 B 세션으로 A의 application 조회/수정 시도 [Then] 403/404로 차단되고 A 데이터가 노출되지 않는다.
- AC-4 [Given] `prisma migrate dev` 적용 [When] schema-contract pytest [Then] `application_events` 테이블 + `user_id` FK 존재로 green이다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/api/test/applications.spec.ts::test_AC_1_applied_recorded_and_cleared_from_feed
- AC-2 → vitest::podo/apps/api/test/applications.spec.ts::test_AC_2_favorite_preserved_regardless_of_score
- AC-3 → vitest::podo/apps/api/test/applications.spec.ts::test_AC_3_cross_user_access_blocked
- AC-4 → pytest::ai/tests/test_schema_contract.py::test_AC_4_application_events_table_exists

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Feature: [F-019-application-tracking](../features/F-019-application-tracking.md)
- Architecture: [ARCH §3-2 소유권](../../20-system/ARCHITECTURE_OVERVIEW.md), [§7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1)
- ADR: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md) (user 격리)

## 8. 메모
- 이벤트 로그 형식(상태 컬럼 X) — GS-3 후속 분석에 유리(F-019 §12 결정).
- 재노출 규칙(스킵 며칠 후?)은 단순 시작(즐겨찾기 영구·스킵 unskip으로 복구).
- 구현 결정(implement): 멱등 = `(user_id, job_posting_id)` 복합 unique upsert(동일 user×job 최신 action 1행). 피드 제외 = 최신 action이 applied/skipped인 공고만(favorite/unfavorite/unskip 비제외). 격리 = deleteAction이 event.user_id≠요청자면 403, getActions는 본인 user_id 범위.
- 구현 결정(implement) — **vitest fileParallelism:false 추가**: applications.spec가 now()-dated ranking_run을 만들면서, 파일 병렬 실행 시 feed.spec의 *글로벌* getFeed(-1)(no userId)가 그 run을 전역 최신으로 집어 충돌(플레이키). DB 통합 테스트가 단일 Postgres 공유 → 파일 직렬화로 격리(일반적 올바른 처리). feed.spec 로직 불변(글로벌 경로 커버 유지). 본 변경은 T-050 applications.spec 도입이 노출한 잠재 레이스의 근본 수정.
- 검증(implement): api vitest 35 pass(podo_test, 직렬) · schema-contract 3 pass(AC-4 포함) · `pnpm validate` green.

## 9. 의존성
- depends_on: [T-042]
- read_set: ["podo/apps/api/src/feed/", "podo/apps/api/src/auth/"]
- write_set: ["podo/apps/api/prisma/schema.prisma", "podo/apps/api/prisma/migrations/**", "podo/apps/api/src/applications/", "podo/apps/api/src/feed/", "podo/apps/api/test/applications.spec.ts", "ai/tests/test_schema_contract.py"]
- assumptions: ["T-042 인증 가드·user_id 격리 존재"]
- verifier: "pnpm --filter @podo/api test applications && uv run pytest ai/tests/test_schema_contract.py"
