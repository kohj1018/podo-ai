# T-094-activity-views

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
액션만 있고 회수 화면이 없던 **즐겨찾기·지원기록 목록 뷰**를 기존 API(`GET /api/v1/applications?filter=`)로 붙인다(F-029, 순수 프론트).

## 2. 작업 범위
프론트 뷰 2종 + 공용 ActivityList. 필요한 경우 applications API에 공고 상세 include(최소).

## 3. 구현 항목
1. 신규 `podo/apps/web/components/ActivityList.tsx` — 현재: 없음 → 변경: prop `filter: 'favorite'|'applied'`로 `GET /api/v1/applications?filter=${filter}`(credentials:'include') fetch → 항목 목록 렌더(회사·직무·링크). 빈/로딩/에러 상태(삼키지 않음). → 확인 (AC-1, AC-2, AC-3).
2. 신규 `podo/apps/web/app/favorites/page.tsx` · `podo/apps/web/app/applications/page.tsx` — 현재: 없음 → 변경: `<AuthGate>` + `<ActivityList filter="favorite|applied" />`. → 확인: 라우트 렌더 (AC-1, AC-2).
3. (필요 시) `podo/apps/api/src/applications/applications.service.ts` `getActions` — 현재: `ApplicationEventRow[]`(job_posting_id만) → 변경: 표시용 `job_posting`(company/title/url) include. 7-1 envelope 무변경. → 확인: 목록에 공고 정보 (AC-1).

## 4. 제외 항목
- 지원 스테이지(서류/면접) 트래킹·편집.
- 마이페이지 허브/네비(T-093).

## 4-1. 변경 예정 파일/경로

## 5. 완료 조건
즐겨찾기·지원기록 뷰가 실 API 목록을 빈/로딩/에러 처리와 함께 렌더한다.

## 6. Acceptance Criteria
- AC-1 [Given] 즐겨찾기한 공고가 있는 사용자 [When] `/favorites` 진입 [Then] `?filter=favorite` 목록이 공고 정보와 함께 렌더된다.
- AC-2 [Given] 지원 기록이 있는 사용자 [When] `/applications` 진입 [Then] `?filter=applied` 목록이 렌더된다.
- AC-3 [Given] 활동 0건 또는 fetch 실패 [When] 뷰 진입 [Then] 빈 상태(포도 톤) 또는 에러 상태를 표시한다(빈 목록으로 삼키지 않음).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/activity_views.spec.tsx > test_AC_1_favorites_list
- AC-1(API shape) → podo/apps/api/test/applications.spec.ts > test_getActions_includes_posting_company_title_url (mock 뒤 가려지는 response shape 회귀 차단 — repair-plan P2)
- AC-2 → podo/apps/web/test/activity_views.spec.tsx > test_AC_2_applications_list
- AC-3 → podo/apps/web/test/activity_views.spec.tsx > test_AC_3_empty_and_error

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-029-account-and-navigation](../features/F-029-account-and-navigation.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) · [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)

## 8. 메모
- 해석 확정: AC-1 표시 정보 = `getActions`에 `job_posting`(company/title/url) include 추가(현재 job_posting_id만이라 공고명 표시 불가). API 변경은 include 1개로 한정, envelope·격리 불변.

## 9. 의존성
- depends_on: []
- write_set: ["podo/apps/web/components/ActivityList.tsx", "podo/apps/web/app/favorites/page.tsx", "podo/apps/web/app/applications/page.tsx", "podo/apps/api/src/applications/applications.service.ts"]
