# T-045-worker-sqs-consumer

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
Python worker의 일회성 `__main__` 진입점(`--resume-id` 인자)을 **SQS long-poll 상시 consumer**로 전환한다(ADR-106 D1). 메시지마다 기존 `run_scoring`→`persist_run`을 실행하고, 완료 시 api가 `scoring_jobs.status`를 갱신하도록 완료 메시지를 **완료 큐(또는 같은 큐의 완료 페이로드)**로 전송한다. 결정론·캐시 키·`held` 처리·복합 unique upsert 불변. T-044(SQS 큐) 선행.

## 2. 작업 범위
- `ai/worker/src/worker/__main__.py` 현재: `--resume-id` 인자 받아 1회 실행 → 변경: boto3 SQS long-poll 무한 루프(visibility timeout·backoff 재시도·dead-letter 한도 정책).
- 메시지 소비 흐름: receive → `status=running` 완료 메시지 enqueue(api용) → `run_scoring` → `persist_run` → `status=done` 완료 메시지 enqueue. 예외 시 backoff 재시도, 한도 초과 시 `status=failed` 메시지 enqueue.
- **api가 완료 메시지를 수신해 `scoring_jobs.status` 갱신**(worker는 `scoring_jobs`에 직접 write 금지, ARCH §3-2). 완료 큐 엔드포인트는 환경변수로. 대안: `ranking_runs` 존재로 api가 상태 폴링 시 done 판정(구현에서 선택).
- docker compose `worker` 서비스: `ai/` Python uv 컨테이너, LocalStack SQS 연결.
- 멱등 소비: `ranking_runs` 복합 unique upsert로 중복 메시지 → 1행.
- `pnpm e2e` 재배선: 업로드→enqueue→큐 드레인 대기→피드 assert(T-052 연계).

## 3. 구현 항목
1. `ai/worker/src/worker/__main__.py` — 현재: `argparse --resume-id` 1회 실행 → 변경:
   ```python
   # SQS consumer 상시 루프
   sqs = boto3.client('sqs', endpoint_url=os.getenv('SQS_ENDPOINT_URL'))
   queue_url = os.getenv('SQS_QUEUE_URL')
   while True:
       msgs = sqs.receive_message(QueueUrl=queue_url, WaitTimeSeconds=20, MaxNumberOfMessages=1)
       for msg in msgs.get('Messages', []):
           payload = json.loads(msg['Body'])  # { resume_id, job_id }
           _process(payload, sqs, queue_url)
           sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg['ReceiptHandle'])
   ```
   `_process(payload)`: (a) 완료 메시지 `status=running` → 완료 큐 enqueue; (b) `run_scoring(resume_id)` → `persist_run`; (c) 완료 메시지 `status=done` 전송. 예외 시 최대 3회 backoff, 초과 시 `status=failed` 전송. → 확인: 로컬 큐에서 메시지 소비 후 `ranking_runs` 생성. (AC-1, AC-2)
2. `ai/worker/src/worker/` — **`run_scoring`·`persist_run` 변경 없음**(결정론·캐시 키·held 불변. SPEC SSOT 불변). → 확인: 기존 pytest 모두 green. (AC-3)
3. `infra/docker-compose.yml` — `worker` 서비스 추가:
   ```yaml
   worker:
     build: ./ai
     command: uv run python -m worker
     environment:
       - SQS_ENDPOINT_URL=http://localstack:4566
       - SQS_QUEUE_URL=http://localstack:4566/000000000000/scoring-queue
       - DATABASE_URL=${DATABASE_URL}
     depends_on: [localstack, db]
   ```
   → 확인: `docker compose up worker` 후 consumer 루프 실행. (AC-1)
4. **worker가 상태 이벤트를 `scoring-status-queue`에 emit**(T-044 메커니즘): 메시지 pickup 시 `{job_id, status:'running'}`, 완료 시 `'done'`, 재시도 한도 초과 시 `'failed'`. **worker는 `scoring_jobs`에 직접 write 안 함**(api status consumer가 받아 갱신 — 단일 writer). → 확인: consume 후 상태 이벤트가 큐에 전송되고 api가 `/scoring-jobs/:id`를 `running`→`done`으로 갱신. (AC-1, AC-2, AC-4)
5. `ai/tests/test_worker_consumer.py` (신규) — AC-1(LocalStack 메시지 소비→ranking_run 생성), AC-2(동일 입력 2회→1행 upsert=GS-1-through-queue), AC-3(소비 후 scoring_jobs done 판정). → 확인: `pytest ai/tests/test_worker_consumer.py` green. (AC-1, AC-2, AC-3)

## 4. 제외 항목
- 실 AWS SQS(M6 엔드포인트 교체만). · 작업 진행률(%) push. · 동시성 다중 메시지 병렬(MaxNumberOfMessages=1로 시작). · run_scoring 알고리즘 변경(SPEC SSOT 불변).

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/__main__.py` — consumer 전환
- `infra/docker-compose.yml` — worker 서비스 추가
- `podo/apps/api/src/scoring-jobs/scoring-jobs.controller.ts` — ranking_runs join으로 done 판정
- `ai/tests/test_worker_consumer.py` (신규)

## 5. 완료 조건
worker가 SQS 메시지를 소비해 `run_scoring`→`persist_run`을 수행하고, `/scoring-jobs/:id` 폴링이 `done`을 반환한다. 동일 입력 2회 채점 시 `ranking_runs` 1행(멱등). `held` 공고는 `recommendations.status='held'`로 기록되고 작업은 `done`(가짜 점수 0). 기존 worker pytest 전부 green.

## 6. Acceptance Criteria
- AC-1 [Given] LocalStack SQS에 `{ resume_id, job_id }` 메시지 [When] worker consumer가 소비 [Then] `ranking_runs` + `recommendations` 행이 생성되고 `/scoring-jobs/:job_id` = `{ status: 'done' }`이다.
- AC-2 [Given] 동일 (resume_id, 공고집합)을 SQS 경로로 2회 채점 [When] 두 번째 소비 [Then] `ranking_runs` 복합 unique로 결과 1행만 존재하고 결과 값이 1회차와 동일하다(GS-1-through-queue, 캐시 hit).
- AC-3 [Given] LLM miss 공고가 포함된 채점 [When] worker 완료 [Then] 해당 공고 `recommendations.status='held'`(fit_level NULL)이고 작업 상태는 `done`이다(가짜 점수 없음).
- AC-4 [Given] worker 처리가 재시도 한도(3회) 초과로 실패하는 메시지 [When] consumer가 한도 초과 [Then] `status=failed` 완료 신호가 전송되고 `/scoring-jobs/:job_id`가 `failed`를 반환한다(무한 재시도 없이 종료).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/tests/test_worker_consumer.py::test_AC_1_consume_message_creates_ranking_run_and_job_done
- AC-2 → pytest::ai/tests/test_worker_consumer.py::test_AC_2_idempotent_two_consumes_one_row_gs1_through_queue
- AC-3 → pytest::ai/tests/test_worker_consumer.py::test_AC_3_held_jobs_done_no_fake_score
- AC-4 → pytest::ai/tests/test_worker_consumer.py::test_AC_4_failed_status_after_retry_limit

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Feature: [F-017-worker-trigger-queue](../features/F-017-worker-trigger-queue.md)
- Architecture-Iface: [ARCH ## 7-3 백엔드/워커](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md) · [ADR-103](../../90-decisions/project/ADR-103-eval-worker-boundary.md) · [ADR-104](../../90-decisions/project/ADR-104-worker-shared-util-boundary.md)

## 8. 메모
- worker는 `scoring_jobs`에 직접 write 금지(ARCH §3-2 단일 writer). 완료 신호 = `ranking_runs` 행 존재. api가 폴링 시 join으로 done 판정 — 별도 완료 큐 없이 산출물 존재 기반(단순성 우선, ADR-006).
- `SQS_ENDPOINT_URL` 미설정 시 실 AWS SQS(M6). 코드 분기 없음.
- `held` 처리 불변: 기존 `persist_run` 로직 그대로, 공고 status='held'는 recommendations 레벨.

## 9. 의존성
- depends_on: [T-044]
- read_set: ["ai/worker/src/worker/__main__.py", "ai/worker/src/worker/run_scoring.py", "ai/worker/src/worker/persist_run.py", "infra/docker-compose.yml"]
- write_set: ["ai/worker/src/worker/__main__.py", "infra/docker-compose.yml", "podo/apps/api/src/scoring-jobs/scoring-jobs.controller.ts", "ai/tests/test_worker_consumer.py"]
- assumptions: ["T-044 LocalStack SQS + scoring_jobs 테이블 존재", "웜캐시(.cache/llm) 존재(무키 E2E)", "기존 run_scoring·persist_run pytest green"]
- verifier: "pytest ai/tests/test_worker_consumer.py && pytest ai/tests/"
