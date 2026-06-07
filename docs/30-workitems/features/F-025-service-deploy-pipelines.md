# F-025-service-deploy-pipelines: api/worker/crawler 호스팅 + GHA 배포 + 매일 오전 크롤 cron

## 0. Status
draft

> **잠정 (M6).** 알림 *발송* 기능은 비범위 — 본 feature의 cron은 *크롤링* cron만.

## 0-1. Type
technical-enabler

## 1. 요약
**api·worker = AWS 호스팅**(ECS/Fargate vs Lambda vs EC2 — ADR), **crawler = GitHub Actions cron**으로 실행. GitHub Actions `deploy-api`·`deploy-worker`·`crawl-jobs`·`schema-contract`·`e2e-smoke` 워크플로를 실가동한다. **`crawl-jobs` 매일 오전 cron**이 신규 공고를 수집해 `diff_status`를 갱신 → 사용자가 진입 시 신규/마감이 반영된 피드를 본다. **이메일/푸시 알림 *발송*은 비범위(나중).**

## 2. 기술적 근거 (Technical rationale)
**무엇을:** api(NestJS)·worker(Python consumer)는 AWS에 호스팅, crawler(Python)는 GitHub Actions cron으로 실행하며, **`crawl-jobs`를 매일 오전 cron으로 실가동**(M4가 UI만 준비한 신규/마감 diff 트리거를 실제로 켬)한다.
**서비스하는 결정:** [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)(D-DEPLOY: crawler=GHA cron, web=Vercel) · ADR(AWS 호스팅 — M6).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. main 머지 → GHA가 api/worker 배포.
2. 매일 오전 `crawl-jobs` cron → 공식 소스 수집 → `job_postings` upsert + diff.
3. worker consumer가 SQS 채점 메시지 소비(상시).
4. 사용자 진입 → 신규/마감 반영된 피드.
### Fail path
1. 🔴 크롤 실패 → 커버리지 패널에 노출(조용한 실패 금지, Fail #3) + 로그/알람.
2. 🔴 배포 실패 → 롤백 + green 게이트(schema-contract/e2e-smoke).

## 4. 범위
- **api·worker = AWS 호스팅**(실행 단위 — ADR로 ECS/Lambda/EC2 확정), worker는 상시 SQS consumer(F-017). **crawler = GitHub Actions cron job으로 직접 실행**(AWS 호스팅 서비스 아님 — ARCH §7-3/ADR-101 D-DEPLOY). *AWS task를 GHA가 호출하는 변형은 AWS 호스팅 ADR에서 확정.*
- **단일 worker로 시작**(다중 인스턴스·공유 캐시는 F-027, 본 feature 후행 — 순환 의존 차단).
- GHA: deploy-api·deploy-worker·crawl-jobs(cron)·schema-contract·e2e-smoke 실가동.
- **매일 오전 크롤 cron** + 실패 로깅/가시화.
- 배포 게이트(schema-contract·e2e-smoke green 필수).

## 5. 비범위
- **이메일/푸시 알림 발송 기능 — 비범위(나중).** cron은 *수집*만.
- web 배포 — F-026(Vercel, 사용자 직접).
- 새 기능 — M4/M5.
- 오토스케일·멀티리전 — 최소 구성.

## 6. 요구사항
- ADR-101 D-DEPLOY 정합(api/worker/crawler=GHA, web=Vercel 분리).
- 크롤 실패 가시화(커버리지 패널·로그).
- 배포 전 schema-contract·e2e-smoke green.
- worker는 SQS consumer 상시(F-017).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** GHA가 api/worker를 AWS에 배포하되 **배포 전 `schema-contract` gate가 green**(pre-deploy)이고, **`e2e-smoke`는 배포 후 검증**(post-deploy)으로 동작한다(순환 없음 — round2/3 정합).
- **FAC-2:** `crawl-jobs` cron이 매일 오전 공식 소스를 수집해 `diff_status`(신규/마감)를 갱신한다.
- **FAC-3:** 크롤 실패 시 커버리지 패널/로그에 노출되고 "전부 수집" 거짓 인상이 없다(Fail #3).
- **FAC-4:** worker가 AWS에서 SQS consumer로 상시 동작하며 채점이 큐 경유로 완주한다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-084:AC-1(schema-contract pre-deploy gate `needs`), T-086:AC-1(post-deploy e2e-smoke)
- FAC-2 → T-085:AC-1
- FAC-3 → T-085:AC-3
- FAC-4 → T-086:AC-1, T-084:AC-3

## 8. Non-functional Requirements
- 운영성: 크롤 실패율·캡차율·큐 지연 로깅/알람.
- 신뢰성: 배포 게이트로 회귀 차단. cron 누락 감지.
- 보안: 배포 자격증명 시크릿(F-024).

## 8-1. UX 흐름 품질
(해당 없음 — 배포/오케스트레이션. 사용자엔 신규/마감 반영 피드.)

## 9. 엣지 케이스
- cron 시각에 소스 장애 → 부분 수집 정직 고지.
- 배포 중 마이그레이션 필요 → schema-contract green 후 진행.
- worker 다중 인스턴스 → 공유 캐시(F-027) 필요.

## 10. 의존성
- 선행: F-024(인프라)·F-017(worker consumer). **F-027은 선행 아님 — 본 feature(단일 worker 배포)가 F-027(공유 캐시·다중화)의 선행**(순환 의존 제거).
- 상위: ADR-101·ADR(AWS 호스팅).

## 11. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-3 cron·워커, §6 외부 연동)
- Architecture-Iface: [ARCH ## 7-3 cron·워커](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) · [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md)

## 12. 열린 질문 (논의 전제)
- 호스팅 = ECS/Fargate vs Lambda vs EC2(비용·콜드스타트·SQS 상시 소비 정합).
- cron 시각·타임존(오전 첫 진입 전 반영).
- 배포 전략(blue-green vs rolling) — 단순성 우선.
