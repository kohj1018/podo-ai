# T-043-login-ui-protected-routes

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
Next.js 로그인 화면(`/login`)과 보호 라우트 SSR 가드를 만든다. 비로그인 사용자가 피드·업로드 등 보호 라우트에 진입하면 `/login`으로 리다이렉트되고, 로그인 화면에서 GitHub/Google 버튼을 누르면 OAuth 플로우가 시작된다. DESIGN.md 토큰 준수 + 포도 동반자 톤("포도와 함께 시작해요") + 접근성. T-042(AuthModule)가 선행.

## 2. 작업 범위
- Next.js `/login` 페이지: GitHub/Google 로그인 버튼(DESIGN §7 Button 재사용) + 포도 환영 톤 헤딩·설명.
- SSR 가드: `middleware.ts`(App Router) — 쿠키 세션 없으면 보호 라우트 → `/login` 리다이렉트.
- 로그아웃 버튼(레이아웃 헤더) + `POST /auth/logout` 호출 → 세션 무효 → `/login` 리다이렉트.
- OAuth 에러 콜백 처리: query param `error=...` 있으면 로그인 화면에 "로그인에 실패했어요. 다시 시도해주세요." 표시.
- DESIGN.md §2 토큰만(raw hex 금지) + Button.primary/secondary 재사용(primitive 신설 없음).

## 3. 구현 항목
1. `podo/apps/web/app/login/page.tsx` — 현재: 없음 → 변경: 서버 컴포넌트. 세션 쿠키 이미 유효하면 `/`로 redirect(이미 로그인). 아니면 `LoginButtons` 클라이언트 컴포넌트 렌더. 제목: "포도와 함께 시작해요", 부제: "오늘의 맞춤 공고를 골라드릴게요". → 확인: `/login` 진입 시 버튼 렌더. (AC-1)
2. `podo/apps/web/components/LoginButtons.tsx`(`'use client'`) — 현재: 없음 → 변경: "GitHub으로 시작" + "Google로 시작" Button.primary. 각 버튼 href = `/auth/github` / `/auth/google`(NestJS api 경유). 클릭 시 버튼 spinner/disabled(가짜 진입 금지). `error` query param 있으면 "로그인에 실패했어요. 다시 시도해주세요." alert 렌더. provider 버튼 `aria-label` 명시. → 확인: AC-1 버튼 aria-label, AC-2 error 메시지 렌더. (AC-1, AC-2)
3. `podo/apps/web/middleware.ts` — 현재: 없음(또는 미보호) → 변경: `matcher: ['/', '/resume', '/feed']`. 쿠키 `session`(또는 `connect.sid`) 없으면 `NextResponse.redirect('/login')`. → 확인: 비인증 `GET /` → `/login` redirect. (AC-3)
4. 레이아웃 헤더(`podo/apps/web/app/layout.tsx` 또는 `Header.tsx`) — 현재: 로그아웃 버튼 없음 → 변경: 세션 존재 시 사용자 아바타 + "로그아웃" 버튼. 클릭 → `POST /auth/logout`(api) → `/login` redirect. → 확인: 로그아웃 후 세션 무효 + 리다이렉트. (AC-3)
5. `podo/apps/web/test/login.spec.tsx` (신규) — AC-1(버튼 렌더·aria-label), AC-2(error 메시지), AC-3(middleware redirect 단위 테스트). → 확인: `pnpm --filter @podo/web test` green. (AC-1, AC-2, AC-3)

## 4. 제외 항목
- OAuth provider 실 redirect(로컬 callback — T-042 담당). · 로그인 성공 후 피드 렌더(F-018 담당). · 비밀번호·이메일 인증. · 계정 삭제·설정 화면.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/app/login/page.tsx` (신규 — 서버 컴포넌트, 세션 있으면 / redirect)
- `podo/apps/web/components/LoginButtons.tsx` (신규 — GitHub/Google, error prop)
- `podo/apps/web/components/LogoutButton.tsx` (신규 — 헤더 로그아웃, layout에서 사용)
- `podo/apps/web/middleware.ts` (신규 — matcher ['/','/resume','/feed'], connect.sid 없으면 /login)
- `podo/apps/web/app/layout.tsx` — 세션 시 헤더 + LogoutButton 노출
- `podo/apps/web/test/login.spec.tsx` (신규)

## 5. 완료 조건
비로그인 사용자가 보호 라우트 접근 시 `/login`으로 리다이렉트되고, 로그인 화면에서 GitHub/Google 버튼으로 OAuth 플로우를 시작할 수 있다. OAuth 에러 시 친절한 에러 메시지를 표시한다. 로그아웃 버튼으로 세션을 무효화할 수 있다.

## 6. Acceptance Criteria
- AC-1 [Given] `/login` 진입 [When] 렌더 [Then] "GitHub으로 시작"·"Google로 시작" 버튼이 각각 `aria-label`과 함께 렌더되고 raw hex 없이 DESIGN §2 토큰만 사용된다.
- AC-2 [Given] OAuth 실패 후 `/login?error=access_denied` 진입 [When] 렌더 [Then] "로그인에 실패했어요. 다시 시도해주세요." 메시지가 표시되고 재시도 버튼이 활성이다.
- AC-3 [Given] 세션 쿠키 없는 상태 [When] `GET /`(피드) 요청 [Then] `middleware.ts`가 `/login`으로 리다이렉트한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/login.spec.tsx::test_AC_1_login_buttons_render_with_aria_label_no_hex
- AC-2 → vitest::podo/apps/web/test/login.spec.tsx::test_AC_2_error_query_param_shows_retry_message
- AC-3 → vitest::podo/apps/web/test/login.spec.tsx::test_AC_3_middleware_redirects_unauthenticated_to_login

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Feature: [F-016-oauth-multiuser](../features/F-016-oauth-multiuser.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components), [## 2 Colors](../../20-system/DESIGN.md#design-2-colors)
- ADR: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md) · [ADR-042](../../90-decisions/boilerplate/ADR-042-ux-flow-quality.md)

## 8. 메모
- 포도 톤: "포도와 함께 시작해요" 헤딩 — copy는 간결·친근. 보안 에러 메시지는 사실 명확("로그인에 실패했어요").
- middleware는 `connect.sid` 쿠키 이름을 T-042 express-session 설정과 맞춰야 함(열린 질문 — 구현 시 확인).
- 세션 유효 판단: SSR에서 쿠키 존재 체크 → api 세션 검증 없이(쿠키 유무로 1차 판단, api에서 최종 401). 구현 단순화.
- 구현 결정(implement): **Button primitive 미존재**(DESIGN §7 등록되었으나 코드 컴포넌트 없음 — ResumeUpload도 inline 토큰 버튼) → LoginButtons/LogoutButton도 inline `var(--token)` 버튼(raw hex 0, 기존 컨벤션 정합). error는 **prop**(서버 page가 searchParams.error 주입)으로 — useSearchParams/Suspense 회피, 단위 테스트 단순. cookies()/searchParams는 Next 14.2 동기 API. 로그아웃 버튼은 layout에서 세션 쿠키 시에만 렌더(LogoutButton 별도 컴포넌트로 추출).
- 검증(implement): web tsc green · login.spec 4 pass(AC-1/2/3 + middleware allow) · `pnpm validate` green.

## 9. 의존성
- depends_on: [T-042]
- read_set: ["docs/20-system/DESIGN.md", "podo/apps/web/app/layout.tsx", "podo/apps/web/components/**"]
- write_set: ["podo/apps/web/app/login/page.tsx", "podo/apps/web/components/LoginButtons.tsx", "podo/apps/web/middleware.ts", "podo/apps/web/app/layout.tsx", "podo/apps/web/test/login.spec.tsx"]
- assumptions: ["T-042 AuthModule + /auth/github·/auth/google 엔드포인트 존재", "DESIGN §7 Button 컴포넌트 존재", "T-028 RTL 인프라 존재"]
- verifier: "pnpm --filter @podo/web test"
