# T-042-oauth-auth-module

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
NestJS `AuthModule`을 신설해 **GitHub·Google OAuth 소셜 로그인 + httpOnly 쿠키 세션**을 구현한다. `users` 테이블(Prisma 스키마)과 전 user-facing 조회에 `user_id` 범위 인가 가드를 붙인다. 테스트 우회(fake provider/시드 세션) 경로도 포함해 무키 E2E/CI 보존. **F-016 M4 첫 작업** — 다른 feature가 user 컨텍스트에 의존한다(ADR-107 D4/D5).

## 2. 작업 범위
- Prisma 스키마: `users` 테이블 신설 + `resumes.user_id` FK(기존 테이블에 컬럼 추가) + 마이그레이션.
- NestJS `AuthModule`: passport-github2/passport-google-oauth20 전략 + callback 핸들러 + 세션 발급/검증/로그아웃 엔드포인트.
- httpOnly 쿠키 세션(express-session + 서명 쿠키, DB 세션 테이블 없이 stateless signed 쿠키).
- `JwtAuthGuard`(또는 `SessionGuard`) — 보호 라우트 전 `@UseGuards` 적용.
- 채점 인가: `POST /resumes/:id/score` 전 `resume.user_id == session.user_id` 검증.
- **계정 PII(ADR-105 Amend1)**: `users`에 최소 5필드만 저장(provider·provider_account_id·email·display_name·avatar_url), OAuth 토큰 미영속, 계정 PII 스코어링 경로 미유입.
- **테스트 우회**: `NODE_ENV=test`일 때만 활성인 `/auth/test-session` 엔드포인트(시드 세션 발급) — 프로덕션 빌드 비활성.
- schema-contract pytest 갱신(`users` 테이블 + `resumes.user_id` FK 존재 검증).

## 3. 구현 항목
1. 의존성 설치 — `pnpm --filter @podo/api add passport @nestjs/passport passport-github2 passport-google-oauth20 express-session @types/passport @types/passport-github2 @types/passport-google-oauth20 @types/express-session` (용도: OAuth 전략 + 세션). → 확인: import 가능. (AC-1)
2. `podo/apps/api/prisma/schema.prisma` — 현재: `users` 없음 → 변경: `model User { id String @id @default(cuid()) provider String provider_account_id String email String display_name String avatar_url String? created_at DateTime @default(now()) resumes Resume[] @@unique([provider, provider_account_id]) }` + `model Resume`에 `user_id String? user User? @relation(fields:[user_id], references:[id])` 추가. → 확인: `prisma generate` 성공. (AC-1)
3. `prisma migrate dev --name add_users_table` — 마이그레이션 파일 생성. → 확인: `prisma migrate status` clean. (AC-1)
4. `podo/apps/api/src/auth/` 디렉토리 신설:
   - `auth.module.ts` — PassportModule, SessionSerializer, GitHub/Google 전략, AuthController, AuthService 배선.
   - `auth.service.ts` — `findOrCreateUser(provider, profile)`: `users` upsert(provider+account_id 복합 unique). **OAuth access token 미저장**. 반환 `userId`.
   - `github.strategy.ts` — `PassportStrategy(Strategy, 'github')`: 환경변수 `GITHUB_CLIENT_ID/SECRET/CALLBACK_URL`. validate에서 `authService.findOrCreateUser('github', profile)` 호출. **계정 PII(email·displayName)를 log에 출력 금지**.
   - `google.strategy.ts` — `PassportStrategy(Strategy, 'google')`: 환경변수 `GOOGLE_CLIENT_ID/SECRET/CALLBACK_URL`. 동일 패턴.
   - `session.serializer.ts` — `serializeUser(userId)` / `deserializeUser(userId→User)`.
   - `session.guard.ts` — `@Injectable() SessionGuard implements CanActivate`: `req.isAuthenticated()` 확인, 아니면 401.
   - `auth.controller.ts` — `GET /auth/github` / `GET /auth/github/callback` / `GET /auth/google` / `GET /auth/google/callback` / `POST /auth/logout`. **`POST /auth/test-session`**(NODE_ENV=test만 활성 — `if (process.env.NODE_ENV !== 'test') throw 403`): body `{ userId }` 받아 `req.session` 시드 발급(무키 E2E용 — AC-1/AC-3와 일치, GET body 금지·세션 발급은 POST: ARCH §7-1). → 확인: callback·test-session 후 session 쿠키 발급. (AC-1, AC-3)
5. `podo/apps/api/src/resumes/resumes.controller.ts` — 현재: 인가 없음 → 변경: `@UseGuards(SessionGuard)` 추가. `POST /resumes/:id/score`(F-017 트리거)에 소유권 검증 `if (resume.user_id !== req.user.id) throw new ForbiddenException`. → 확인: 비로그인 시 401 반환. (AC-2)
6. `podo/apps/api/src/feed/feed.controller.ts` + `coverage.controller.ts` — 현재: 인가 없음 → 변경: `@UseGuards(SessionGuard)` 추가 + 피드 쿼리에 `where: { user_id: req.user.id }` 범위 필터. → 확인: A 세션으로 B 데이터 조회 시 빈 결과(404). (AC-2)
7. `podo/apps/api/src/app.module.ts`(또는 `main.ts`) — `AuthModule` import + `express-session` 미들웨어 + `passport.initialize()/session()` 적용. **쿠키: `httpOnly:true` + 환경 의존 `sameSite`/`secure`** — 로컬(web:3000↔api:3001 = same-site)은 `sameSite:'lax'`, **프로덕션(Vercel↔AWS = cross-site)은 `sameSite:'none'`+`secure:true`**(아니면 교차출처 fetch에서 쿠키 미전송 — M2 enableCors 부채 연장). **CORS**: `app.enableCors({ origin: <web origin>, credentials: true })` + web fetch는 `credentials:'include'`(와일드카드 금지 — T-087). → 확인: `pnpm start` 부팅 + 로컬 same-site 세션 쿠키 동작. (AC-1)
8. `ai/tests/test_schema_contract.py` — 현재: `users` 테이블 검증 없음 → 변경: `users` 테이블 존재 + 컬럼(provider·provider_account_id·email) + `resumes.user_id` FK 검증 추가. → 확인: `pytest ai/tests/test_schema_contract.py` green. (AC-4)
9. `podo/apps/api/test/auth.spec.ts` (신규) — AC-1(test-session 발급→피드 접근), AC-2(횡단 차단), AC-3(test-session 프로덕션 비활성). → 확인: `pnpm --filter @podo/api test` green. (AC-1, AC-2, AC-3)

## 4. 제외 항목
- 카카오/네이버 등 추가 provider. · RBAC/역할 권한. · 계정 삭제·데이터 export. · 이메일 병합(동일 이메일 다른 provider = 별 계정). · 실 redirect 도메인(M6). · DB 세션 테이블(stateless signed 쿠키로 대체). · 로그인 UI(T-043 담당).

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/prisma/schema.prisma` — users 테이블 + resumes.user_id FK
- `podo/apps/api/prisma/migrations/YYYYMMDD_add_users_table/migration.sql` (신규)
- `podo/apps/api/src/auth/` (신규 디렉토리 + 7개 파일)
- `podo/apps/api/src/app.module.ts` — AuthModule 등록 + session 미들웨어
- `podo/apps/api/src/resumes/resumes.controller.ts` — SessionGuard + 소유권 검증
- `podo/apps/api/src/feed/feed.controller.ts` — SessionGuard + user 범위 필터
- `podo/apps/api/src/coverage/coverage.controller.ts` — SessionGuard
- `podo/apps/api/test/auth.spec.ts` (신규)
- `ai/tests/test_schema_contract.py` — users·user_id FK 검증 추가
- `podo/apps/api/package.json` + `pnpm-lock.yaml` — 의존성 추가

## 4-2. 사용자 직접 수행 (웹 콘솔 — builder/코드 불가, 검증: 최신 공식문서 2026-06)
> OAuth 앱 등록은 *제공자 웹 콘솔*에서 사람이 해야 한다(코드 불가). client secret은 `.env`/시크릿 매니저에만, **커밋 금지**. **무키 E2E/CI는 `/auth/test-session` 우회 경로**(AC-3/AC-5)로 이 단계 없이 통과.
- **GitHub OAuth App** ([공식](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app)): Settings → Developer settings → **OAuth Apps → New OAuth App**. *Authorization callback URL* = `http://localhost:3001/auth/github/callback`(로컬). **OAuth App은 callback URL 1개만** 허용 → **로컬/프로덕션 = 별도 OAuth App 2개**(프로덕션 callback은 M6/T-087에서 실 도메인으로). Client ID(공개) + **Generate a new client secret**(1회 노출) → `GITHUB_CLIENT_ID`·`GITHUB_CLIENT_SECRET`·`GITHUB_CALLBACK_URL` env에.
- **Google OAuth Client** ([공식](https://support.google.com/cloud/answer/15549257)): Google Cloud Console → **APIs & Services → OAuth consent screen** 구성 → **Credentials → Create Credentials → OAuth client ID → Web application**. *Authorized redirect URIs*에 `http://localhost:3001/auth/google/callback`(Google은 **다중 redirect URI 허용** → 로컬+프로덕션 한 클라이언트에 추가 가능). Client ID + Secret → `GOOGLE_CLIENT_ID`·`GOOGLE_CLIENT_SECRET`·`GOOGLE_CALLBACK_URL` env에. ⚠ redirect URI는 **정확히 일치**해야 함(`redirect_uri_mismatch` 방지), 설정 반영에 수 분~수 시간 소요 가능.
- **세션 secret**: `SESSION_SECRET`(랜덤 고강도) env 생성. **위 secret 일체 커밋 금지**(`.env`는 `.gitignore`).

## 5. 완료 조건
GitHub·Google OAuth 로그인으로 `users` 계정이 생성/매칭되고 httpOnly 쿠키 세션으로 피드 등 보호 라우트에 접근 가능하다. 사용자 A가 B의 데이터에 접근하면 401/403/404로 차단된다. 테스트 우회 경로로 무키 E2E 세션을 발급할 수 있고 프로덕션 빌드에서는 비활성이다. schema-contract pytest green.

## 6. Acceptance Criteria
- AC-1 [Given] 테스트 환경에서 `/auth/test-session` + `{ userId }` [When] POST [Then] httpOnly 쿠키 세션이 발급되고 해당 세션으로 `GET /api/v1/feed`가 200을 반환한다.
- AC-2 [Given] 사용자 A 세션 [When] 사용자 B의 `resume_id`·피드·지원기록에 접근/채점 시도 [Then] 403 또는 404를 반환하고 B 데이터가 응답 바디에 노출되지 않는다(횡단 접근 차단).
- AC-3 [Given] `NODE_ENV=production` 빌드 [When] `/auth/test-session` 호출 [Then] 403을 반환해 우회 경로가 비활성임을 확인한다.
- AC-4 [Given] `prisma migrate dev` 적용 후 [When] `pytest ai/tests/test_schema_contract.py` [Then] `users` 테이블 존재 + `resumes.user_id` FK 존재로 green이다.
- AC-5 [Given] GitHub(또는 Google) OAuth strategy의 `validate`에 mock profile [When] callback 처리 [Then] `AuthService.findOrCreateUser`가 `users`에 (provider, provider_account_id)로 upsert(최초=생성, 재로그인=동일 계정 매칭)하고 httpOnly 세션이 발급되며 OAuth access token이 저장되지 않는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/api/test/auth.spec.ts::test_AC_1_test_session_issues_cookie_and_feed_returns_200
- AC-2 → vitest::podo/apps/api/test/auth.spec.ts::test_AC_2_cross_user_access_blocked_403_or_404
- AC-3 → vitest::podo/apps/api/test/auth.spec.ts::test_AC_3_test_session_disabled_in_production
- AC-4 → pytest::ai/tests/test_schema_contract.py::test_AC_4_users_table_and_user_id_fk_exist
- AC-5 → vitest::podo/apps/api/test/auth.spec.ts::test_AC_5_oauth_callback_upserts_user_and_issues_session

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Feature: [F-016-oauth-multiuser](../features/F-016-oauth-multiuser.md)
- Architecture-Iface: [ARCH ## 7-1 API/인증](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1), [## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md) · [ADR-105 Amend1](../../90-decisions/project/ADR-105-pii-masking-policy.md#adr-105-amend-1) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 8. 메모
- 세션 저장 = stateless signed 쿠키(express-session 기본, secret 환경변수). DB 세션 테이블 없음 — 단순성 우선(ADR-006).
- OAuth 토큰(access/refresh) 컬럼은 `users`에 없음 — ADR-105 Amend1 §2.
- 계정 PII(email·display_name)는 `users` 테이블에만 존재. `ranking_runs.result`·`.cache/llm`·로그에 유입 금지 — AuthService에서 log.debug 시 email 출력 금지 주석 명시.
- 동일 이메일이 GitHub·Google 양쪽 → provider+account_id 복합 unique로 별 계정(병합 비범위).
- **라이브러리 검증(공식문서 2026-06)**: `@nestjs/passport`+`passport`+`passport-github2`(원본 `passport-github`은 GitHub API v3 이후 미유지 fork)+`passport-google-oauth20`+`express-session` = 현행 NestJS Passport 권장 방식과 일치. `@nestjs/config`로 env 주입.
- **OAuth 콜백 URL 1개 제약(GitHub)**: 로컬/프로덕션 별도 OAuth App. CI/E2E는 `/auth/test-session` 우회라 실 OAuth App 불요.

## 9. 의존성
- depends_on: []
- read_set: ["podo/apps/api/prisma/schema.prisma", "podo/apps/api/src/app.module.ts", "podo/apps/api/src/resumes/resumes.controller.ts", "podo/apps/api/src/feed/**", "ai/tests/test_schema_contract.py"]
- write_set: ["podo/apps/api/prisma/schema.prisma", "podo/apps/api/prisma/migrations/**", "podo/apps/api/src/auth/**", "podo/apps/api/src/app.module.ts", "podo/apps/api/src/resumes/resumes.controller.ts", "podo/apps/api/src/feed/feed.controller.ts", "podo/apps/api/src/coverage/coverage.controller.ts", "podo/apps/api/test/auth.spec.ts", "ai/tests/test_schema_contract.py", "podo/apps/api/package.json", "pnpm-lock.yaml"]
- assumptions: ["PrismaService 존재(T-026)", "Postgres 로컬 실행 중", "GitHub/Google OAuth 앱 로컬 등록(테스트는 우회 경로로 회피)"]
- verifier: "pnpm --filter @podo/api test && pytest ai/tests/test_schema_contract.py"
