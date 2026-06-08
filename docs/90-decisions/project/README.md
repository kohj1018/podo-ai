# Project ADR Index

> 이 디렉터리는 fork된 프로젝트의 자체 결정 ADR을 박는 영역.
> 첫 ADR은 ADR-100부터 시작 (정책: [boilerplate/ADR-000](../boilerplate/ADR-000-boilerplate-decision-policy.md)).

## ADR 목록

`area`=product/design/dev/infra/process/tooling. `superseded`된 ADR은 상태 컬럼에 표기하고 상단 '대체: ADR-NNN' 링크로 supersession 추적(폴더 이동 X). 연 1회 `last-reviewed` 갱신 권장.

| # | 제목 | 상태 | area | last-reviewed | 한 줄 요약 |
|---|------|------|------|---------------|-----------|
| [100](ADR-100-initial-project-decisions.md) | 초기 프로젝트 결정 (수집+fit/합격가능성 SaaS) | accepted | product | 2026-06-04 | 신뢰 게이트 우선(D1) · 4-layer 미채택/모듈 의존성 규칙(D2) · 결정론 캐시로 GS-1 보증(D3) |
| [101](ADR-101-stack-selection.md) | 스택 선택 (폴리글랏 모노레포 — TS web/api + Python worker/crawler) | accepted | infra | 2026-06-04 | 폴리글랏 TS+Python(D-LANG) · turbo는 podo/만/uv workspace 분리(D-MONO) · Prisma SSOT+DDL/DML 분리(D-DB) · 계약 3규칙으로 R6 가드(D-CONTRACT) |
| [102](ADR-102-python-test-layout.md) | Python 테스트 레이아웃 + 검증 설정 컨벤션 | accepted | tooling | 2026-06-05 | co-located 패키지 테스트 + 중앙 foundational(D1) · test 디렉터리 `__init__.py` 없음+importlib(D2) · mypy strict는 test 제외(D3) · ruff E501 test 제외(D4) · 구현 src-layout(D5) |
| [103](ADR-103-eval-worker-boundary.md) | eval↔worker 의존 경계 — eval은 worker 공개 심볼만 의존 | accepted | dev | 2026-06-06 | eval은 worker public만 import(D1) · grounding을 공개 `worker.grounding` 모듈로 승격(D2) · 단순 alias 기각(D3). 구현: M2 F-011 |
| [104](ADR-104-worker-shared-util-boundary.md) | worker 공통 util 경계 — cross-module util은 leaf 모듈로 중앙화 | accepted | dev | 2026-06-06 | leaf 중앙화·로컬복사 금지(D1) · `_json_util`(D2)·`_prompts`(D3)·`DOM_RANK` 단일출처(D4). 구현: M2 F-011 |
| [105](ADR-105-pii-masking-policy.md) | PII 마스킹 정책 (+Amend1 계정 PII) | accepted | dev | 2026-06-07 | 이력서 직접 식별자 rule-based 마스킹·raw→외부 LLM 금지 · Amend1: 계정 PII 마스킹 X·`users` 최소저장·스코어링 경로 유입금지·간접 재식별→M6. 구현: M3 F-014 / M4 F-016 |
| [106](ADR-106-worker-trigger-boundary.md) | 워커 트리거 경계 — 큐(SQS) 기반 비동기 채점 | accepted | infra | 2026-06-07 | subprocess spawn 폐기→큐 enqueue(D1) · SQS LocalStack→AWS 동일경로(D2) · 작업 상태머신(D3) · 결정론 보존(D4). 구현: M4 F-017 |
| [107](ADR-107-oauth-multiuser.md) | OAuth 멀티유저 + Charter 멀티유저 비목표 반전 | accepted | product | 2026-06-07 | 멀티유저 채택(협업은 비범위, D1) · OAuth GitHub+Google(D2) · httpOnly 쿠키세션(D3) · `user_id` 격리·횡단접근 차단(D4) · 테스트 인증우회(D5). 구현: M4 F-016 |
| [108](ADR-108-scoring-candidate-prefilter.md) | 스코어링 비용 구조 — 벡터+하이브리드 후보 사전필터(N→K) | accepted | dev | 2026-06-07 | `job_embeddings`만 영속(구조화JD는 디스크캐시, D1) · 벡터∪도메인∪스킬 합집합 recall우선(D2) · coarse/deep 물리분리·유사도는 적합도 아님(D3) · 파이프라인 본체 불변 입력만 K(D4) · 증분(D5) · GS-1 버전핀(D6) · 티어링은 측정후(D7). 구현: M5 F-021 |
| [109](ADR-109-aws-hosting-topology.md) | M6 AWS 호스팅 토폴로지 — Fargate 상시 api/worker · NAT 없는 public subnet · RDS private 최소 | accepted | infra | 2026-06-08 | api·worker Fargate 상시1(on-demand UX 우선, scale-to-zero 기각 D1) · NAT 미사용·public subnet+assignPublicIp(D2) · RDS private·t4g.micro·백업 없음(유실 risk accepted D3) · 보안 SG/private RDS/Secrets로 보상(D4) · scale-to-zero는 후속 옵션(D5). 구현: M6 F-024 |
