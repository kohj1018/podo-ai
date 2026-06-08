# ADR-109 — M6 AWS 호스팅 토폴로지 (Fargate 상시 api/worker · NAT 없는 public subnet · RDS private 최소사양)

## Status
accepted

> **결정 2026-06-08 (사용자 승인).** M6 §7 열린질문(호스팅 방식·worker 상시 여부·NAT·RDS 사양)을 비용 외부 리뷰(2026-06-08) + on-demand UX 우선 판단으로 확정한다. M6 진입(`/plan-workitem M6`) 전 T-082/T-083/T-089가 본 ADR을 따른다.

## Context
[관측됨 — 아키텍처 비용 리뷰 2026-06-08] M6은 LocalStack/로컬 Docker가 대역하던 인프라를 실 AWS로 옮긴다(M6 §1). M6 §7이 "api/worker 호스팅 = ECS/Fargate 기본 가정, worker 상시 consumer"를 *열린 질문*으로 남겼다. 비용 관점 검토에서 두 항목이 식별됐다.

1. **worker 상시 Fargate** — 트래픽이 적으면 "일 안 하는데 컨테이너가 24h 과금". scale-to-zero(SQS depth 오토스케일) 또는 scheduled run-task가 비용상 유리.
2. **NAT Gateway** — private subnet의 worker가 OpenAI(외부)를 호출하려면 통상 NAT가 필요한데, NAT는 *UX 기여 0 + 고정비(~$32/월) + 처리 GB당 과금*.

단, 본 제품의 채점은 **on-demand**다 — 이력서 업로드 직후 사용자가 결과를 기대한다("분석 중" 화면). worker를 scale-to-zero로 두면 SQS-depth 오토스케일의 알람 주기(~1분) + Fargate task 기동(~1~2분) = **메시지 도착→채점 시작 2~3분 cold-start**가 UX에 치명적이다. 절약분(가장 작은 Fargate 기준 ~$9~15/월)은 NAT($32)보다 작은 레버이면서 UX 비용은 더 크다. MVP는 비용최소 우선이되, *비용 레버 크기와 UX 비용을 함께* 가늠해 결정한다(사용자 판단 2026-06-08).

## 결정

### D1. api·worker 둘 다 ECS/Fargate 상시 1 task (worker scale-to-zero 기각)
- api·worker를 **ECS/Fargate desired count 1 상시**로 둔다. worker scale-to-zero는 *기본값으로 두지 않는다* — on-demand 채점에서 cold-start 2~3분이 즉시성 기대를 깬다.
- Lambda 기각: worker는 상시 SQS consumer + Python/NestJS 컨테이너라 Fargate에 자연. (Lambda는 cold-start·15분 한도·컨테이너 패키징 마찰.)

### D2. NAT Gateway 미사용 — api/worker public subnet + assignPublicIp
- **NAT Gateway를 생성하지 않는다.** UX 기여 0 + 고정비. api/worker를 **public subnet**에 두고 `assignPublicIp=ENABLED`로 outbound(OpenAI·AWS API·ECR 이미지 pull)를 public IP 경유 처리한다.
- inbound는 보안그룹으로 제한 — api는 **ALB**를 통해서만, worker는 **inbound 없음(outbound 전용)**.

### D3. RDS private subnet + 최소사양 + 백업 미사용
- RDS는 **private DB subnet group**에 둔다 — **절대 public 금지**. rds-sg ingress = api-sg·worker-sg source만(5432), `0.0.0.0/0` 금지.
- 사양: **db.t4g.micro**(또는 t3.micro), **Multi-AZ off**, **자동 백업 미사용(`backup_retention_period=0`)**. 비용최소 우선 — *데이터 유실 risk를 MVP에서 accepted*로 받는다(트래픽·데이터 가치 상승 시 백업·Multi-AZ 활성).

### D4. 보안 보상 — public subnet 다운그레이드를 SG·private RDS·시크릿으로 상쇄
- public subnet Fargate(public IP)는 보안 포스처 하향이다. 보상: ① SG inbound 최소화(api=ALB만·worker=inbound 없음), ② RDS private, ③ 시크릿=Secrets Manager, ④ 노출면을 ALB+api로 한정.
- **T-089(보안 하드닝)에 accepted-risk로 명문화** — "NAT 없는 public subnet은 의식적 비용/보안 트레이드오프"임을 잊지 않게 박는다.

### D5. scale-to-zero / scheduled run-task는 후속 비용최적화 옵션 (M6 미구현)
- 트래픽 증가 또는 채점을 *batch*(밤에 cron이 몰아서)로 전환하면 worker를 **desired=0 + SQS-depth 오토스케일** 또는 **scheduled `run-task`**로 전환한다. 본 ADR은 그 경로를 *문서화*만 하고 M6에서 구현하지 않는다(YAGNI — ADR-006).

## 근거
- 비용 외부 리뷰 + on-demand UX 우선(사용자 판단 2026-06-08). **레버 크기·UX 비용을 함께** 평가: NAT는 큰 레버(고정 $32)·UX비용 0 → 무조건 제거. worker 상시는 작은 레버($9~15)·UX비용 큼 → 유지. 둘을 같은 무게로 두지 않는다.
- RDS·Fargate 상시는 제품 중심 저장소·즉시 채점이라 불가피한 베이스. 백업 미사용은 *복구보다 비용*을 우선한 MVP 한정 선택(가역 — 켜면 됨).

## 결과
- (+) NAT 고정비 0 · RDS 백업비 0 · 단순 1-tier 네트워킹(IGW만).
- (+) on-demand 채점 즉시성 보존(worker warm — cold-start 없음).
- (−) api/worker public IP → 보안 포스처 하향(SG·private RDS·Secrets Manager로 보상, T-089 accepted-risk).
- (−) RDS 백업 없음 → 데이터 유실 risk(MVP accepted; 데이터 가치 상승 시 백업 켜기).
- 월 비용 감각(리전·사용량 의존, AWS Pricing Calculator로 확정): NAT 제거로 ~$32 절감 → RDS(t4g.micro)+Fargate api/worker 상시로 대략 **$35~70대**. SQS/Secrets/ECR/CloudWatch는 초반 수 달러 이내. OpenAI는 사용량 별도.

## Surfaces
- `infra/aws/` — T-082(RDS `backup_retention_period=0`·private subnet·SQS·Secrets), T-083(public subnet api/worker·private DB subnet·NAT 없음·SG·IAM).
- T-089 — public-subnet/no-NAT accepted-risk 명문화.
- M6 §7 열린질문 해소.

## 후속 작업
- worker scale-to-zero / scheduled run-task 전환(트래픽 증가 또는 batch 채점 전환 시) — D5.
- RDS 자동 백업·Multi-AZ 활성화(데이터 가치 상승 시) — D3.
- VPC endpoint(SQS/Secrets/ECR interface endpoint)로 AWS 서비스 호출의 보안·비용 개선(선택; OpenAI egress는 여전히 public IP 필요).

## 관련 문서
- Milestone: [M6-deployment](../../30-workitems/milestones/M6-deployment.md) (§1 목적, §7 열린질문)
- ADR: [ADR-101](ADR-101-stack-selection.md)(D-DEPLOY 호스팅 방향) · [ADR-106](ADR-106-worker-trigger-boundary.md)(SQS 큐 경계)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 물리 배치, §7-3 백엔드/인프라)
- Tasks: [T-082](../../30-workitems/tasks/T-082-rds-sqs-secret-provisioning.md) · [T-083](../../30-workitems/tasks/T-083-iac-networking-and-iam.md) · [T-089](../../30-workitems/tasks/T-089-prod-security-hardening.md)
