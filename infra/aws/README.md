# podo-ai AWS 인프라 (IaC)

Terraform으로 정의된 AWS 인프라. ADR-109(NAT 없는 public subnet + private RDS)를 따른다.

## 파일 구성

| 파일 | 역할 |
|------|------|
| `main.tf` | provider, RDS, SQS, Secrets Manager |
| `networking.tf` | VPC, 서브넷, IGW, 라우팅 테이블, DB 서브넷 그룹 |
| `security_groups.tf` | ALB·api·worker·RDS 보안그룹 |
| `iam.tf` | api-role, worker-role, GitHub OIDC |
| `variables.tf` | env, aws_region, db_password, db_instance_class, github_org_repo |
| `outputs.tf` | rds_endpoint, sqs_queue_url 등 출력 |
| `terraform.tfvars.example` | 변수 입력 예시 (복사 후 실값 채움) |

---

## 사용자 수행 단계

### 1. 사전 준비

```bash
# AWS CLI 자격증명 확인
aws sts get-caller-identity

# Terraform 설치 확인 (>= 1.6)
terraform -version
```

### 2. 변수 파일 준비

```bash
cd infra/aws
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars 열어서 실값 채움 (커밋 금지 — .gitignore 확인)
```

필수 값:
- `db_password`: 강력한 랜덤 비밀번호 (예: `openssl rand -base64 24`)
- `github_org_repo`: GitHub org/repo 이름 (예: `myorg/podo-ai`)
- `env`: `staging` 또는 `prod`

### 3. IaC apply 순서

```bash
# 1) 초기화 (provider 설치)
terraform init

# 2) 계획 검토 — staging
terraform plan -var-file=terraform.tfvars

# 3) apply (실 자원 생성 — AWS 비용 발생)
terraform apply -var-file=terraform.tfvars

# prod 환경을 별도 배포할 때
terraform apply -var env=prod -var-file=terraform.tfvars
```

apply 완료 후 `terraform output`으로 생성된 자원 정보를 확인한다.

### 4. Secrets Manager 시크릿 값 주입

IaC apply는 시크릿 *리소스*(빈 껍데기)만 생성한다. 실값은 AWS 콘솔 또는 CLI로 직접 주입한다.

```bash
# OpenAI API key (실값은 콘솔/CLI에서만 — 커밋·로그 금지)
aws secretsmanager put-secret-value \
  --secret-id "podo/staging/OPENAI_API_KEY" \
  --secret-string '{"value":"<OPENAI_API_KEY 실값>"}'

# DATABASE_URL — RDS 엔드포인트 확인 후 주입 (아래 §5 참조)
aws secretsmanager put-secret-value \
  --secret-id "podo/staging/DATABASE_URL" \
  --secret-string "postgresql://podo:<password>@<rds-endpoint>:5432/podo?sslmode=require"

# OAuth secret
aws secretsmanager put-secret-value \
  --secret-id "podo/staging/OAUTH_SECRET" \
  --secret-string '{"value":"실값"}'
```

주의: 시크릿 실값을 절대 코드·커밋에 포함하지 않는다.

### 5. RDS 엔드포인트 확인

```bash
# terraform output으로 확인
terraform output rds_endpoint   # host:port 형식
terraform output rds_host       # host만

# 또는 AWS CLI
aws rds describe-db-instances \
  --db-instance-identifier podo-staging-pg \
  --query 'DBInstances[0].Endpoint'
```

RDS 엔드포인트를 확인한 뒤 위 §4의 `DATABASE_URL` 시크릿에 주입한다.

### 6. SQS URL 확인

```bash
terraform output sqs_queue_url         # 채점 트리거 큐
terraform output sqs_status_queue_url  # 채점 상태 큐
```

SQS URL을 서비스 환경변수(`SQS_QUEUE_URL`)에 설정한다.

---

## 주요 보안 결정 (ADR-109)

- api/worker는 **public subnet** + `assignPublicIp` — NAT Gateway 미사용(비용 절감, ADR-109 D2)
- RDS는 **private subnet** — `publicly_accessible=false`, rds-sg ingress는 api-sg·worker-sg source만 허용
- api-sg: ALB source 경유 inbound만 / worker-sg: inbound 없음(outbound 전용)
- 시크릿은 Secrets Manager — 코드·커밋에 실값 포함 금지
- NAT 없는 public subnet은 **의식적 비용/보안 트레이드오프** (T-089 accepted-risk)

## 비용 감각 (참고, 실제는 AWS Pricing Calculator로 확인)

- NAT Gateway 미사용으로 ~$32/월 절감
- RDS db.t3.micro 상시: ~$13~17/월
- Fargate api+worker 상시: ~$20~35/월
- SQS/Secrets/ECR/CloudWatch: 초반 수 달러 이내
