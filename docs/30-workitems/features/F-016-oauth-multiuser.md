# F-016-oauth-multiuser: OAuth 소셜 로그인 + 사용자별 데이터 격리

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
M3까지 단일 사용자(self-proxy)였던 서비스를, **OAuth 소셜 로그인(GitHub·Google) + 사용자별 데이터 격리** 멀티유저로 전환한다. `users` 테이블 신설, httpOnly 쿠키 세션, `resumes`·`ranking_runs`·`recommendations` 및 신규 user-facing 테이블을 `user_id`로 묶어 **본인 데이터만 조회·채점**한다. 채점 트리거는 *요청 사용자가 해당 이력서 소유자인지* 인가 후에만. 계정 PII는 ADR-105 Amendment 1대로(마스킹 X·최소 저장·스코어링 경로 유입 금지). 무키 E2E/CI를 위한 테스트 인증 우회 경로를 둔다. **M4 첫 작업** — 다른 feature가 user 컨텍스트에 의존.

상위 결정: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)(멀티유저·OAuth) · [ADR-105 Amend1](../../90-decisions/project/ADR-105-pii-masking-policy.md#adr-105-amend-1)(계정 PII).

## 2. 사용자 가치 (User Story)
- As a **유진(신입/졸업예정 개발자 구직자)**, I want to log in with my GitHub/Google account, so that my resume and recommendations are private to me and persist across sessions on my own account.

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 비로그인 사용자가 진입 → "GitHub으로 시작 / Google로 시작" 로그인 화면.
2. provider 선택 → OAuth redirect → 동의 → callback.
3. 최초 로그인이면 `users`에 계정 생성(provider·account id·이메일·표시이름·아바타), 재로그인이면 기존 계정 매칭.
4. httpOnly 쿠키 세션 발급 → 피드/업로드 등 보호 라우트 접근 가능.
5. 이후 모든 이력서·채점·지원기록은 해당 `user_id`로 격리 저장·조회.
### Alternate path
1. 이미 세션 유효 → 로그인 화면 건너뛰고 피드로.
2. 로그아웃 → 세션 무효화 → 보호 라우트 접근 시 로그인 화면으로.
### Fail path
1. 🔴 OAuth 동의 거부/실패 → "로그인에 실패했어요. 다시 시도해주세요." + 재시도(가짜 세션 발급 금지).
2. 🔴 사용자 A가 B의 `resume_id`로 채점/조회 시도 → 403/404(횡단 접근 차단 — 존재 노출도 금지).
3. 🔴 세션 만료 → 401 → 재로그인 유도.

## 4. 범위
- NestJS `AuthModule`: OAuth(GitHub·Google) 전략 + callback + 세션 발급/검증/로그아웃 + 인증 가드(`@UseGuards`).
- Prisma 스키마: `users` 테이블(api 소유) + `resumes`·`ranking_runs`(간접)·지원/즐겨찾기 테이블에 `user_id` FK. **모든 user-facing 조회에 user 범위 필터.**
- 세션 = httpOnly 쿠키(SSR Next.js 정합). 로그인 상태 SSR 가드 + 보호 라우트.
- 채점 인가: `POST /resumes/:id/score`(F-017 트리거) 전에 `resume.user_id == session.user_id` 검증.
- **계정 PII(ADR-105 Amend1):** `users`에 최소 식별자만, OAuth 토큰 미영속, 계정 PII가 스코어링 경로(prompt·LLM·`.cache/llm`·`ranking_runs.result`·로그)에 미유입.
- **테스트 인증 우회**: fake provider 또는 시드 세션(프로덕션 빌드 비활성) — 무키 E2E/CI 보존.
- Next.js 로그인 화면(GitHub/Google 버튼, DESIGN.md 토큰) + 로그아웃.
- schema-contract test 갱신(`users`·`user_id` FK 존재).

## 5. 비범위
- 협업/공유(취업 스터디·코치 공유) — Charter §5 유지 비범위(ADR-107 D1).
- 자체 비밀번호 인증·이메일 매직링크 — OAuth만.
- 카카오/네이버 등 추가 provider — 후속.
- 역할/권한(RBAC)·조직/팀 — 단일 등급 사용자.
- 계정 삭제·데이터 export(GDPR류) — M6 공개 배포와 함께 재검토.
- 공개 배포(실 redirect 도메인) — M6. M4는 로컬 callback.

## 6. 요구사항
- OAuth provider = GitHub·Google(ADR-107 D2). 세션 = httpOnly 쿠키(D3).
- `users` 최소 필드: provider, provider_account_id, email, display_name, avatar_url, created_at. (OAuth 토큰 컬럼 없음.)
- 전 user-facing 조회/쓰기에 `user_id` 범위 — 횡단 접근 0(ADR-107 D4).
- 에러 바디 `{ error: { code, message } }`(ARCH §7-1). 인증 실패=401, 인가 실패=403/404.
- 테스트 인증 우회 경로 존재 + 프로덕션 빌드 비활성(ADR-107 D5).
- 계정 PII가 스코어링 표면·로그에 미유입(ADR-105 Amend1).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** 비로그인 사용자가 GitHub(또는 Google)로 로그인하면 `users`에 계정이 생성/매칭되고 httpOnly 쿠키 세션으로 보호 라우트(피드)에 접근할 수 있다.
- **FAC-2:** 사용자 A가 사용자 B의 `resume_id`·피드·지원기록·채점결과에 접근/채점을 시도하면 403/404로 차단되고 B의 데이터·존재가 노출되지 않는다(횡단 접근 차단).
- **FAC-3:** 채점 트리거는 `resume.user_id == session.user_id`일 때만 수행된다(타인 이력서 채점 불가).
- **FAC-4:** schema-contract pytest가 `users` 테이블 + `resumes.user_id`(및 격리 FK) 존재를 검증하고 green이다.
- **FAC-5:** 테스트 인증 우회 경로로 OAuth redirect 없이 세션을 얻어 무키 E2E가 로그인 상태로 진행된다(프로덕션 빌드에서 우회 비활성).
- **FAC-6:** 계정 PII(이메일·표시이름)가 `ranking_runs.result`·`.cache/llm`·애플리케이션 로그에 나타나지 않는다(literal scan 0).

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-042:AC-1, T-042:AC-5, T-043:AC-1, T-043:AC-3
- FAC-2 → T-042:AC-2
- FAC-3 → T-042:AC-2, T-044:AC-1
- FAC-4 → T-042:AC-4
- FAC-5 → T-042:AC-1, T-042:AC-3
- FAC-6 → T-052:AC-3

## 8. Non-functional Requirements
- 보안: 세션 쿠키 httpOnly·SameSite·(프로덕션) Secure. 인가는 controller 진입점에서 일괄(AGENTS.md 단순성 — 시스템 경계만).
- 데이터 격리는 *기능*이 아니라 *안전 게이트* — M4 graduation 필수(데이터 격리 Pass).
- 계정 PII 미유입(ADR-105 Amend1) — PII Safety Pass에 계정 식별자 literal 추가.

## 8-1. UX 흐름 품질
- **primary task:** provider 선택 → 동의 → 피드 진입(3단계, 마찰 최소).
- **empty 흐름:** 비로그인 → "포도와 함께 시작해요" + GitHub/Google 버튼.
- **loading 흐름:** OAuth 왕복 중 → 버튼 spinner/disabled, 가짜 진입 금지.
- **error 흐름:** 동의 거부/실패 → "로그인에 실패했어요. 다시 시도해주세요." 재시도.
- **accessibility:** provider 버튼 키보드 포커스·label, 세션 만료 안내.
- **copy 톤:** podo 친근 톤이되 보안 메시지는 사실 명확.
- **success metric (HEART):** Adoption → 로그인 시작→완료율 ≥80%(실 배포 후 이벤트 로그).

## 9. 엣지 케이스
- 동일 이메일이 GitHub·Google 양쪽으로 로그인 → provider+account id로 별 계정 vs 이메일 병합? → **provider별 별 계정(병합 비범위)**, plan에서 확정.
- 세션 쿠키 위조/만료 → 401, 재로그인.
- OAuth provider 장애 → 명확한 에러 + 재시도(가짜 세션 금지).
- 로그인했으나 이력서 미업로드 → 피드 empty + 업로드 유도(F-018 empty 흐름).

## 10. 의존성
- 상위: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)·[ADR-105 Amend1](../../90-decisions/project/ADR-105-pii-masking-policy.md#adr-105-amend-1).
- 후행 의존: F-017(채점 인가 후 enqueue)·F-018(보호 라우트·세션 기반 피드)·F-019(user 범위 지원기록) 모두 본 feature의 user 컨텍스트에 의존 → **M4 첫 구현**.
- DISCOVERY/Charter 멀티유저 범위 sync(ADR-107 후속).

## 11. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§5 멀티유저 — ADR-107 반전)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-1 API/인증](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1), [## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md) · [ADR-105 Amend1](../../90-decisions/project/ADR-105-pii-masking-policy.md#adr-105-amend-1) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 12. 열린 질문
- OAuth 라이브러리 = NestJS Passport(passport-github/google) vs Auth.js(next-auth) 프론트 주도 — 세션 SSOT 위치(api vs web)와 함께 plan에서 확정.
- provider별 계정 vs 이메일 병합 정책(엣지 케이스) — plan.
- 세션 저장 = 쿠키 자체(stateless signed) vs DB 세션 테이블 — plan(단순성 우선이면 signed 쿠키).
