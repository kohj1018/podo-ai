# T-092-recent-unprocessed-resurface

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
신규 적은 날 EmptyState의 *문구뿐인* "최근 7일 미처리 공고를 다시 볼 수 있어요"(FeedView.tsx:163)를 실제 **재노출 액션**으로 만든다(Charter Alt#4).

## 2. 작업 범위
프론트 액션 + feed 재노출 쿼리(최소 백엔드 파라미터). 검색/정렬 제외.

## 3. 구현 항목
1. `podo/apps/web/components/FeedView.tsx:156-165` — 현재: empty 분기가 "최근 7일 미처리…" 문구만 → 변경: 그 아래 `<button>` "최근 7일 미처리 다시 보기" 추가 → 클릭 시 재노출 모드 state로 전환해 `<FeedList resurface />` 렌더. → 확인: 버튼 노출·클릭 동작 (AC-1, AC-2).
2. `podo/apps/web/components/FeedList.tsx:28-56` — 현재: `GET /api/v1/feed?cursor=` → 변경: `resurface` prop 시 `&include_recent_processed=7d` 부착. → 확인: 재노출 fetch (AC-2).
3. `podo/apps/api/src/feed/feed.service.ts:167-176` (getFeed) — 현재: `CLEARED_ACTIONS` 공고를 항상 제외 → 변경: `includeRecentProcessed` 인자 시 최근 7일 내 처리분은 제외하지 않음(`created_at >= now-7d` 처리 이벤트는 노출). → 확인: 재노출 시 미처리+최근처리 반환 (AC-2).
4. `podo/apps/api/src/feed/feed.controller.ts:24-36` — 현재: `?cursor&section&domain` → 변경: `?include_recent_processed` 쿼리 추가 → service 전달. → 확인 (AC-2).

## 4. 제외 항목
- "7일" 외 기간 선택 UI. 마감 섹션·coarse(T-090/091).

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/src/feed/feed.service.ts` (getFeed에 includeRecentProcessed 인자 + 7일 컷오프)
- `podo/apps/api/src/feed/feed.controller.ts` (include_recent_processed 쿼리 → service 전달)
- `podo/apps/web/components/FeedList.tsx` (resurface prop → &include_recent_processed=7d)
- `podo/apps/web/components/FeedView.tsx` (empty-state 재노출 버튼 + resurface state)
- `podo/apps/api/test/feed.spec.ts` (fake-prisma AC-2 단위 테스트 추가)
- `podo/apps/web/test/feed_resurface.spec.tsx` (신규 — AC-1)

## 5. 완료 조건
신규 적은 날 EmptyState에서 버튼을 누르면 최근 7일 미처리(+최근 처리분) 공고가 피드에 재노출된다.

## 6. Acceptance Criteria
- AC-1 [Given] visible 0 + 신규 적은 날(new_count 0) [When] EmptyState 렌더 [Then] "최근 7일 미처리 다시 보기" 액션 버튼이 노출된다.
- AC-2 [Given] 재노출 버튼 클릭 [When] feed 재요청 [Then] `include_recent_processed=7d`로 최근 7일 내 공고(미처리 포함)가 피드에 재노출된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/feed_resurface.spec.tsx > test_AC_1_resurface_button_visible
- AC-2 → podo/apps/api/test/feed.spec.ts > test_AC_2_include_recent_processed

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-028-feed-section-completion](../features/F-028-feed-section-completion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) · [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: —

## 8. 메모
- 해석 확정: AC-2 "최근 7일 미처리" = feed에 `include_recent_processed=7d` 파라미터를 추가해 최근 7일 내 처리(applied/skipped) 공고의 제외를 해제(미처리는 본래 노출). API 변경은 getFeed 인자 1개 + 컨트롤러 쿼리 1개로 한정(7-1 envelope 무변경).

## 9. 의존성
- depends_on: [T-090]
- write_set: ["podo/apps/web/components/FeedView.tsx", "podo/apps/web/components/FeedList.tsx", "podo/apps/api/src/feed/feed.service.ts", "podo/apps/api/src/feed/feed.controller.ts"]
- 비고: `FeedView.tsx`를 T-090과 공유 → 순차.
