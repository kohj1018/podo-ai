# T-093-mypage-and-global-nav

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
로그인 사용자용 **마이페이지(계정 허브)**와 **전역 네비**를 추가해, 주소창으로만 가던 /resume 등으로 도달 가능하게 한다(F-029).

## 2. 작업 범위
프론트만 — /me 라우트 + AppHeader 네비. 계정 설정 편집 제외.

## 3. 구현 항목
1. 신규 `podo/apps/web/app/me/page.tsx` — 현재: 없음 → 변경: `<AuthGate>` + 허브 링크 목록(이력서 수정→`/resume`, 즐겨찾기→`/favorites`, 지원기록→`/applications`, 로그아웃=LogoutButton). 단일 컬럼(maxWidth 430). → 확인: 허브 진입 렌더 (AC-1, AC-3).
2. `podo/apps/web/components/AppHeader.tsx:13-42` — 현재: 로고 + `LogoutButton`만 → 변경: 로고와 우측 사이에 **마이페이지 진입 링크**(`/me`, 아이콘/텍스트) 추가. 기존 `status !== 'authed'` 가드 유지. → 확인: 인증 시 네비 노출 (AC-2).
3. 네비 a11y — `aria-current`/링크 시맨틱, 키보드 도달. → 확인 (AC-2).

## 4. 제외 항목
- 활동 뷰 자체 구현(T-094) — 본 task는 *링크 진입*만.
- 프로필/계정 설정 편집.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/app/me/page.tsx` (신규 — 계정 허브: 이력서수정/즐겨찾기/지원기록/로그아웃 진입)
- `podo/apps/web/components/AppHeader.tsx` (마이페이지 /me 네비 링크 + nav 시맨틱, 로고 anchor화)
- `podo/apps/web/test/mypage.spec.tsx` (신규 — AC-1/AC-3)
- `podo/apps/web/test/app_header_nav.spec.tsx` (신규 — AC-2 + guest 숨김)

## 5. 완료 조건
헤더 네비로 마이페이지에 가고, 마이페이지에서 이력서 수정·즐겨찾기·지원기록·로그아웃에 진입한다.

## 6. Acceptance Criteria
- AC-1 [Given] 로그인 사용자 [When] `/me` 진입 [Then] 이력서 수정·즐겨찾기·지원기록·로그아웃 진입 항목을 표시한다.
- AC-2 [Given] 로그인 사용자 [When] 어느 화면이든 [Then] AppHeader에 마이페이지 진입 네비가 노출되고 키보드로 도달 가능하다.
- AC-3 [Given] `/me` [When] "이력서 수정" 클릭 [Then] `/resume`로 이동한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/mypage.spec.tsx > test_AC_1_hub_links
- AC-2 → podo/apps/web/test/app_header_nav.spec.tsx > test_AC_2_nav_visible_authed
- AC-3 → podo/apps/web/test/mypage.spec.tsx > test_AC_3_resume_edit_link

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-029-account-and-navigation](../features/F-029-account-and-navigation.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)

## 8. 메모
- 해석 확정: 라우트 구조 = 별 라우트(`/me`·`/favorites`·`/applications`). /me는 허브, 활동 뷰는 별 라우트(F-029 §12 결정).

## 9. 의존성
- depends_on: []
- write_set: ["podo/apps/web/app/me/page.tsx", "podo/apps/web/components/AppHeader.tsx"]
