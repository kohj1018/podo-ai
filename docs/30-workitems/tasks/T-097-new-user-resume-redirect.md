# T-097-new-user-resume-redirect

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
회원가입/최초 로그인 후 **이력서가 없으면 피드 인라인 온보딩 대신 /resume로 직행**시킨다(사용자 결정 §2-B).

## 2. 작업 범위
프론트 리다이렉트 가드 + 온보딩 카피 정리. 알림 제외.

## 3. 구현 항목
1. `podo/apps/web/app/page.tsx:27-44` — 현재: `feed/meta`를 fetch해 `resume_domains`만 사용 → 변경: 같은 응답의 `has_resume`가 false면 `router.replace('/resume')`(client). loading 동안 placeholder(깜빡임 최소). → 확인: 이력서 없으면 /resume (AC-1).
2. `podo/apps/web/components/FeedView.tsx:101-104` — 현재: `!has_resume`면 `<Onboarding/>` 인라인 → 변경: page 레벨 리다이렉트가 우선이므로 FeedView no-resume 분기는 fallback로 축소(또는 유지하되 도달 안 함). → 확인: 이력서 있는 사용자 피드 정상 (AC-2).
3. 루프 방지 — 변경: /resume에는 본 리다이렉트 판정을 두지 않음(이미 그 페이지). → 확인: 무한 루프 0 (AC-1).

## 4. 제외 항목
- 다단계 온보딩 튜토리얼·코치마크.
- 로그인 콜백 서버 리다이렉트(교차도메인 — client 가드로 처리).

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/app/page.tsx` (has_resume false → router.replace('/resume') + redirecting placeholder, 루프 방지)
- `podo/apps/web/components/FeedView.tsx` (no-resume Onboarding 분기를 fallback로 명시 — 주석)
- `podo/apps/web/test/new_user_redirect.spec.tsx` (신규 — AC-1/AC-2)

## 5. 완료 조건
이력서 없는 인증 사용자가 진입 즉시 /resume로 안내되고, 이력서 있는 사용자는 피드를 정상적으로 본다.

## 6. Acceptance Criteria
- AC-1 [Given] 인증됐으나 이력서 없는 사용자 [When] `/` 진입 [Then] `/resume`로 리다이렉트되며 리다이렉트 루프가 발생하지 않는다.
- AC-2 [Given] 이력서 있는 인증 사용자 [When] `/` 진입 [Then] 리다이렉트 없이 피드가 렌더된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/new_user_redirect.spec.tsx > test_AC_1_no_resume_redirects
- AC-2 → podo/apps/web/test/new_user_redirect.spec.tsx > test_AC_2_with_resume_feed

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-031-onboarding-and-loading-ux](../features/F-031-onboarding-and-loading-ux.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)

## 8. 메모
- 해석 확정: 리다이렉트 위치 = 피드 page client 가드(`has_resume` 기반, feed/meta 재사용). 교차도메인이라 SSR 리다이렉트 불가(SessionProvider 패턴 정합).

## 9. 의존성
- depends_on: []
- write_set: ["podo/apps/web/app/page.tsx", "podo/apps/web/components/FeedView.tsx"]
- 비고: page.tsx/FeedView.tsx를 T-090/091/092와 공유 → 순차 또는 별 worktree.
