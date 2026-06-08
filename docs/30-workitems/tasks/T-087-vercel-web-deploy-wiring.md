# T-087-vercel-web-deploy-wiring

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
Next.js web을 Vercel에 배포(사용자 직접)하고, api(AWS) 도메인·CORS·OAuth redirect를 결선한다. M3 stabilize가 잡은 로컬 CORS 이슈의 프로덕션 판 완결. [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)(D-DEPLOY: web=Vercel 사용자 직접) · [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)(OAuth redirect 도메인).

## 2. 작업 범위
- **사용자 수행**: Vercel 프로젝트 생성·연결 + **Root Directory = `podo/apps/web` 설정**(모노레포 — web만 배포, Vercel이 pnpm workspace·turbo 자동 감지; 필요 시 `vercel.json` install `cd ../.. && pnpm install`) + `NEXT_PUBLIC_API_BASE_URL`(실 api 도메인) 환경변수 + 도메인/HTTPS.
- api `main.ts` CORS 설정: `enableCors({ origin: '<vercel-domain>', credentials: true })` — 프로덕션 도메인 화이트리스트(와일드카드 금지).
- OAuth provider redirect callback URL = **실 api 도메인** `https://<api-domain>/auth/{github,google}/callback`(콜백은 **NestJS api가 처리** — T-042, web 도메인 아님) 등록(사용자 수행).
- 세션 쿠키 `SameSite`·`Secure` 플래그 — 크로스 도메인(web.vercel.app ↔ api.aws.com) 정합.

## 3. 구현 항목
1. **사용자 수행** — Vercel 대시보드에서 저장소 연결 + **Root Directory = `podo/apps/web`**(Project Settings → Root Directory → Edit) + `NEXT_PUBLIC_API_BASE_URL=https://<api-domain>` 환경변수 + 배포. → 확인: 배포 URL 발급 + `NEXT_PUBLIC_API_BASE_URL`이 브라우저 network 탭에서 실 api 도메인으로 호출됨. (AC-1 전제)
2. `podo/apps/api/src/main.ts` — 현재: `enableCors({ origin: '*' })`(또는 로컬 설정) → 변경: `origin: process.env.CORS_ALLOWED_ORIGIN`(환경변수 주입, 와일드카드 제거), `credentials: true` 유지 → 확인: `CORS_ALLOWED_ORIGIN` 미설정 시 기동 실패(명확 에러). (AC-1)
3. `CORS_ALLOWED_ORIGIN` 환경변수 — 현재: 없음 → 변경: api ECS task definition(또는 Secrets Manager)에 실 Vercel 도메인 값 추가(사용자 수행) + `.env.example`에 이름 추가 → 확인: api 로그에서 CORS origin 값 확인. (AC-1)
4. **사용자 수행** — OAuth 콜백 URL = **`https://<api-domain>/auth/github/callback`·`/auth/google/callback`**(NestJS api 처리 — T-042 routes, *web 도메인 아님*). **GitHub**: OAuth App은 콜백 1개만 → **프로덕션용 신규 OAuth App 생성**(T-042 §4-2). **Google**: 기존 OAuth client에 *Authorized redirect URI 추가*(다중 허용). 프로덕션 `GITHUB_*`/`GOOGLE_*`/`SESSION_SECRET` 시크릿 주입(커밋 금지). → 확인: 배포 도메인에서 OAuth 로그인 완주. (AC-2 전제)
5. 세션 쿠키 설정(`podo/apps/api/src/auth/` 또는 NestJS session 설정) — 현재: 로컬 설정 → 변경: 프로덕션에서 `SameSite: 'none'`·`Secure: true`(크로스 도메인 필수) — `NODE_ENV === 'production'` 조건부 → 확인: 배포 후 브라우저 DevTools Application > Cookies에서 `Secure·SameSite=None` 확인. (AC-2)

## 4. 제외 항목
- web 기능 변경 — M4/M5 완성분.
- CDN/엣지 최적화 — Vercel 기본 설정 사용.
- 프리뷰 배포 OAuth(와일드카드 불가 — 별도 열린 질문).
- api 호스팅 — F-025/T-084.

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/src/main.ts` — CORS `origin: process.env.CORS_ALLOWED_ORIGIN`(와일드카드 0) + 프로덕션 미설정 시 기동 실패 가드; 쿠키 `sameSite: isProd ? 'none':'lax'`·`secure: isProd`(기존 구현 유지)
- `podo/apps/api/src/auth/auth.controller.ts` — OAuth 콜백 리다이렉트를 `WEB_ORIGIN`→`CORS_ALLOWED_ORIGIN`로 통일(dual-var footgun 제거; 동일 web origin, write_set `auth/**` 내)
- `.env.example` — `CORS_ALLOWED_ORIGIN` 항목 추가(프로덕션 필수·localhost 기본·task definition 주입 주석)

## 5. 완료 조건
Vercel 배포 URL에서 `NEXT_PUBLIC_API_BASE_URL`로 AWS api를 호출하고 CORS가 허용되며, OAuth 로그인이 실 도메인에서 동작하고, 쿠키 Secure·SameSite=None이 설정된다.

## 6. Acceptance Criteria
- AC-1 [Given] Vercel 배포 web + AWS api [When] web에서 api 호출(fetch/axios) [Then] CORS 오류 없이 응답을 받고, api CORS 설정에 와일드카드(`*`)가 없다.
- AC-2 [Given] 실 배포 도메인 [When] GitHub/Google OAuth 로그인 시도 [Then] redirect가 성공하고 세션 쿠키에 `Secure`·`SameSite=None`이 설정된다.
- AC-3 [Given] web·api 결선 완료 [When] 배포 URL에서 가입→업로드→채점→피드 [Then] 멀티유저(사용자 2명)로 완주한다(T-086 smoke와 연동).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → `grep -n '"\*"' podo/apps/api/src/main.ts` → 0행(와일드카드 없음); 배포 후 `curl -I -H "Origin: https://<vercel-domain>" https://<api-domain>/health` → `Access-Control-Allow-Origin: https://<vercel-domain>` 포함
- AC-2 → 수동(사용자 확인): 배포 URL에서 OAuth 로그인 완주 + DevTools 쿠키 검사
- AC-3 → `jest::podo/apps/web/e2e/smoke.spec.ts::[smoke] 가입→업로드→채점→피드` (T-086 공유)

## 6-2. TDD opt-out
- 사유: Vercel 배포·OAuth 등록은 외부 대시보드 작업(에이전트 수행 불가). 코드 변경(CORS·쿠키)은 단위 테스트 가능하지만 최종 검증은 배포 후 smoke.
- Follow-up task: T-086(e2e-smoke)이 배포 환경 최종 검증.

## 7. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Feature: [F-026-web-deploy-wiring](../features/F-026-web-deploy-wiring.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-4 Vercel, §7-1 API CORS)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) · [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) · [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)

## 8. 메모
- SameSite=None + Secure는 크로스 도메인(web.vercel.app ↔ api.{aws-region}.amazonaws.com 또는 커스텀 도메인) 필수. 같은 상위 도메인이면 SameSite=Lax도 가능 — 도메인 구성 확정 후 결정.
- 프리뷰 배포 OAuth: Vercel preview URL은 동적이라 OAuth callback 사전 등록 불가. MVP는 production 도메인만(열린 질문 잔류).
- 사용자 직접 수행 단계는 에이전트가 실행하지 않는다 — §3 해당 항목 "사용자 수행" 명시.

## 9. 의존성
- depends_on: [T-084]   # api가 AWS에 배포되어 도메인이 있어야 CORS·환경변수 결선 가능
- write_set: ["podo/apps/api/src/main.ts", "podo/apps/api/src/auth/**", ".env.example"]
- assumptions: ["T-084 api 배포 완료, api 도메인 확정", "사용자가 Vercel 배포·OAuth 등록을 직접 수행", "CORS_ALLOWED_ORIGIN이 api 환경에 주입됨"]
- verifier: "grep -c '\"\\*\"' podo/apps/api/src/main.ts || true"
