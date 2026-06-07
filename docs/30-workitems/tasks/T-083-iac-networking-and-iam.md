# T-083-iac-networking-and-iam

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
`infra/aws/`의 VPC 네트워킹·보안그룹·IAM 역할을 세분화하고, 환경(staging/prod) 구분·재현 가능성을 완성한다. T-082가 단일 파일로 초안을 잡으면 본 task가 네트워킹/IAM을 구체화해 `FAC-4`(IaC 재현 가능 정의)를 충족시킨다.

## 2. 작업 범위
- VPC·서브넷·인터넷게이트웨이·라우팅 테이블: api/worker용 private 서브넷, RDS용 DB 서브넷 그룹.
- 보안그룹 세분화: api-sg(외부 인바운드 80/443), worker-sg(SQS outbound only), rds-sg(api-sg·worker-sg만 5432 인바운드).
- IAM 역할: api-role(Secrets Manager read, SQS SendMessage), worker-role(Secrets Manager read, SQS ReceiveMessage/DeleteMessage, RDS IAM auth).
- 환경(staging/prod) 변수화 — `var.env`로 이름·태그 분기.
- `infra/aws/README.md` — 사용자 직접 수행 단계(apply 순서·시크릿 주입 방법) 기술.

## 3. 구현 항목
1. `infra/aws/networking.tf` — 현재: 없음 → 변경: VPC(CIDR `10.0.0.0/16`), public 서브넷 2개(NAT GW용), private 서브넷 2개(api/worker), DB 서브넷 그룹(private 서브넷 참조) 정의 → 확인: `terraform validate` 오류 0. (AC-1)
2. `infra/aws/security_groups.tf` — 현재: 없음 → 변경: api-sg·worker-sg·rds-sg 분리(rds-sg ingress = api-sg·worker-sg source만, 와일드카드 0.0.0.0/0 금지) → 확인: 보안그룹 ingress 규칙에 `0.0.0.0/0` 포함 여부 grep(`grep -r "0\.0\.0\.0/0" infra/aws/` — rds-sg에 없어야 함). (AC-2)
3. `infra/aws/iam.tf` — 현재: 없음 → 변경: api-role(policy: `secretsmanager:GetSecretValue`, `sqs:SendMessage`), worker-role(policy: `secretsmanager:GetSecretValue`, `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `rds-db:connect`) 정의, 최소권한 원칙 — 불필요한 `*` action 없음 → 확인: `terraform validate` + 수동 policy 문서 검토. (AC-2)
4. `infra/aws/variables.tf` — 현재: 없음 → 변경: `env`(default="staging")·`aws_region`·`db_instance_class`(default="db.t3.micro") 변수 정의, staging/prod 이름 분기(`"podo-${var.env}-*"` 패턴) → 확인: `terraform plan -var env=prod` 오류 0. (AC-1)
5. `infra/aws/README.md` — 현재: 없음 → 변경: 사용자 직접 수행 단계(①IaC apply 순서 ②Secrets Manager 시크릿 값 주입 방법 ③RDS endpoint 확인 ④SQS URL 확인) 명시 → 확인: 문서 존재 + 단계 목록 포함. (AC-3)

## 4. 제외 항목
- NAT Gateway 실 생성(비용 — MVP는 worker가 VPC endpoint 또는 public subnet 임시 허용; 열린 질문, 사용자 결정).
- WAF·Shield·고급 엣지 보안.
- 멀티리전·오토스케일.

## 4-1. 변경 예정 파일/경로
- `infra/aws/networking.tf`
- `infra/aws/security_groups.tf`
- `infra/aws/iam.tf`
- `infra/aws/variables.tf`
- `infra/aws/README.md`

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
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 8. 메모
- NAT Gateway 비용 결정: MVP에서 worker private subnet의 SQS outbound를 NAT GW 없이 처리하려면 VPC endpoint(com.amazonaws.{region}.sqs) 사용. 비용 대비 단순성 — 사용자 판단.
- 환경 변수화: `terraform.tfvars.example`도 함께 두면 사용자 진입 마찰 감소(`.env.example`과 동일 패턴).

## 9. 의존성
- depends_on: [T-082]   # T-082가 main.tf 초안 후 본 task가 세분화
- write_set: ["infra/aws/networking.tf", "infra/aws/security_groups.tf", "infra/aws/iam.tf", "infra/aws/variables.tf", "infra/aws/README.md"]
- assumptions: ["T-082의 main.tf가 RDS·SQS·Secrets Manager 자원 블록을 정의함", "IaC 도구(Terraform) 선택 확정"]
- verifier: "terraform validate -chdir=infra/aws"
