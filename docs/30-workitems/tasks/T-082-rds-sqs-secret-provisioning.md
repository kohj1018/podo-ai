# T-082-rds-sqs-secret-provisioning

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
AWS RDS(Postgres+pgvector)·SQS·Secrets Manager·네트워킹을 IaC(`infra/aws/`)로 프로비저닝한다. LocalStack이 대역하던 DB/큐를 실 AWS 자원으로 교체하는 첫 단계. 가정 A-INFRA("실물 AWS 이전은 나중에")를 닫는다. [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)(D-DB·D-DEPLOY) · [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md)(SQS 엔드포인트 교체).

## 2. 작업 범위
- `infra/aws/` IaC 정의: RDS(Postgres+pgvector)·SQS 큐·Secrets Manager·보안그룹/IAM 최소권한·VPC 네트워킹.
- RDS에 `prisma migrate deploy` 적용(pgvector extension + HNSW raw SQL 포함).
- Secrets Manager에 `OPENAI_API_KEY`·`DATABASE_URL`·OAuth secret 등록(`.env` 값 → 관리형, 커밋 금지).
- staging/prod 환경 구분 변수화.
- SQS 큐 URL·ARN을 서비스 환경변수로 출력(F-025에서 소비).

## 3. 구현 항목
1. `infra/aws/main.tf` (또는 동등 IaC 파일) — 현재: 없음 → 변경: RDS 인스턴스(**db.t4g.micro**(또는 t3.micro), **Postgres 16.5+** [pgvector 0.8 지원 — RDS 확인됨], **Multi-AZ OFF · `backup_retention_period=0`(백업 미사용) · private DB subnet group** — ADR-109 D3 비용최소·유실 risk accepted), SQS 표준 큐(`podo-scoring-queue`), Secrets Manager 시크릿 리소스, 보안그룹(api→RDS 5432, worker→RDS, worker→SQS — rds-sg는 api/worker-sg source만, T-083 상세), IAM 역할(최소권한 — RDS 접근 + SQS SendMessage/ReceiveMessage). **GitHub Actions OIDC**: IAM **OIDC identity provider**(`token.actions.githubusercontent.com`, audience `sts.amazonaws.com`) + 배포용 AssumeRole 역할(`sub` claim을 `repo:<org>/<repo>:ref:refs/heads/main`으로 제한 — T-084가 사용). → 확인: `terraform plan`(또는 동등) 오류 0. (AC-1)
2. **사용자 수행** — AWS 콘솔/CLI에서 IaC apply, RDS 엔드포인트·SQS URL 확보, Secrets Manager에 실 시크릿 값 주입. → 확인: 후속 AC-2 마이그레이션 단계로 검증.
3. `podo/apps/api/prisma/schema.prisma` 및 마이그레이션 — 현재: 로컬 PG 대상 → 변경: `DATABASE_URL`이 RDS 엔드포인트를 가리키도록 환경변수 문서화(코드 변경 없음, env만) → 확인: `prisma migrate deploy`를 RDS 대상으로 실행 후 `SELECT extname FROM pg_extension WHERE extname='vector'` 성공. (AC-2)
4. `.env.example` — 현재: 로컬 값 → 변경: `DATABASE_URL`·`SQS_QUEUE_URL`·`AWS_REGION`·`OPENAI_API_KEY` 이름 추가(값 비움, 주석으로 Secrets Manager 참조 명시) → 확인: `.env` gitignore 유지, `.env.example`만 커밋. (AC-3)
5. `infra/aws/outputs.tf` (또는 동등) — 현재: 없음 → 변경: `rds_endpoint`·`sqs_queue_url`·`sqs_queue_arn` 출력 정의 → 확인: `terraform output` 또는 동등 명령으로 값 확인. (AC-1)

## 4. 제외 항목
- S3/오브젝트 스토리지: 바이너리 저장 없음, 공유 LLM 캐시는 Postgres(F-027).
- 서비스 호스팅 실행(ECS/Lambda 등) — F-025.
- 공유 LLM 캐시 Postgres 어댑터 — F-027.
- 멀티리전·오토스케일·고가용: MVP 단일 리전.
- (IaC 도구는 **Terraform 확정** — M6 §7. 비범위 아님.)

## 4-1. 변경 예정 파일/경로
- `infra/aws/main.tf` (신규) — VPC·public/private subnet·SG·RDS(PG16.5)·SQS×2·Secrets×3·OIDC·IAM 초안(T-083이 networking/SG/IAM 분리·세분화)
- `infra/aws/outputs.tf` (신규) — rds_endpoint·sqs_queue_url/arn·OIDC role ARN 등 출력
- `infra/aws/variables.tf` (신규) — env·aws_region·db_password(sensitive)·github_org_repo (T-083이 db_instance_class 등 추가)
- `infra/aws/.terraform.lock.hcl` (신규, 커밋 O) — provider 버전 핀(aws ~> 5.0)
- `.env.example` — AWS 배포 섹션 추가(`AWS_REGION`·`SQS_QUEUE_URL`; DATABASE_URL·OPENAI_API_KEY 기존 + Secrets Manager 주입 주석)
- `.gitignore` — Terraform 산출물 ignore(`.terraform/`·`*.tfstate`·실 `*.tfvars`; lock·*.example은 커밋)

## 5. 완료 조건
RDS(Postgres+pgvector)·SQS·Secrets Manager가 AWS에 존재하고, `prisma migrate deploy`가 RDS 대상으로 green이며, 시크릿이 저장소에 커밋되지 않은 상태로 서비스에 주입 가능하다.

## 6. Acceptance Criteria
- AC-1 [Given] `infra/aws/` IaC 정의 [When] `terraform plan`(또는 동등) [Then] RDS·SQS·Secrets Manager·보안그룹·IAM 자원 계획이 오류 0으로 출력되고, `outputs`에 `rds_endpoint`·`sqs_queue_url`이 포함된다.
- AC-2 [Given] RDS가 apply된 상태 [When] `prisma migrate deploy` 실행 [Then] 마이그레이션이 green으로 완료되고 `SELECT extname FROM pg_extension WHERE extname='vector'` 결과가 `vector`를 반환한다(사용자 수행 후 검증).
- AC-3 [Given] 저장소 전체 [When] `git grep -r "OPENAI_API_KEY\|DATABASE_URL" -- ':!*.example' ':!docs/'` [Then] `.env` 실값이 커밋에 포함되지 않는다(시크릿 미커밋).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → IaC lint/plan: `terraform validate && terraform plan` exit 0 (또는 CDK synth 동등)
- AC-2 → 수동(사용자 수행): `DATABASE_URL=<rds_endpoint> npx prisma migrate deploy` → `psql $DATABASE_URL -c "SELECT extname FROM pg_extension WHERE extname='vector';"` 결과 = 1행
- AC-3 → `git grep -r "sk-\|postgres://.*:.*@" -- ':!*.example' ':!docs/'` exit 0 (매칭 없음)

## 6-2. TDD opt-out
- 사유: IaC 자원 프로비저닝은 단위 테스트 부적합 — plan/validate·마이그레이션 실행·시크릿 grep으로 대체. 사용자 콘솔 작업(apply) 포함.
- Follow-up task: F-025의 e2e-smoke(T-086)가 RDS 연결 최종 검증.

## 7. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Feature: [F-024-aws-infra-provisioning](../features/F-024-aws-infra-provisioning.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 A-INFRA, §6 RDS/SQS, §7-3)
- Architecture-Iface: [ARCH ## 7-3 백엔드/인프라](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) · [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md) · [ADR-109](../../90-decisions/project/ADR-109-aws-hosting-topology.md)(호스팅·RDS 사양·백업)

## 8. 메모
- **IaC 도구 = Terraform 확정**(M6 §7 — ECS/Fargate 정합). §3·verifier(`terraform validate/plan`)가 이 선택과 일치. (CDK/SST 전환 시 AWS 호스팅 ADR + verifier 갱신.)
- **RDS pgvector (확인됨 2026-06):** pgvector는 RDS Postgres **15.9+/16.5+/17.1+에서 0.8** 지원(15.2+부터 가용) → **PG 16.5+ 선택**. `CREATE EXTENSION vector`·HNSW는 Prisma migration raw SQL(로컬과 동일). `rds.force_ssl=1` 권장. *(열린 질문 해소.)*
- **GitHub OIDC provider/role**: T-084 배포가 OIDC AssumeRole을 쓰므로 본 IaC가 OIDC identity provider + 역할을 함께 생성(사용자 apply). long-lived AWS key 미사용.
- MVP: **db.t4g.micro(또는 t3.micro), 단일 AZ, 백업 미사용**(`backup_retention_period=0`) — ADR-109 D3(비용최소 우선 · 데이터 유실 risk accepted; 데이터 가치 상승 시 백업·Multi-AZ 활성). RDS는 **private subnet**(절대 public 금지). 고가용은 비범위.
- 사용자 수행 단계(IaC apply, 시크릿 주입)는 에이전트가 실행하지 않는다.

## 9. 의존성
- depends_on: []   # wave 1 선두 — 선행 M6 task 없음
- write_set: ["infra/aws/**", ".env.example"]
- assumptions: ["AWS 계정·CLI 자격증명 설정됨", "IaC 도구(Terraform/CDK/SST) 설치됨", "사용자가 RDS apply·시크릿 주입을 직접 수행"]
- verifier: "terraform validate -chdir=infra/aws"
