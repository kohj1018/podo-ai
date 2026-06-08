# T-083-iac-networking-and-iam

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
`infra/aws/`의 VPC 네트워킹·보안그룹·IAM 역할을 세분화하고, 환경(staging/prod) 구분·재현 가능성을 완성한다. T-082가 단일 파일로 초안을 잡으면 본 task가 네트워킹/IAM을 구체화해 `FAC-4`(IaC 재현 가능 정의)를 충족시킨다.

## 2. 작업 범위
- VPC·서브넷·인터넷게이트웨이·라우팅 테이블: **api/worker용 public 서브넷**(`assignPublicIp`, NAT 없이 outbound — ADR-109 D2), **RDS용 private DB 서브넷 그룹**(절대 public 금지).
- 보안그룹 세분화: api-sg(**ALB 경유 인바운드만**), worker-sg(**egress 443 — OpenAI·AWS API·ECR; ingress 없음**), rds-sg(api-sg·worker-sg source만 5432 인바운드).
- IAM 역할: api-role(Secrets Manager read, SQS SendMessage), worker-role(Secrets Manager read, SQS ReceiveMessage/DeleteMessage, RDS IAM auth).
- 환경(staging/prod) 변수화 — `var.env`로 이름·태그 분기.
- `infra/aws/README.md` — 사용자 직접 수행 단계(apply 순서·시크릿 주입 방법) 기술.

## 3. 구현 항목
1. `infra/aws/networking.tf` — 현재: 없음 → 변경: VPC(CIDR `10.0.0.0/16`), **public 서브넷 2개(api/worker — `map_public_ip_on_launch`)**, **private DB 서브넷 2개(RDS)**, DB 서브넷 그룹(private 참조), 인터넷게이트웨이 — **NAT Gateway 없음**(ADR-109 D2) 정의 → 확인: `terraform validate` 오류 0 + `grep -rc "aws_nat_gateway" infra/aws/` = 0. (AC-1)
2. `infra/aws/security_groups.tf` — 현재: 없음 → 변경: api-sg(ingress=**ALB source만** 80/443)·worker-sg(**ingress 없음**, egress 443)·rds-sg(ingress = api-sg·worker-sg source만 5432, 와일드카드 0.0.0.0/0 금지) — public subnet 보상(ADR-109 D4) → 확인: ingress 규칙에 `0.0.0.0/0` 포함 여부 grep(`grep -r "0\.0\.0\.0/0" infra/aws/` — rds-sg·worker-sg ingress에 없어야 함). (AC-2)
3. `infra/aws/iam.tf` — 현재: 없음 → 변경: api-role(policy: `secretsmanager:GetSecretValue`, `sqs:SendMessage`), worker-role(policy: `secretsmanager:GetSecretValue`, `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `rds-db:connect`) 정의, 최소권한 원칙 — 불필요한 `*` action 없음 → 확인: `terraform validate` + 수동 policy 문서 검토. (AC-2)
4. `infra/aws/variables.tf` — 현재: 없음 → 변경: `env`(default="staging")·`aws_region`·`db_instance_class`(default="db.t3.micro") 변수 정의, staging/prod 이름 분기(`"podo-${var.env}-*"` 패턴) → 확인: `terraform plan -var env=prod` 오류 0. (AC-1)
5. `infra/aws/README.md` — 현재: 없음 → 변경: 사용자 직접 수행 단계(①IaC apply 순서 ②Secrets Manager 시크릿 값 주입 방법 ③RDS endpoint 확인 ④SQS URL 확인) 명시 → 확인: 문서 존재 + 단계 목록 포함. (AC-3)

## 4. 제외 항목
- NAT Gateway — **영구 미사용 확정**(ADR-109 D2: public subnet + assignPublicIp로 outbound). VPC endpoint는 후속 보안/비용 옵션.
- WAF·Shield·고급 엣지 보안.
- 멀티리전·오토스케일.

## 4-1. 변경 예정 파일/경로
- `infra/aws/networking.tf` (신규) — VPC·public/private subnet·IGW·라우팅·DB subnet group (NAT 없음)
- `infra/aws/security_groups.tf` (신규) — alb-sg(인터넷 80/443)·api-sg(ALB source만)·worker-sg(ingress 없음)·rds-sg(api/worker SG source 5432만)
- `infra/aws/iam.tf` (신규) — api-role(secrets read + sqs send)·worker-role(secrets read + sqs consume + rds-db:connect)·GitHub OIDC provider/deploy role (main.tf에서 이동)
- `infra/aws/variables.tf` — `db_instance_class`(default db.t3.micro) 추가
- `infra/aws/README.md` (신규) — 사용자 수행 단계(apply 순서·시크릿 주입·endpoint/SQS 확인) + 보안 결정
- `infra/aws/terraform.tfvars.example` (신규, 커밋 O) — 변수 입력 예시(실 tfvars는 gitignore)
- `infra/aws/main.tf` — networking/SG/IAM 블록을 위 파일들로 **추출**(refactor) + RDS `instance_class = var.db_instance_class` 배선 (T-083 §1 "단일 파일 초안→세분화" 목적상 불가피)
- `infra/aws/outputs.tf` — IAM 분리에 따라 `ecs_task_role_arn` → `api_role_arn`·`worker_role_arn`로 교체

## 5. 완료 조건
`infra/aws/`가 `terraform validate`(또는 동등) 오류 0이고, 보안그룹·IAM이 최소권한이며, 환경 변수화로 staging/prod 양쪽 plan이 가능하다. 사용자가 README를 보고 apply·시크릿 주입을 자력으로 수행할 수 있다.

## 6. Acceptance Criteria
- AC-1 [Given] `infra/aws/` 전체 [When] `terraform validate && terraform plan -var env=staging && terraform plan -var env=prod` [Then] 두 환경 모두 오류 0으로 계획이 출력된다.
- AC-2 [Given] `infra/aws/security_groups.tf`·`iam.tf` [When] 정적 grep·수동 검토 [Then] rds-sg ingress에 `0.0.0.0/0`이 없고, IAM policy에 `Action: "*"`·`Resource: "*"` 조합이 없다.
- AC-3 [Given] `infra/aws/README.md` [When] 파일 존재 확인 [Then] "사용자 수행" 단계(apply·시크릿 주입·endpoint 확인)가 순서대로 기술되어 있다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → `terraform validate -chdir=infra/aws` exit 0
- AC-2 → `grep -rn "0\.0\.0\.0/0" infra/aws/security_groups.tf` → rds-sg 블록 외 결과 0; `grep -n '"*"' infra/aws/iam.tf` → Action 컨텍스트 없음
- AC-3 → `Test-Path infra/aws/README.md` → True; `Select-String -Path infra/aws/README.md -Pattern "사용자 수행|apply"` → 1개 이상 매칭

## 6-2. TDD opt-out
- 사유: IaC 구성 파일은 단위 테스트 부적합 — validate·grep·수동 검토로 대체. 실 자원 검증은 T-086 e2e-smoke.
- Follow-up task: T-086(e2e-smoke)에서 RDS·SQS 연결 최종 검증.

## 7. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Feature: [F-024-aws-infra-provisioning](../features/F-024-aws-infra-provisioning.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 A-INFRA, §7-3)
- Architecture-Iface: [ARCH ## 7-3 백엔드/인프라](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) · [ADR-109](../../90-decisions/project/ADR-109-aws-hosting-topology.md)(호스팅·networking·NAT 미사용)

## 8. 메모
- **NAT Gateway 미사용 확정**(ADR-109 D2). worker outbound(OpenAI·AWS·ECR)는 public subnet + public IP 경유. AWS 서비스 호출만 VPC endpoint로 좁히는 건 후속 옵션(OpenAI은 외부라 여전히 public IP egress 필요). public subnet 보안 다운그레이드는 **T-089 accepted-risk**.
- 환경 변수화: `terraform.tfvars.example`도 함께 두면 사용자 진입 마찰 감소(`.env.example`과 동일 패턴).

## 9. 의존성
- depends_on: [T-082]   # T-082가 main.tf 초안 후 본 task가 세분화
- write_set: ["infra/aws/networking.tf", "infra/aws/security_groups.tf", "infra/aws/iam.tf", "infra/aws/variables.tf", "infra/aws/README.md"]
- assumptions: ["T-082의 main.tf가 RDS·SQS·Secrets Manager 자원 블록을 정의함", "IaC 도구(Terraform) 선택 확정"]
- verifier: "terraform validate -chdir=infra/aws"
