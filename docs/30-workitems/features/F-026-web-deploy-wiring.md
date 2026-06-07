# F-026-web-deploy-wiring: Vercel web 배포 결선 (도메인·CORS·환경)

## 0. Status
draft

> **잠정 (M6).** Vercel 배포는 **사용자가 웹에서 직접 수행**(ADR-101 D-DEPLOY).

## 0-1. Type
technical-enabler

## 1. 요약
Vercel에 web 배포(사용자 직접) + `NEXT_PUBLIC_API_BASE_URL` 실 api 도메인 + api CORS 허용 origin + OAuth redirect callback URL(실 도메인)을 결선한다. M3 stabilize가 잡았던 로컬 CORS(`enableCors`) 이슈의 프로덕션 판.

## 2. 기술적 근거 (Technical rationale)
**무엇을:** Next.js web을 Vercel에 배포하고 api(AWS)와 결선한다(도메인·CORS·환경변수·OAuth redirect). ADR-101 D-DEPLOY: web=Vercel(사용자 직접), api/worker=AWS·crawler=GHA cron.
**서비스하는 결정:** [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)(D-DEPLOY) · [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)(OAuth redirect 도메인).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 사용자가 Vercel에 web 연결·배포 + 환경변수(`NEXT_PUBLIC_API_BASE_URL`) 설정.
2. api는 web 도메인을 CORS 허용 origin에 등록.
3. OAuth provider(GitHub·Google)에 실 redirect URL 등록 → 배포 도메인에서 로그인 동작.
4. 배포 URL에서 회원가입→업로드→채점→피드 완주.
### Fail path
1. 🔴 CORS 미허용 → web→api 호출 차단(명확 에러).
2. 🔴 OAuth redirect URL 미등록 → 로그인 실패.

## 4. 범위
- Vercel 프로젝트 설정(사용자 직접) + 환경변수.
- api CORS 허용 origin(web 도메인) — 프로덕션 결선.
- OAuth redirect callback(실 도메인) 등록(F-016 프로덕션 판).
- 도메인/HTTPS.

## 5. 비범위
- web 기능 변경 — M4 완성분.
- AWS api 호스팅 — F-025.
- CDN/엣지 최적화 고급 — 기본 Vercel.

## 6. 요구사항
- web=Vercel·사용자 직접(ADR-101 D-DEPLOY).
- CORS·redirect URL 프로덕션 결선.
- 시크릿/환경변수 미커밋.

## 7. Feature-level Acceptance Criteria
- **FAC-1:** Vercel 배포 web에서 `NEXT_PUBLIC_API_BASE_URL`로 AWS api를 호출하고 CORS가 허용된다.
- **FAC-2:** 배포 도메인에서 GitHub/Google OAuth 로그인이 동작한다(redirect URL 등록).
- **FAC-3:** 배포 URL에서 회원가입→업로드→채점→피드가 멀티유저로 완주한다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-087:AC-1
- FAC-2 → T-087:AC-2
- FAC-3 → T-087:AC-3

## 8. Non-functional Requirements
- 보안: CORS 화이트리스트(와일드카드 금지), HTTPS, 세션 쿠키 Secure.
- 성능: 정적 자산 CDN(Vercel 기본).

## 8-1. UX 흐름 품질
(해당 없음 — 배포 결선. UX는 F-018.)

## 9. 엣지 케이스
- 프리뷰 배포 도메인 OAuth redirect(와일드카드 불가) 처리.
- web↔api 도메인 쿠키 SameSite(크로스사이트) 정책.

## 10. 의존성
- 선행: F-024(api 도메인)·F-025(api 호스팅)·F-016(OAuth).
- 상위: ADR-101·ADR-107.

## 11. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-4 Vercel)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1), [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) · [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)

## 12. 열린 질문 (논의 전제)
- web↔api 쿠키 세션의 크로스도메인 처리(동일 상위도메인 vs SameSite=None; Secure).
- 프리뷰 배포 OAuth 처리.
