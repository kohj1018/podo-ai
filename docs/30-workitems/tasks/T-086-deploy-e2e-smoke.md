# T-086-deploy-e2e-smoke

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
배포 환경(실 AWS api + Vercel web)에서 E2E smoke 시나리오를 실행한다. `schema-contract`·`e2e-smoke` GHA 게이트가 green일 때만 deploy 진행(T-084 전제). M6 done-line의 핵심 증거: 실배포 URL에서 멀티유저 가입→업로드→채점→피드 완주. worker SQS consumer 상시 동작 + 채점 큐 경유 완주 확인(FAC-4).

## 2. 작업 범위
- `.github/workflows/e2e-smoke.yml`(**post-deploy, T-086 단독 소유** — `workflow_call`로 배포 *후* 실행): **기존 `scripts/e2e.mjs`를 `E2E_BASE_URL`로 실배포 URL 대상 실행**(신규 Playwright 도입 X — T-052/M2 패턴 재사용, API+feed assert). 가입→업로드→채점 대기(큐 경유 `done`)→피드 점수 행 + 멀티유저(2명) 격리.
- `scripts/e2e.mjs`에 `E2E_BASE_URL` env 지원 추가(미설정=로컬 docker compose, 설정=실배포 URL 대상). T-052의 멀티유저+격리 로직 재사용.
- worker SQS consumer 상시 동작 검증: enqueue 후 일정 시간 내 `done` 전환 폴링.
- schema-contract CI(`schema-contract.yml`) — T-019 skeleton 실가동: test DB 대상 `uv run pytest ai/tests/test_schema_contract.py` 실행.
- **deploy 게이트 소유권(라운드2 정합):** pre-deploy gate = **schema-contract**(T-084 소유, URL 불요). 본 task의 e2e-smoke는 **post-deploy 검증**이라 deploy-*.yml을 수정/소유하지 않는다(순환 방지).

## 3. 구현 항목
1. `.github/workflows/e2e-smoke.yml` — 현재: 없거나 skeleton → 변경: `on: workflow_call`(inputs `base_url`) + `jobs.smoke`: pnpm+uv setup + `E2E_BASE_URL=${{ inputs.base_url }} pnpm e2e:smoke`(= `node scripts/e2e.mjs`). → 확인: `actionlint` exit 0. (AC-1)
2. `scripts/e2e.mjs` — 현재: 로컬 docker compose 오케스트레이션(M2/T-052) → 변경: `E2E_BASE_URL` env 분기 추가(미설정=로컬, 설정=실배포 URL 대상 — compose 기동 skip, fetch 대상만 교체). 시나리오: ①OAuth 우회/가입 ②이력서 업로드 ③채점 enqueue→`done` 폴링(최대 60초) ④`GET /api/v1/feed` 점수 행 assert. → 확인: `E2E_BASE_URL=<url> pnpm e2e:smoke` 완주. (AC-1)
3. `scripts/e2e.mjs` 멀티유저 격리 단계(T-052 재사용) — 사용자 A·B 가입 → A 피드에 B 데이터 미노출 assert. → 확인: 동일 실행 내 격리 단계 통과. (AC-2)
4. `.github/workflows/schema-contract.yml` — 현재: skeleton(T-019) → 변경: `jobs.contract`: Postgres 서비스 컨테이너(test DB) + `uv run pytest ai/tests/test_schema_contract.py -v` → 확인: CI에서 pass. (AC-3)
5. **deploy 게이트 배선(소유권 분리):** 본 task는 `deploy-api.yml`·`deploy-worker.yml`을 **수정하지 않는다**(T-084 소유). pre-deploy gate=schema-contract(T-084의 `needs`), e2e-smoke는 **배포 *후*** deploy workflow가 `e2e-smoke.yml`을 `workflow_call`로 호출(또는 별도 post-deploy job)하도록 T-084와 인터페이스만 합의. → 확인: e2e-smoke.yml이 deploy 후 실행되는 구조(순환 없음).

## 4. 제외 항목
- 전체 E2E 커버리지(smoke 1~2 시나리오만) — 전체는 로컬 `pnpm e2e`.
- 성능 테스트·부하 테스트.
- 알림 발송 smoke — 비범위.

## 4-1. 변경 예정 파일/경로
- `.github/workflows/e2e-smoke.yml` — `on: workflow_call`(inputs.base_url) 추가(post-deploy 호출 가능) + `E2E_BASE_URL: ${{ inputs.base_url }}` 주입 + SQS 큐 생성 step을 로컬모드(base_url 빈값)로 조건화 + `pnpm e2e:smoke` 실행. pull_request 로컬 게이트 유지
- `.github/workflows/schema-contract.yml` — node/pnpm setup + **`prisma migrate deploy`**(누락된 마이그레이션 step 추가 — 빈 DB에서 pytest 실패 방지) + `pytest test_schema_contract.py -v`
- `scripts/e2e.mjs` — `E2E_BASE_URL` 분기(REMOTE_MODE): 설정 시 compose/migrate/worker 기동 생략 + `base=E2E_BASE_URL` + `runRemoteSmoke()`(health→가입→업로드→채점 enqueue→done 폴링→피드+격리 assert). 미설정 시 기존 로컬 동작 불변
- `package.json`(루트) — `e2e:smoke` script 추가(`node scripts/e2e.mjs`)

## 5. 완료 조건
배포 환경 URL에서 smoke 시나리오(가입→업로드→채점→피드)가 멀티유저 격리와 함께 `scripts/e2e.mjs`로 통과하고, schema-contract CI가 green이며, **schema-contract가 pre-deploy gate(T-084), e2e-smoke가 post-deploy 검증**으로 동작한다(순환 없음).

## 6. Acceptance Criteria
- AC-1 [Given] 배포된 api(AWS) + web(Vercel) [When] `E2E_BASE_URL=<실배포 URL> pnpm e2e:smoke`(scripts/e2e.mjs) [Then] 가입→이력서 업로드→채점 완료(큐 경유 done)→`GET /api/v1/feed` 점수 행 assert가 통과한다.
- AC-2 [Given] 사용자 A·B 각각 계정 생성·이력서 업로드 [When] A로 로그인한 피드 조회 [Then] B의 채점 결과가 A의 피드에 노출되지 않는다(격리).
- AC-3 [Given] `schema-contract.yml` CI [When] RDS 호환 test DB에서 `pytest ai/tests/test_schema_contract.py` [Then] worker 의존 컬럼·타입이 존재함을 확인하고 green이다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → `E2E_BASE_URL=<url> pnpm e2e:smoke`(scripts/e2e.mjs — 가입→업로드→채점 done→feed assert, exit 0)
- AC-2 → scripts/e2e.mjs 격리 단계(A→B 데이터 미노출 assert)
- AC-3 → `pytest::ai/tests/test_schema_contract.py::test_worker_columns_exist`

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Feature: [F-025-service-deploy-pipelines](../features/F-025-service-deploy-pipelines.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-3, §7-4)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) · [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) · [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md)

## 8. 메모
- smoke 채점 대기(polling): SQS→worker→done 사이클이 실 환경에서 30~60초 소요 예상. Playwright `waitForSelector` 또는 polling helper 사용.
- 멀티유저 격리는 M4 done-line 조건 — M6 배포 환경 재검증.
- schema-contract는 RDS 직접 연결 대신 test DB(GHA 서비스 컨테이너 postgres)로 실행해도 컬럼 검증 목적 충족.

## 9. 의존성
- depends_on: [T-084, T-087]   # api·web 모두 배포된 URL이 있어야 smoke 가능
- write_set: [".github/workflows/e2e-smoke.yml", ".github/workflows/schema-contract.yml", "scripts/e2e.mjs", "package.json"]
- assumptions: ["T-084 api·worker 배포 완료", "T-087 Vercel web 배포 완료", "scripts/e2e.mjs(M2/T-052) 존재 — E2E_BASE_URL 분기만 추가"]
- verifier: "node scripts/e2e.mjs (또는 pnpm e2e:smoke)"
