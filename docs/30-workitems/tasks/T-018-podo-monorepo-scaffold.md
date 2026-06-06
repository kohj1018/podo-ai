# T-018-podo-monorepo-scaffold

## 0. Status
done

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
- 루트(pnpm 워크스페이스 루트): `package.json`(수정), `pnpm-workspace.yaml`, `turbo.json`, `pnpm-lock.yaml`, `.gitignore`(수정 — `*.tsbuildinfo`·`.turbo`)
- `podo/biome.json`, `podo/vitest.config.ts`
- `podo/apps/api/**`: `package.json`·`tsconfig.json`·`vitest.config.ts`·`src/{main,app.module,health.controller}.ts`·`test/health.spec.ts`
- `podo/apps/web/**`: `package.json`·`tsconfig.json`·`vitest.config.ts`·`next.config.mjs`·`next-env.d.ts`·`postcss.config.mjs`·`tailwind.config.ts`·`app/{layout,page}.tsx`·`app/globals.css`·`test/smoke.spec.ts`

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
- 구현 노트(2026-06-06): implement-workitem 포크가 루트 설정만 만들고 generator 단계 전 사망 → 메인 세션 수동 구현. §3의 generator(`@nestjs/cli new`·`create-next-app`) 대신 **hand-written 최소 scaffold** 채택. 사유: (1) 포크 사망, (2) generator 인터랙티브 프롬프트 hang 위험(sandbox 비대화), (3) generator 산출물(ESLint/Jest)이 Biome/Vitest 선택(§3-4/§3-5)과 충돌, (4) ADR-006 surgical(생성 cruft 0). AC-1(vitest health)·AC-2(biome+vitest) 동일 달성, 통합 validate green.
- 레이아웃 확정: pnpm 워크스페이스 루트=**repo 루트**(`pnpm-workspace.yaml`+`package.json`), TS 코드·공유설정(`podo/biome.json`·`podo/vitest.config.ts`)=`podo/`. 근거: `scripts/verify.mjs`가 repo 루트에서 `pnpm --filter "./podo/**"` 호출 + `podo/biome.json`·`podo/vitest.config.ts` 존재검사 = 의도된 설계(verify.mjs 무수정). turbo.json=루트(turbo는 podo apps만 orchestrate — ADR-101 D-MONO 정합).
- pnpm 11 빌드승인: `pnpm-workspace.yaml`의 `allowBuilds`(@biomejs/biome·esbuild=true, @nestjs/core=false). pnpm 11이 ignored build script에 명시 boolean을 요구(`onlyBuiltDependencies`만으론 `ERR_PNPM_IGNORED_BUILDS` exit 1). esbuild 빌드는 vitest 동작에 필수.

## 9. 의존성
- (선행 없음 — M2 wave 1)
- write_set: ["podo/**", "pnpm-lock.yaml"]
- assumptions: ["Node/pnpm 설치됨", "포트 3000/3001 미점유"]
- verifier: "pnpm -r test"
- # lockfile race: `pnpm-lock.yaml` write → 단독 wave 권장(병렬 implement 시 충돌 차단)
