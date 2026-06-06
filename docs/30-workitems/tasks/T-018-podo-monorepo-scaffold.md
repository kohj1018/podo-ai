# T-018-podo-monorepo-scaffold

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
`podo/` TS 모노레포를 Turborepo+pnpm으로 scaffold하고 `apps/api`(NestJS)·`apps/web`(Next.js+Tailwind) 골격 + 헬스 경로를 세운다. M2 전 체인의 물리 기반(ARCH §3-2 매핑표). 알고리즘·스키마·UI 로직은 비범위.

## 2. 작업 범위
- `podo/` pnpm workspace + Turborepo + Biome 설정.
- `podo/apps/api` NestJS 골격 + `GET /api/v1/health`.
- `podo/apps/web` Next.js(App Router)+Tailwind 골격 + 헬스 페이지.
- 루트 통합 `validate`에 TS(Biome lint + Vitest placeholder) 합류.

## 3. 구현 항목
1. 의존성 설치 — `pnpm init` + `pnpm add -D turbo @biomejs/biome` (podo/ 루트). → 확인: `podo/package.json`·`pnpm-workspace.yaml`(`apps/*`)·`turbo.json` 생성. (AC-1)
2. `podo/apps/api` — 현재: 없음 → 변경: NestJS scaffold(`pnpm dlx @nestjs/cli new api --skip-git --package-manager pnpm`) + `src/health.controller.ts`에 `@Get('api/v1/health')` → `{status:'ok'}`. 포트 3001(`main.ts`). → 확인: `pnpm --filter api start` 후 `curl :3001/api/v1/health` = 200. (AC-1)
3. `podo/apps/web` — 현재: 없음 → 변경: `pnpm dlx create-next-app@latest web --ts --tailwind --app --no-git` + `app/page.tsx` 헬스 표시. 포트 3000. → 확인: `pnpm --filter web dev` 후 `:3000` 200. (AC-1)
4. `podo/biome.json` — 현재: 없음 → 변경: Biome lint/format 설정(ADR-101 — Biome for TS). → 확인: `pnpm exec biome check .` 통과. (AC-2)
5. `podo/apps/{api,web}`에 Vitest placeholder 테스트 1개씩(`*.spec.ts` smoke). 루트 `validate`(또는 `pnpm -r test`)에 합류. → 확인: `pnpm -r test` exit 0. (AC-2)

## 4. 제외 항목
- Prisma 스키마(T-020) · 실제 endpoint/UI 로직(F-009/F-010) · Docker/CI(T-019) · Vercel 배포.

## 4-1. 변경 예정 파일/경로
- `podo/package.json`, `podo/pnpm-workspace.yaml`, `podo/turbo.json`, `podo/biome.json`, `podo/apps/api/**`(scaffold), `podo/apps/web/**`(scaffold), `pnpm-lock.yaml`

## 5. 완료 조건
`pnpm install` 후 단일 명령으로 web·api가 기동되고 헬스 경로가 응답하며, TS lint/test가 green이다.

## 6. Acceptance Criteria
- AC-1 [Given] fresh checkout + `pnpm install` [When] web·api를 기동(`pnpm dev` 또는 개별 filter) [Then] `:3000` 200, `:3001/api/v1/health`가 `{status:"ok"}` 200을 반환한다.
- AC-2 [Given] scaffold 완료 [When] `pnpm exec biome check . && pnpm -r test` [Then] exit 0이다(placeholder smoke 테스트 green).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/api/test/health.spec.ts::test_AC_1_health_returns_ok
- AC-2 → (lint/test 통합) `pnpm exec biome check . && pnpm -r test` exit 0

## 6-2. TDD opt-out
- 사유: scaffold(프레임워크 골격 생성)는 외부 generator 산출이라 RGR 부적합 — 헬스 경로만 테스트(AC-1)로 박고 골격 생성은 generator 사용.
- Follow-up task: 없음(후속 feature가 실로직 TDD).

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-005-monorepo-scaffold](../features/F-005-monorepo-scaffold.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 매핑, §7-0 운영 사실)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) (경로 `/api/v1`)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-MONO·D-LANG)

## 8. 메모
- 변경 파일이 scaffold라 5개 초과 — ADR-026 sizing 가이드상 *초기 scaffolding은 자연스러운 초과*(분할 권장 텍스트 N/A). 사용자 결정.
- 해석 확정: AC-1 = "기동+헬스 200"까지(라우팅/미들웨어 표준 골격 — 커스텀 로직 X).

## 9. 의존성
- (선행 없음 — M2 wave 1)
- write_set: ["podo/**", "pnpm-lock.yaml"]
- assumptions: ["Node/pnpm 설치됨", "포트 3000/3001 미점유"]
- verifier: "pnpm -r test"
- # lockfile race: `pnpm-lock.yaml` write → 단독 wave 권장(병렬 implement 시 충돌 차단)
