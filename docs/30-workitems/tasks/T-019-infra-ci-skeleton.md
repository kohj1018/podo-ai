# T-019-infra-ci-skeleton

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
로컬 인프라(Docker Compose: Postgres+pgvector)와 `.github/workflows` skeleton을 둔다. M2 done-line(로컬 E2E)의 DB 런타임 + CI 골격.

## 2. 작업 범위
- `infra/docker-compose.yml`: Postgres+pgvector 서비스 + `.env.example`(`DATABASE_URL` 등 이름만).
- `.github/workflows` skeleton 4종: `deploy-api`·`deploy-worker`·`crawl-jobs`·`schema-contract`(placeholder/no-op 또는 lint-only, 실동작은 후속 T-021/T-025).

## 3. 구현 항목
1. `infra/docker-compose.yml` — 현재: 없음 → 변경: `postgres` 서비스(이미지 `pgvector/pgvector:pg16`, 포트 5432, volume, healthcheck). → 확인: `docker compose -f infra/docker-compose.yml up -d` 후 `psql ... -c "CREATE EXTENSION IF NOT EXISTS vector;"` 성공. (AC-1)
2. `.env.example` — 현재: (루트에 존재 가능) → 변경: `DATABASE_URL`·`OPENAI_API_KEY`·`OPENAI_MODEL`·`PROMPT_VERSION`·`NEXT_PUBLIC_API_BASE_URL` 이름만(값 비움). → 확인: `.env`는 gitignore(커밋 금지) 확인. (AC-1)
3. `.github/workflows/schema-contract.yml` — 현재: 없음 → 변경: PG 서비스 컨테이너 + `uv run pytest ai/tests/test_schema_contract.py` 호출 골격(T-021이 실측 채움). → 확인: `actionlint` 또는 YAML 파서 통과. (AC-2)
4. `.github/workflows/{deploy-api,deploy-worker,crawl-jobs}.yml` — 현재: 없음 → 변경: trigger(workflow_dispatch + crawl-jobs는 schedule cron 골격) + no-op step. → 확인: YAML 유효. (AC-2)

## 4. 제외 항목
- 실제 배포 로직(Vercel/AWS — M2 비범위) · schema-contract 실측(T-021) · crawl-jobs 실행 로직(T-025).

## 4-1. 변경 예정 파일/경로
- `infra/docker-compose.yml`, `.env.example`, `.github/workflows/schema-contract.yml`, `.github/workflows/deploy-api.yml`, `.github/workflows/deploy-worker.yml`, `.github/workflows/crawl-jobs.yml`

## 5. 완료 조건
`docker compose up`으로 PG+pgvector가 기동되고 extension이 가용하며, CI workflow 4종 YAML이 유효하다.

## 6. Acceptance Criteria
- AC-1 [Given] `infra/docker-compose.yml` [When] `docker compose up -d` 후 DB 접속 [Then] Postgres가 기동되고 `CREATE EXTENSION IF NOT EXISTS vector`가 성공한다.
- AC-2 [Given] `.github/workflows` 4종 [When] YAML lint(actionlint) [Then] 4개 파일 모두 유효하고 `crawl-jobs.yml`은 `schedule` cron + `workflow_dispatch` 트리거를 갖는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → (수동/스크립트) `docker compose up -d && psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS vector;"` exit 0
- AC-2 → `actionlint .github/workflows/*.yml` exit 0

## 6-2. TDD opt-out
- 사유: 인프라 설정(compose/YAML)은 단위 테스트 부적합 — 기동 검증·YAML lint로 대체.
- Follow-up task: schema-contract 실측 테스트는 T-021.

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-005-monorepo-scaffold](../features/F-005-monorepo-scaffold.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동 — PG, §7-0 디렉터리·env)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3) (주기 수집 cron)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-DB·D-DEPLOY)

## 8. 메모
- 해석 확정: AC-2 = workflow는 *skeleton*(trigger + no-op/placeholder) — 실동작은 schema-contract(T-021)·crawl-jobs(T-025)가 채움.

## 9. 의존성
- depends_on: [T-018]   # podo/ scaffold 후 루트 구조 위에 infra/CI 배치
- write_set: ["infra/docker-compose.yml", ".env.example", ".github/workflows/schema-contract.yml", ".github/workflows/deploy-api.yml", ".github/workflows/deploy-worker.yml", ".github/workflows/crawl-jobs.yml"]
- assumptions: ["Docker Desktop 설치됨"]
- verifier: "actionlint .github/workflows/*.yml"
