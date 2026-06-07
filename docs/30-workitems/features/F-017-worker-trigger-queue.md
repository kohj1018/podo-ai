# F-017-worker-trigger-queue: 채점 트리거 큐(SQS) 비동기화 + 워커 서비스화

## 0. Status
draft

## 0-1. Type
technical-enabler

## 2. 기술적 근거 (Technical rationale)
**무엇을:** M3의 NestJS→`uv run python -m worker --resume-id N` **subprocess spawn**(로컬 임시)을 **큐(SQS) 기반 비동기 트리거**로 교체하고, worker를 큐 소비 *상시 서비스*로 전환한다.
**왜:** ① ARCH §7-3 "api 미트리거" 경계 위반(REV-M3-002) 복원, ② F-016 멀티유저의 *동시 채점*을 subprocess가 못 버팀, ③ M6 컨테이너 분리 시 subprocess spawn은 동작 불가. LocalStack SQS(로컬)→AWS SQS(M6)로 *연습=실전* 동일 경로.
**서비스하는 결정:** [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md)(워커 트리거 경계) 구현. 멀티유저 동인 = [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md).

## 1. 요약
api는 채점 요청을 **SQS에 enqueue**하고 즉시 반환(작업 id/상태 제공). Python worker는 **boto3로 큐를 소비**하는 상시 consumer로 동작하며, 메시지마다 `run_scoring`→`persist_run`을 수행한다. **작업(채점 run) 상태 = `queued→running→done|failed`** 이고, **개별 공고의 `scored|held`는 `recommendations` 레벨**(작업 상태와 구분 — held는 LLM miss 공고이지 작업 실패가 아님). 결정론(GS-1)·캐시 키·`held` 처리·`ranking_runs` 복합 unique는 불변 — 트리거 방식만 바뀐다. 로컬은 LocalStack SQS, M6은 AWS SQS(엔드포인트만 교체).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 사용자가 "이 이력서로 분석" → api가 소유권 인가(F-016) 후 SQS에 채점 메시지 enqueue + 작업 `queued` 기록.
2. api는 즉시 202/작업 id 반환(블로킹 X) → UI는 진행 상태 폴링/표시.
3. worker consumer가 메시지 수신 → `running` → `run_scoring`(웜캐시/LLM) → `persist_run` → `done`.
4. UI가 완료를 감지 → 피드에 적합도 배지·근거 렌더(F-018).
### Alternate path
1. 동일 (이력서, 공고집합) 재요청 → 캐시 hit으로 결과 동일(GS-1) — 재채점도 큐 경유 일관.
2. 동시 다수 사용자 요청 → 큐에 버퍼링되어 순차/병렬(동시성 한도) 소비.
### Fail path
1. 🔴 일부 공고 LLM miss → 해당 공고만 `held`(fit_level NULL), 작업은 `done`(가짜 점수 금지, 기존 불변식).
2. 🔴 worker 처리 중 예외 → 재시도(backoff), 한도 초과 시 작업 `failed` + 가시화(조용한 실패 금지).
3. 🔴 메시지 중복 수신 → 멱등(복합 unique upsert)으로 결과 1행 유지.

## 4. 범위
- api: 채점 enqueue(AWS SDK, SQS) + 작업 상태 read 엔드포인트 + 소유권 인가 결선(F-016).
- worker: `__main__` 일회성 실행 → **SQS consumer 상시 서비스**(boto3 long-poll) 전환. 기존 `run`/`persist_run` 재사용.
- 작업 상태 저장: **작업(채점 run) 상태 = `queued/running/done/failed`** (개별 공고 `scored/held`는 `recommendations` 레벨, 작업 상태 아님). **상태 테이블은 단일 writer(ARCH §3-2)** — api 소유(폴링 대상)로 두고 worker는 자기 소유 테이블(`ranking_runs`)만 쓴다. 완료는 **큐 완료 메시지 또는 산출물(`ranking_run`) 존재**로 api에 전달 → api가 상태 갱신(worker의 상태 테이블 직접 write = shared-write 금지). 구체 store는 plan.
- 재시도/backoff + dead-letter(한도 초과) 정책.
- 로컬 인프라: `infra/docker-compose`에 LocalStack SQS 큐 + worker 서비스 컨테이너.
- `scripts/e2e.mjs` 재배선: 업로드→**enqueue→큐 드레인 대기**→피드 assert(무키 웜캐시 경로 보존).
- subprocess spawn 코드 제거(M3 임시).

## 5. 비범위
- 실 AWS SQS·IAM 결선 — M6(엔드포인트 교체만).
- 우선순위 큐·요금제별 동시성·rate limiting — YAGNI(단일 등급).
- 알고리즘/캐시 키 변경 — SPEC SSOT 불변(M5도 출력계약 동결).
- 작업 진행률(%)·실시간 푸시 — 폴링으로 충분(알림 기능은 M6+ 비범위).

## 6. 요구사항
- 트리거 = SQS enqueue(api)/consume(worker), LocalStack→AWS 동일 코드(ADR-106 D2).
- worker = 상시 consumer(ADR-106 D1). 작업 상태머신(D3).
- 결정론 보존(ADR-106 D4): 캐시 키·`held`·복합 unique upsert 불변. 동일 입력→동일 결과.
- 멱등 소비(중복 메시지 안전). 실패 가시화(조용한 실패 금지 — Charter Fail #2 정신).
- 무키 E2E: 큐 드레인까지 포함해 `pnpm e2e` exit 0(웜캐시).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** 채점 요청 시 api가 SQS에 메시지를 enqueue하고 즉시(블로킹 없이) 작업 id/`queued`를 반환한다.
- **FAC-2:** worker consumer가 메시지를 소비해 `run_scoring`→`persist_run`을 수행하고 **작업 상태를 `done`**(실패 시 `failed`)으로 갱신한다. **개별 공고는 `recommendations`에 `scored`/`held`(LLM miss)**로 기록된다(작업 상태와 공고 상태 분리 — 작업은 `held` 상태를 갖지 않는다).
- **FAC-3:** 동일 (이력서, 공고집합)을 큐 경로로 2회 채점하면 저장된 result/recommendations가 변동 0(캐시 hit, GS-1-through-queue).
- **FAC-4:** 메시지 중복 수신 시에도 `ranking_runs` 복합 unique로 결과가 1행만 유지된다(멱등).
- **FAC-5:** 무키 `pnpm e2e`가 업로드→enqueue→큐 드레인→피드 적합도 배지 assert까지 exit 0(웜캐시, 외부 LLM 0).
- **FAC-6:** api 코드에 subprocess spawn(`uv run python -m worker`)이 더는 존재하지 않는다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-044:AC-1
- FAC-2 → T-045:AC-1, T-045:AC-3, T-045:AC-4
- FAC-3 → T-045:AC-2
- FAC-4 → T-045:AC-2
- FAC-5 → T-052:AC-1
- FAC-6 → T-044:AC-3

## 8. Non-functional Requirements
- 신뢰성: 재시도/dead-letter로 메시지 유실 0. 결정론(GS-1) 큐 경로 보존.
- 운영성: 작업 상태·실패가 조회 가능(가시화). 큐 깊이/소비 지연 로깅(M6 알람의 토대).
- 보안: enqueue 전 소유권 인가(F-016). 메시지에 raw/계정 PII 미포함.

## 8-1. UX 흐름 품질
(해당 없음 — 오케스트레이션 레이어. UI 진행 표시는 F-018 LoadingState가 담당.)

## 9. 엣지 케이스
- 큐는 비었는데 worker만 떠 있음 → long-poll idle(정상).
- 채점 중 이력서 교체/삭제 → 작업 무효화 또는 stale 결과 폐기 정책(plan).
- LocalStack 재시작으로 큐 소실 → 로컬 개발 한정, 재enqueue로 복구.
- 매우 큰 공고집합 → 단일 메시지 vs 분할(현재 공고 수 적어 단일, M5 대량 시 재검토).

## 10. 의존성
- 상위: [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md).
- 선행: F-016(소유권 인가가 enqueue 전제).
- 후행: F-018(작업 상태로 LoadingState/피드 갱신).
- M5 대량 채점(증분/벡터 prefilter)이 본 트리거 위에 얹힘 — 메시지 단위 설계 시 고려.

## 11. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-3 백엔드/워커](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (A-INFRA)

## 12. 열린 질문
- 작업 상태 저장 = `scoring_jobs` 테이블이면 **api 단일 소유**(ARCH §3-2 — UI 폴링 대상) + worker는 직접 write 안 함(완료는 큐/산출물로 전달). shared-write(worker가 상태 컬럼 갱신)는 단일-writer 규칙 위반 → 필요 시 ARCH 개정 선행. SQS 메시지 속성/별도 store 대안은 plan.
- worker 동시성 한도(메시지 병렬 처리 수) — 로컬 자원 기준 기본값, plan.
- enqueue↔consume 메시지 스키마(resume_id·job_set·ranking_mode) 버전 핀.
