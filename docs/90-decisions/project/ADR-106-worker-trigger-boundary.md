# ADR-106 — 워커 트리거 경계 (큐 기반 비동기 채점)

## Status
accepted

## Context
M3에서 NestJS(api)가 채점을 트리거하려고 `uv run python -m worker --resume-id N`을 **subprocess로 직접 spawn**한다(로컬 단일프로세스 임시 결정 — T-037).
- ARCH §7-3은 "api = user-facing CRUD + Worker 산출물 *서빙*, ranking/score *미계산·미트리거*"로 경계를 박았는데 subprocess spawn은 이를 새로 위반한다(REV-M3-002가 P1 + "ADR 미신설"으로 플래깅).
- **M4가 멀티유저(ADR-107)를 도입**하면 동시 채점 요청이 들어오는데, 요청마다 subprocess를 띄우면 자원이 폭증한다.
- **M6가 컨테이너 분리(AWS)**되면 api와 worker가 다른 실행 단위라 subprocess spawn은 *동작 자체가 불가*하다.

즉 채점 트리거 경계를 M4에서 비동기 큐 방식으로 교체해야 멀티유저와 배포를 동시에 받아낸다.

## 결정

### D1. 트리거 = 비동기 큐 (subprocess spawn 폐기)
api는 더 이상 worker를 직접 실행하지 않는다. **채점 요청을 큐에 enqueue**하고 즉시 반환한다. **worker는 큐를 소비하는 상시 서비스**로 전환한다(일회성 `--resume-id` 프로세스 → 장기 실행 consumer). ARCH §7-3의 "api 미트리거" 경계를 *복원*한다(api는 enqueue만, 계산·트리거는 큐 경유).

### D2. 큐 구현 = SQS (LocalStack 로컬 → AWS 프로덕션)
- 로컬(M4/M5)은 **LocalStack SQS**, 프로덕션(M6)은 **AWS SQS** — *엔드포인트만 교체*하고 코드 경로는 동일(연습=실전).
- **폴리글랏 친화**: NestJS(TS)는 AWS SDK로 enqueue, Python worker는 boto3로 consume. Node 전용 큐(pg-boss/BullMQ)는 Python 소비가 부자연스러워 기각.

### D3. 채점 작업 상태머신
채점 작업은 `queued → running → done | held`로 추적한다(상태 저장 위치·스키마는 F-017 구현에서 확정 — Prisma 소유 테이블 또는 SQS 메타). 실패는 재시도하되, LLM miss 공고는 기존대로 `held`(가짜 점수 금지).

### D4. 결정론 보존
큐 경유는 *트리거 방식*만 바꾼다. 캐시 키(이력서 정규화본·JD·모델·프롬프트 버전)·`ranking_runs` 복합 unique·`.cache/llm`은 불변 — 동일 입력 → 동일 결과(GS-1-through-DB)가 큐 경로에서도 보존된다.

## 근거
- **연습=실전(단순성)**: LocalStack→AWS 동일 경로라 M6 배포 시 트리거 재작성 0 (가정 A-INFRA 정합).
- **폴리글랏 비용 0 수렴**: SQS는 TS·Python 양쪽 1급 SDK가 있어 ARCH §3-2 폴리글랏 경계와 충돌 없음.
- **대안 비교**:
  - *Prisma `scoring_jobs` 테이블 폴링* — 가장 단순, 신규 인프라 0, DDL=Prisma 정합. **단 AWS 큐를 연습하지 못함**. (M4에서 SQS 도입이 부담이면 fallback 후보.)
  - *worker HTTP 서비스* — api가 직접 호출. 즉각적이나 버퍼/재시도 없음 → 동시 부하·실패 복원에 약함. 기각.
- REV-M3-002가 이미 요청한 부채를 닫는다.

## 결과
- api에서 subprocess spawn 코드 제거, worker 상시 consumer 전환.
- ARCH §7-3 본문에 "채점 트리거 = SQS enqueue(api) / consume(worker)" 반영.
- M6는 SQS 엔드포인트·IAM만 실 AWS로 교체.

## Surfaces
- [ARCHITECTURE_OVERVIEW §7-3](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3) — 트리거 경계 본문 갱신 (F-017 구현 시 `per ADR-106`).
- `ai/worker` 진입점 — consumer 전환.
- `podo/apps/api` resumes 모듈 — enqueue.

## 후속 작업
- **F-017 (worker-trigger-queue)** 이 본 ADR을 구현한다.
- 작업 상태 저장 스키마·재시도/backoff·dead-letter 정책은 F-017 plan에서 확정.

## 관련 문서
- [M4-product-mvp](../../30-workitems/milestones/M4-product-mvp.md) (§2 워커 트리거 비동기화)
- [ARCHITECTURE_OVERVIEW §7-3](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3) · §6(LocalStack→AWS SQS)
- [ADR-101](ADR-101-stack-selection.md) (D-DEPLOY·A-INFRA) · [ADR-107](ADR-107-oauth-multiuser.md) (멀티유저 동시 채점 동인)
- [IMPROVEMENT_GUIDE REV-M3-002](../../40-validation/IMPROVEMENT_GUIDE.md)
