# T-046-greeting-card-feed-states

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
피드 진입점 경험을 완성한다: **GreetingCard**(포도 인사 + 오늘의 신규/마감 카운트) + **8-상태 매트릭스**(DESIGN.md §7-4: loading skeleton·error·empty·보류·이력서 없음·분석 중·신규 있음·전부 처리완료)를 일급으로 구현한다. M2 REV-M2-UI-001(error/empty 미처리) 부채 회수. F-016(세션) + F-017(채점 상태) 선행 필요.

## 2. 작업 범위
- `GreetingCard` 컴포넌트: 포도 PNG(마스코트) + "포도가 오늘의 자리를 골라왔어요!" + 신규 N건 / 마감 임박 M건 카운트. DESIGN §7 인벤토리 등록.
- 피드 페이지(`/` — App Router) **8-상태 분기**:
  1. `loading` — skeleton 카드 + `aria-busy=true` + ring indeterminate.
  2. `error` — 포도 + "아침 배달이 늦어요" + 재시도 버튼 + `role=alert`.
  3. `empty(신규 없음)` — "오늘은 신규가 적어요" + 최근 7일 미처리 재노출.
  4. `pending(보류)` — 전 공고 보류(무키/키 미보유). PendingState(dashed 카드 + 정직 메시지 + 원문 링크).
  5. `no-resume` — 이력서 없음 → 온보딩 안내(업로드 경로).
  6. `scoring(분석 중)` — 채점 진행 중. skeleton + ring indeterminate + "포도가 공고를 분석하고 있어요".
  7. `ready` — 정상 피드 (T-047 JobCard 연결).
  8. `all-processed` — 처리완료 정리 완료(F-019 연결). "오늘 처리할 공고를 다 봤어요"(포도).
- `diff_status` 읽어 신규/마감 섹션 분리 렌더(GreetingCard 카운트 포함).
- NestJS 피드 API에 `scoring_status`(job 상태) + `diff_summary`(신규/마감 수) 응답 추가.
- CoveragePanel 상시 노출(수집 실패 시 danger 표시 — Fail #3 차단).

## 3. 구현 항목
1. `podo/apps/api/src/feed/feed.service.ts` — 현재: recommendations만 반환 → 변경: (a) 사용자 활성 이력서의 최신 scoring_job 상태 조회; (b) `diff_summary: { new_count, expiring_count }`(diff_status='new'/'expiring' 집계); (c) 응답에 `scoring_status(queued/running/done/failed|null)·diff_summary·total_pending_count` 추가. → 확인: AC-3 응답 포함. (AC-3)
2. `podo/apps/web/components/GreetingCard.tsx` (신규, `'use client'`) — 포도 PNG + 제목 + `diff_summary`로 "신규 N건 / 마감 임박 M건" 렌더. `role=region aria-label="오늘의 요약"`. DESIGN §2 토큰만(raw hex 금지). → 확인: AC-1 렌더. (AC-1)
3. `podo/apps/web/app/page.tsx` (피드) — 현재: 단순 FeedList → 변경: `scoring_status·diff_summary` 포함 API 응답으로 8-상태 분기:
   - `no-resume`: `<OnboardingGuide />` — "이력서를 업로드해 포도와 시작해요" + `/resume` 링크.
   - `scoring(queued/running)`: skeleton 카드 + "포도가 공고를 분석하고 있어요" + `aria-busy=true`.
   - `error`: `<ErrorState />` — 포도 + 재시도 + `role=alert`.
   - `empty`: `<EmptyState />` — 포도 + 최근 7일 미처리 재노출.
   - `pending`: `<PendingFeedState />` — 전 공고 dashed 카드 + 정직 메시지.
   - `all-processed`: `<AllProcessedState />` — "오늘 처리할 공고를 다 봤어요".
   - `ready`: `<GreetingCard />` + `<FeedList />` (JobCard는 T-047).
   → 확인: 각 상태 렌더 테스트. (AC-1, AC-2)
4. `podo/apps/web/components/CoveragePanel.tsx` — 현재: 존재 여부 불명 → 변경: 상시 렌더(피드 하단). coverage_degraded=true 시 `role=alert` + danger 색 + "수집 실패 — 일부 공고가 누락될 수 있어요". → 확인: AC-2 danger 표시. (AC-2)
5. `docs/20-system/DESIGN.md` §7 — GreetingCard·CoveragePanel·ErrorState·EmptyState·PendingState는 **이미 §7 등록됨** → **신규는 OnboardingGuide만 추가**(누락분만, scope 최소). → 확인: OnboardingGuide 항목 존재. (등록 완결)
6. `podo/apps/web/test/feed_states.spec.tsx` (신규) — AC-1(GreetingCard 카운트), AC-2(8-상태 각 분기 렌더), AC-3(scoring_status→loading/skeleton). → 확인: `pnpm --filter web test` green. (AC-1, AC-2, AC-3)

## 4. 제외 항목
- JobCard 세부(배지·근거 펼침 — T-047). · lottie 모션(T-048). · 접근성 심화 단언(T-049). · 지원/스킵 버튼(T-050/T-051). · 커서 페이지네이션·가상화.

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/src/feed/feed.service.ts` — getFeedMeta(scoring_status·diff_summary·total_pending_count·visible_count·has_resume)
- `podo/apps/api/src/feed/feed.controller.ts` — GET /api/v1/feed/meta
- `podo/apps/api/src/coverage/coverage.service.ts` — Coverage.degraded 추가
- `podo/apps/web/components/GreetingCard.tsx` (신규)
- `podo/apps/web/components/OnboardingGuide.tsx` (신규)
- `podo/apps/web/components/FeedView.tsx` (신규 — 8-상태 오케스트레이터)
- `podo/apps/web/components/CoveragePanel.tsx` — degraded → danger + role=alert
- `podo/apps/web/app/page.tsx` — CoveragePanel + FeedView
- `podo/apps/web/test/feed_states.spec.tsx` (신규)
- `docs/20-system/DESIGN.md` §7 — OnboardingGuide 등록

## 5. 완료 조건
피드 진입 시 8-상태(loading/error/empty/pending/no-resume/scoring/ready/all-processed)가 각각 올바르게 렌더되고, GreetingCard가 신규/마감 카운트를 표시한다. CoveragePanel이 상시 노출되며 수집 실패 시 danger를 표시한다.

## 6. Acceptance Criteria
- AC-1 [Given] 세션 있는 사용자·done 채점·신규 공고 3건 [When] 피드 진입 [Then] GreetingCard에 "신규 3건"이 표시되고 `role=region` aria 속성이 있다.
- AC-2 [Given] 수집 실패(coverage_degraded=true) [When] 피드 렌더 [Then] CoveragePanel이 danger 스타일 + `role=alert`로 "수집 실패" 메시지를 표시하고 가짜 "전부 수집" 인상을 주지 않는다.
- AC-3 [Given] scoring_status='running' [When] 피드 진입 [Then] skeleton 카드 + `aria-busy=true` + "포도가 공고를 분석하고 있어요" 텍스트가 렌더되고 실제 점수가 표시되지 않는다.
- AC-4 [Given] 신규 공고 0건(empty) / 피드 API 오류(error) [When] 피드 렌더 [Then] empty는 EmptyState("오늘은 신규가 적어요" 포도 + 최근 7일 재노출), error는 ErrorState(`role=alert` + 재시도)가 DESIGN §7-4 매트릭스대로 렌더된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/feed_states.spec.tsx::test_AC_1_greeting_card_shows_new_count_with_region_role
- AC-2 → vitest::podo/apps/web/test/feed_states.spec.tsx::test_AC_2_coverage_panel_danger_on_degraded
- AC-3 → vitest::podo/apps/web/test/feed_states.spec.tsx::test_AC_3_scoring_running_shows_skeleton_no_score
- AC-4 → vitest::podo/apps/web/test/feed_states.spec.tsx::test_AC_4_empty_and_error_states

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Feature: [F-018-companion-feed-experience](../features/F-018-companion-feed-experience.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4), [## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components), [## 7-4 8-State Matrix](../../20-system/DESIGN.md), [## 2 Colors](../../20-system/DESIGN.md#design-2-colors)
- ADR: [ADR-049](../../90-decisions/boilerplate/ADR-049-concept-mockup-first-design.md) · [ADR-042](../../90-decisions/boilerplate/ADR-042-ux-flow-quality.md)

## 8. 메모
- "신규/마감 diff" 데이터: crawler가 set하는 `diff_status` 컬럼 읽기. M4 E2E는 수동/로컬 크롤 1회로 diff_status 시드(cron 실가동은 M6).
- 8-상태 분기는 클라이언트 상태(scoring_status·데이터 존재 여부)로 결정. 서버 컴포넌트 shell + client island 패턴.
- CoveragePanel: coverage API(M2 F-010)의 `degraded` 필드 읽어 danger 표시. 항상 노출(숨김 금지 — Fail #3).
- 구현 결정(implement) — **별도 meta 엔드포인트**: scoring_status·diff_summary는 getFeed(커서 페이지네이션) 응답이 아니라 `GET /api/v1/feed/meta`(1회)로 분리 — getFeed 시그니처/기존 api feed.spec 불변(저위험). FeedView가 meta로 8-상태 결정, ready/pending에서 기존 FeedList(items)에 위임(중복 없음).
- 구현 결정(implement) — **상태 컴포넌트 inline + GreetingCard/OnboardingGuide 컴포넌트화**: ErrorState/EmptyState/AllProcessed/Scoring은 FeedView 내 inline 분기(testid/role/문구). 신규 design 컴포넌트 = GreetingCard·OnboardingGuide·FeedView. DESIGN §7에 OnboardingGuide만 신규 등록(GreetingCard·CoveragePanel·EmptyState·PendingState·ErrorState·LoadingState는 기존 등록).
- 구현 결정(implement) — **role=region은 암묵 role 사용**: biome a11y(useSemanticElements/noRedundantRoles)가 `<section role="region">`를 redundant로 차단 → section+aria-label(암묵 region)로 두고 테스트는 getByRole('region',{name})로 단언. AC "role=region aria 속성" 충족(접근성 트리 기준).
- 검증(implement): web vitest feed_states 5 pass + 기존 web 회귀 0 · api vitest 35 pass(podo_test) · `pnpm validate` green.

## 9. 의존성
- depends_on: [T-042, T-044]
- read_set: ["docs/20-system/DESIGN.md", "podo/apps/web/app/page.tsx", "podo/apps/api/src/feed/feed.service.ts", "podo/apps/api/src/coverage/**"]
- write_set: ["podo/apps/api/src/feed/feed.service.ts", "podo/apps/web/components/GreetingCard.tsx", "podo/apps/web/components/CoveragePanel.tsx", "podo/apps/web/app/page.tsx", "podo/apps/web/test/feed_states.spec.tsx", "docs/20-system/DESIGN.md"]
- assumptions: ["T-042 SessionGuard + user_id 범위 피드 쿼리 존재", "T-044 scoring_jobs 테이블 + job 상태 존재", "DESIGN §7-4 8-상태 매트릭스 문서화됨"]
- verifier: "pnpm --filter @podo/web test && pnpm --filter @podo/api test"
