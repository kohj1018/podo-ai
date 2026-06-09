# T-090-deadline-section-and-feed-ia

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
피드를 피로 최소 IA(M7 §2-A-1)로 재구성한다: 마감 임박 전용 섹션 신설 + 세로 순서(greeting→커버리지 strip→탭→마감→추천→coarse) + 커버리지 compact strip.

## 2. 작업 범위
프론트(`podo/apps/web`)만 — 피드 합성·신규 DeadlineSection·CoveragePanel compact. closing_at 데이터 생산(크롤러)·검색/정렬 제외.

## 3. 구현 항목
1. `podo/apps/web/components/CoveragePanel.tsx` — 현재: 풀 패널 상시 노출 → 변경: 기본 **compact 1줄 strip**("📡 N개 채널 수집 중 · 마지막 HH:MM") + 펼침 토글(`aria-expanded`)로 기존 채널 상세. **degraded(수집 실패)면 자동 펼침 + 경고 유지**(Fail#3). → 확인: 기본 1줄, 클릭 시 상세, degraded 시 경고 (AC-3).
2. 신규 `podo/apps/web/components/DeadlineSection.tsx` — 현재: 없음 → 변경: props `items: FeedItem[]`를 받아 `posting.closing_at` 임박(D-day ≤ 7) 공고를 **상위 3~5 캡**으로 별 섹션 렌더(회사/직무 + DeadlineRow, 배지 없음). 임박 0이면 `return null`(빈 헤더 금지). `<section aria-label="마감 임박">`. → 확인: 임박 있으면 섹션, 없으면 미렌더 (AC-1).
3. `podo/apps/web/components/FeedList.tsx:77-118` — 현재: `items`(state 소유)를 단일 `ArrivalList`로 렌더 → 변경: 메인 리스트 **위에 `<DeadlineSection items={items} />`** 삽입(closing_at 임박 분리). **items를 소유한 FeedList에서 렌더**(FeedView는 items 미소유 — 리뷰 P1-1 회수). `JobCard`가 이미 `daysUntil(posting.closing_at)` 사용(JobCard.tsx:50)하므로 동일 파생 재사용. → 확인: 마감 섹션이 추천 리스트 위 (AC-1, AC-2).
4. DOM 순서(자연 중첩 — 이동 불필요) — `app/page.tsx`(CoveragePanel compact → DomainTabBar → FeedView) + `FeedView`(GreetingCard → FeedList[DeadlineSection → 리스트])로 **커버리지 strip → 직군 탭 → greeting → 마감 임박 → 추천** 순서 확보. CoveragePanel만 compact화(1번), GreetingCard/탭 이동 없음. → 확인: DOM 순서 (AC-2).

## 4. 제외 항목
- `closing_at` 크롤러 수집(데이터 생산) — M7 §7 결정(이연 권장). 데이터 없으면 마감 섹션은 빈.
- `?section=expiring` 백엔드 신규 쿼리 — 본 task는 추천 items의 closing_at *클라 필터*로 시작.
- CoarseSection 마운트(T-091) · 검색/정렬.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/components/DeadlineSection.tsx` (신규 — 마감 임박 섹션, DeadlineRow 재사용)
- `podo/apps/web/components/FeedList.tsx` (DeadlineSection을 ArrivalList 위에 삽입)
- `podo/apps/web/components/CoveragePanel.tsx` (compact 1줄 strip + 펼침 토글, degraded 자동 펼침)
- `podo/apps/web/test/deadline_section.spec.tsx` (신규 — AC-1)
- `podo/apps/web/test/feed_ia.spec.tsx` (신규 — AC-2 세로 순서, HomePage 통합)
- `podo/apps/web/test/coverage_compact.spec.tsx` (신규 — AC-3)
- `podo/apps/web/test/evidence_coverage.spec.tsx` (compact strip 동작에 맞춰 토글 후 상세 단언으로 갱신)

## 5. 완료 조건
마감 임박 공고가 추천과 분리된 섹션으로 위에 뜨고(데이터 시), 커버리지가 compact strip이며, 피드 세로 순서가 IA를 따른다.

## 6. Acceptance Criteria
- AC-1 [Given] `closing_at`이 7일 내인 추천 공고가 있을 때 [When] 피드 진입 [Then] 마감 임박 섹션이 추천 위에 별도로 렌더되고, 임박 공고가 0이면 섹션 DOM이 렌더되지 않는다.
- AC-2 [Given] 피드 ready [When] 렌더 [Then] 세로 순서가 커버리지 strip → (직군 탭) → greeting → 마감 임박 → 추천 순서로 나타난다.
- AC-3 [Given] 피드 진입 [When] 기본 상태 [Then] 커버리지가 1줄 compact strip으로 표시되고 펼침 토글 시 채널 상세를 보여준다(degraded면 자동 경고).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/deadline_section.spec.tsx > test_AC_1_expiring_section_renders_or_hidden
- AC-2 → podo/apps/web/test/feed_ia.spec.tsx > test_AC_2_feed_vertical_order
- AC-3 → podo/apps/web/test/coverage_compact.spec.tsx > test_AC_3_compact_strip_and_expand

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-028-feed-section-completion](../features/F-028-feed-section-completion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components) · [## 2 Colors](../../20-system/DESIGN.md#design-2-colors)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md)

## 8. 메모
- 해석 확정: AC-1 마감 임박 데이터원 = *FeedList items의 posting.closing_at 클라 필터*(백엔드 신규 쿼리 미도입). closing_at 전부 null이면 섹션 항상 숨김(정직) — closing_at 크롤러 수집은 §7 이연.
- repair-plan 2026-06-10 [default] P1 Plan-ambiguity: Adopt-modified — items는 FeedList가 소유(FeedView 미소유) → DeadlineSection을 FeedList에서 렌더(리뷰어 3안 중 'FeedList 내부' 채택). IA 순서는 컴포넌트 중첩에 맞춰 커버리지strip→탭→greeting→마감→추천으로 확정(GreetingCard 이동 회피).

## 9. 의존성
- depends_on: []
- write_set: ["podo/apps/web/components/DeadlineSection.tsx", "podo/apps/web/components/FeedList.tsx", "podo/apps/web/components/CoveragePanel.tsx"]
- assumptions: ["feed 응답의 posting에 closing_at 필드 pass-through(JobPosting.closing_at 존재 — JobCard.tsx:50 이미 사용)"]
- 비고: `FeedList.tsx`를 T-092와 공유 → 순차.
