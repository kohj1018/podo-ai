# T-044-sqs-infra-enqueue

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
LocalStack SQS 큐를 docker compose에 추가하고, NestJS api가 채점 요청을 SQS에 enqueue하도록 전환한다. **M3의 subprocess spawn(`uv run python -m worker`) 코드를 제거**하고 AWS SDK enqueue로 교체(ADR-106 D1/D2). `scoring_jobs` 테이블(api 소유)로 작업 상태 `queued→running→done|failed`를 추적. T-042(user 인가)가 선행.

## 2. 작업 범위
- `infra/docker-compose.yml`(또는 `docker-compose.yml`) — LocalStack 서비스 추가(포트 4566), SQS 큐 초기화 스크립트(`scoring-queue`).
- Prisma 스키마: `scoring_jobs` 테이블(api 소유) — `id, resume_id, status(queued/running/done/failed), created_at, updated_at`. **worker는 직접 write 금지**(ARCH §3-2 단일 writer).
- NestJS `ScoringModule`(또는 `QueueModule`): AWS SDK v3(`@aws-sdk/client-sqs`) enqueue 서비스. 환경변수 `SQS_ENDPOINT_URL`(LocalStack=`http://localhost:4566`, AWS=생략하면 실 SQS). 메시지 페이로드: `{ resume_id, job_id, ranking_mode }`.
- `POST /resumes/:id/score` — 현재: subprocess spawn → 변경: enqueue + `scoring_jobs.status=queued` INSERT + 202 `{ job_id, status: 'queued' }` 반환(블로킹 X).
- `GET /scoring-jobs/:job_id` — 작업 상태 폴링 엔드포인트(UI가 완료 감지).
- **api status consumer** — `scoring-status-queue`의 worker 상태 이벤트를 받아 `scoring_jobs.status`(running/done/failed) 갱신(api가 유일 writer). (LocalStack=2번째 큐, M6=실 SQS.)
- subprocess spawn 코드 제거(F-017 FAC-6).

## 3. 구현 항목
1. 의존성 설치 — `pnpm --filter @podo/api add @aws-sdk/client-sqs` (용도: SQS enqueue). → 확인: import 가능. (AC-1)
2. `infra/docker-compose.yml` — 현재: Postgres+pgvector → 변경: LocalStack 서비스 추가:
   ```yaml
   localstack:
     image: localstack/localstack:3
     ports: ["4566:4566"]
     environment:
       SERVICES: sqs
     volumes:
       - ./infra/localstack-init:/etc/localstack/init/ready.d
   ```
   `infra/localstack-init/01-create-queue.sh` — `awslocal sqs create-queue --queue-name scoring-queue`. → 확인: `docker compose up localstack` 후 큐 생성됨. (AC-1)
3. `podo/apps/api/prisma/schema.prisma` — 현재: scoring_jobs 없음 → 변경: `model ScoringJob { id String @id @default(cuid()) resume_id String status String @default("queued") created_at DateTime @default(now()) updated_at DateTime @updatedAt resume Resume @relation(fields:[resume_id], references:[id]) }` 추가. → 확인: `prisma generate` 성공. (AC-1)
4. `prisma migrate dev --name add_scoring_jobs_table`. (AC-1)
5. `podo/apps/api/src/queue/queue.service.ts` (신규) — `SQSClient`(endpoint=`SQS_ENDPOINT_URL` 환경변수, region=us-east-1) + `enqueue(resumeId, jobId)`: `SendMessageCommand({ QueueUrl, MessageBody: JSON.stringify({ resume_id, job_id }) })`. **메시지에 email·display_name 등 계정 PII 미포함**. → 확인: LocalStack 큐에 메시지 전송. (AC-1)
6. `podo/apps/api/src/resumes/resumes.controller.ts` — `POST /resumes/:id/score` 현재: subprocess spawn 코드 → 변경: (a) SessionGuard 소유권 확인(T-042); (b) `prisma.scoringJob.create({ data: { resume_id, status: 'queued' } })` → job_id; (c) `queueService.enqueue(resume_id, job_id)`; (d) 202 `{ job_id, status: 'queued' }` 반환. subprocess spawn 코드 완전 제거. → 확인: spawn 코드 0 + AC-1 엔드포인트 202. (AC-1, AC-3)
7. `podo/apps/api/src/resumes/resumes.controller.ts` + `scoring-jobs.controller.ts` (신규) — `GET /scoring-jobs/:id`: `prisma.scoringJob.findUnique` + user_id 범위 검증(횡단 접근 차단). 반환 `{ job_id, status, resume_id }`. → 확인: AC-2 폴링 응답. (AC-2)
8. `podo/apps/api/test/queue.spec.ts` (신규) — AC-1(enqueue→202→queued), AC-2(GET scoring-jobs 폴링), AC-3(spawn 코드 부재). → 확인: `pnpm --filter @podo/api test` green. (AC-1, AC-2, AC-3)

## 4. 제외 항목
- worker consumer 전환(T-045 담당). · 실 AWS SQS IAM 결선(M6). · 재시도/dead-letter 정책(T-045). · 우선순위 큐·동시성 제한. · 작업 진행률(%) push.

## 4-1. 변경 예정 파일/경로
- `infra/docker-compose.yml` — LocalStack(sqs) 서비스 추가
- `infra/localstack-init/01-create-queue.sh` (신규 — scoring-queue 생성)
- `podo/apps/api/prisma/schema.prisma` — scoring_jobs 모델 + Resume.scoring_jobs 역참조
- `podo/apps/api/prisma/migrations/20260607130324_add_scoring_jobs/migration.sql` (신규)
- `podo/apps/api/src/queue/queue.service.ts` · `queue.module.ts` (신규)
- `podo/apps/api/src/scoring-jobs/scoring-jobs.controller.ts` · `scoring-jobs.module.ts` (신규)
- `podo/apps/api/src/resumes/resumes.service.ts` — WorkerRunner→QueueService, score()가 scoringJob 생성+enqueue+queued 반환
- `podo/apps/api/src/resumes/resumes.controller.ts` — score 202 + ScoreResult(job_id) 반영
- `podo/apps/api/src/resumes/resumes.module.ts` — QueueModule import, WorkerRunner provider 제거
- `podo/apps/api/src/resumes/worker-runner.port.ts` (삭제 — subprocess spawn 제거, F-017 FAC-6)
- `podo/apps/api/src/app.module.ts` — ScoringJobsModule 등록
- `podo/apps/api/test/queue.spec.ts` (신규)
- `podo/apps/api/test/resumes.spec.ts` — WorkerRunner→noopQueue, 폐기된 T-037 subprocess 트리거 테스트 제거(큐로 이관)
- `podo/apps/api/test/auth.spec.ts` — WorkerRunner→noopQueue(ResumesService 시그니처 변경 ripple)
- `podo/apps/api/package.json` + `pnpm-lock.yaml` — @aws-sdk/client-sqs 추가

## 5. 완료 조건
`POST /resumes/:id/score`가 SQS enqueue 후 즉시 202 + job_id를 반환하고, `GET /scoring-jobs/:id`로 상태를 폴링할 수 있다. api 코드에 subprocess spawn이 존재하지 않는다. LocalStack 큐에 메시지가 전달됨을 확인.

## 6. Acceptance Criteria
- AC-1 [Given] 인증 사용자의 `POST /resumes/:id/score` [When] 요청 [Then] 202 + `{ job_id, status: 'queued' }`를 즉시 반환하고 LocalStack SQS 큐에 메시지가 전달되며 `scoring_jobs`에 `queued` 행이 생성된다.
- AC-2 [Given] job_id [When] `GET /scoring-jobs/:job_id` [Then] 현재 `status`(`queued/running/done/failed`)를 반환하고 타 사용자 job 조회 시 404를 반환한다.
- AC-3 [Given] api 소스 전체 [When] `grep -r "uv run python" podo/apps/api/src` [Then] 결과 0건으로 subprocess spawn 코드가 제거됐다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/api/test/queue.spec.ts::test_AC_1_score_endpoint_enqueues_and_returns_202_queued
- AC-2 → vitest::podo/apps/api/test/queue.spec.ts::test_AC_2_scoring_jobs_polling_returns_status_and_blocks_cross_user
- AC-3 → vitest::podo/apps/api/test/queue.spec.ts::test_AC_3_no_subprocess_spawn_in_source

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Feature: [F-017-worker-trigger-queue](../features/F-017-worker-trigger-queue.md)
- Architecture-Iface: [ARCH ## 7-3 백엔드/워커](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 8. 메모
- **엔드포인트(검증 2026-06):** AWS SDK v3는 **`AWS_ENDPOINT_URL` env를 native 지원**(LocalStack 시 `http://localhost:4566`, 미설정 시 실 AWS) — 코드 분기 0(ADR-106 "엔드포인트만 교체"). 본 task의 명시적 `SQS_ENDPOINT_URL`도 동등(SQSClient `endpoint`로 주입).
- **큐 URL 해석:** 하드코딩 대신 **`SQS_QUEUE_URL` env**(로컬=`http://localhost:4566/000000000000/scoring-queue`, 프로덕션=T-082 IaC output) 또는 startup 시 `GetQueueUrlCommand({QueueName:'scoring-queue'})`로 해석. 인터컨테이너는 host=`localstack`(compose 서비스명).
- LocalStack 이미지: `localstack/localstack:3` 동작, **v4 가용**(major 핀 권장 — 셋업 시 결정). 큐 생성 = init 스크립트 `awslocal sqs create-queue`(공식 방식 — `/etc/localstack/init/ready.d`).
- **상태 갱신 메커니즘(확정 — 단일 writer):** `scoring_jobs`는 **api 단일 소유**. worker는 직접 write 금지(ARCH §3-2). worker가 **상태 큐(`scoring-status-queue`)에 `{job_id, status}` 이벤트**(running on pickup / done|failed on 완료)를 전송 → **api의 경량 status consumer**가 받아 `scoring_jobs.status` 갱신. (`ranking_runs 존재=done`만으론 running/failed 불가하므로 상태 큐로 일원화 — T-045가 emit.) `GET /scoring-jobs/:id`는 그 테이블을 읽음.
- 메시지 페이로드에 계정 PII(email 등) 절대 미포함(ADR-105 Amend1).
- **구현 결정(implement): 상태 갱신 = 별도 status 큐/consumer 미도입, T-045 §8의 join 기반(ranking_run 존재=done)으로 일원화** (ADR-006 단순성 — T-044 scope의 "scoring-status-queue + api status consumer"는 T-045 §8 결정과 충돌하므로 후자 채택). 따라서 LocalStack은 `scoring-queue` 단일 큐만 생성, scoring_jobs.status는 enqueue 시 `queued` 기록, `GET /scoring-jobs/:id`는 저장된 status 반환(running/done/failed 전이는 T-045가 join으로 계산). 무한 폴링 background service 미추가.
- 구현 결정(implement): score 트리거 계약이 동기 `{status:'scored'}` → 비동기 202 `{job_id,status:'queued'}`로 바뀌어 ResumesService 생성자(WorkerRunner→QueueService)가 변경됨 → resumes.spec(T-037 트리거 테스트 폐기)·auth.spec(생성자 인자) ripple 수정. worker-runner.port.ts 삭제(F-017 FAC-6 — api에 subprocess spawn 0).
- 검증(implement): `pnpm --filter @podo/api test` 31 passed(podo_test DB 포함) · tsc green · `pnpm validate` green. 실 LocalStack enqueue 왕복은 T-045(소비)·T-052(E2E)에서 실증.

## 9. 의존성
- depends_on: [T-042]
- read_set: ["podo/apps/api/prisma/schema.prisma", "podo/apps/api/src/resumes/**", "infra/docker-compose.yml"]
- write_set: ["infra/docker-compose.yml", "infra/localstack-init/**", "podo/apps/api/prisma/schema.prisma", "podo/apps/api/prisma/migrations/**", "podo/apps/api/src/queue/**", "podo/apps/api/src/resumes/resumes.controller.ts", "podo/apps/api/src/scoring-jobs/**", "podo/apps/api/src/app.module.ts", "podo/apps/api/test/queue.spec.ts", "podo/apps/api/package.json", "pnpm-lock.yaml"]
- assumptions: ["T-042 스키마 마이그레이션 적용됨", "Docker+LocalStack 로컬 실행 가능", "SQS_ENDPOINT_URL 환경변수 설정"]
- verifier: "pnpm --filter @podo/api test"
