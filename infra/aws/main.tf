# T-082: RDS(Postgres+pgvector)·SQS·Secrets Manager·네트워킹·OIDC IaC
# ADR-109: NAT 없는 public subnet(api/worker) + private subnet(RDS)
# ADR-109 D3: db.t4g.micro, Multi-AZ off, backup_retention_period=0

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "podo-${var.env}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "podo-${var.env}-igw" }
}

# ---------------------------------------------------------------------------
# Public subnets — api / worker (ADR-109 D2: assignPublicIp, NAT 없음)
# ---------------------------------------------------------------------------
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags                    = { Name = "podo-${var.env}-public-a" }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true
  tags                    = { Name = "podo-${var.env}-public-b" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "podo-${var.env}-rt-public" }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

# ---------------------------------------------------------------------------
# Private subnets — RDS only (ADR-109 D3: private DB subnet, public 금지)
# ---------------------------------------------------------------------------
resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.aws_region}a"
  tags              = { Name = "podo-${var.env}-private-a" }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.12.0/24"
  availability_zone = "${var.aws_region}b"
  tags              = { Name = "podo-${var.env}-private-b" }
}

# DB subnet group requires >= 2 AZs even for single-AZ RDS
resource "aws_db_subnet_group" "main" {
  name       = "podo-${var.env}-db-sg"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  tags       = { Name = "podo-${var.env}-db-subnet-group" }
}

# ---------------------------------------------------------------------------
# Security Groups
# ---------------------------------------------------------------------------

# api SG — inbound from ALB only (T-083 상세); outbound: RDS 5432, internet
resource "aws_security_group" "api" {
  name        = "podo-${var.env}-api-sg"
  description = "ECS api service (T-083 wires ALB inbound)"
  vpc_id      = aws_vpc.main.id

  # ALB 80/443 inbound은 T-083에서 ALB SG source로 추가
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound (RDS, SQS, Secrets, internet)"
  }

  tags = { Name = "podo-${var.env}-api-sg" }
}

# worker SG — inbound 없음(outbound 전용, ADR-109 D2)
resource "aws_security_group" "worker" {
  name        = "podo-${var.env}-worker-sg"
  description = "ECS worker service — outbound only (ADR-109 D2)"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound (RDS, SQS, OpenAI)"
  }

  tags = { Name = "podo-${var.env}-worker-sg" }
}

# RDS SG — ingress from api-sg and worker-sg source only (ADR-109 D3)
resource "aws_security_group" "rds" {
  name        = "podo-${var.env}-rds-sg"
  description = "RDS Postgres — api/worker SG source only"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id, aws_security_group.worker.id]
    description     = "Postgres from api/worker SGs only"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "podo-${var.env}-rds-sg" }
}

# ---------------------------------------------------------------------------
# RDS — Postgres 16.5+, db.t4g.micro, private subnet, backup off
# ADR-109 D3: Multi-AZ off, backup_retention_period=0 (데이터 유실 risk accepted)
# ---------------------------------------------------------------------------
resource "aws_db_instance" "main" {
  identifier              = "podo-${var.env}-pg"
  engine                  = "postgres"
  engine_version          = "16.5"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  storage_type            = "gp3"
  db_name                 = "podo"
  username                = "podo"
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  publicly_accessible     = false   # ADR-109 D3: private only
  multi_az                = false   # ADR-109 D3: MVP 단일 AZ
  backup_retention_period = 0       # ADR-109 D3: 백업 미사용 (risk accepted)
  deletion_protection     = false
  skip_final_snapshot     = true
  # pgvector 0.8 지원 (RDS Postgres 16.5+ — T-082 §8 확인됨)
  parameter_group_name    = aws_db_parameter_group.main.name

  tags = { Name = "podo-${var.env}-rds" }
}

resource "aws_db_parameter_group" "main" {
  name   = "podo-${var.env}-pg16"
  family = "postgres16"

  parameter {
    # ssl 강제 (T-082 §8 권장)
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = { Name = "podo-${var.env}-pg16-params" }
}

# ---------------------------------------------------------------------------
# SQS — 채점 트리거 큐 + 상태 큐 (ADR-106)
# ---------------------------------------------------------------------------
resource "aws_sqs_queue" "scoring" {
  name                       = "podo-${var.env}-scoring-queue"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 86400  # 24h

  tags = { Name = "podo-${var.env}-scoring-queue" }
}

resource "aws_sqs_queue" "scoring_status" {
  name                       = "podo-${var.env}-scoring-status-queue"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 86400

  tags = { Name = "podo-${var.env}-scoring-status-queue" }
}

# ---------------------------------------------------------------------------
# Secrets Manager — 실값은 사용자 직접 주입(커밋 금지, T-082 §3-2)
# ---------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "podo/${var.env}/OPENAI_API_KEY"
  description             = "OpenAI API key — 실값은 AWS 콘솔/CLI로 주입"
  recovery_window_in_days = 0   # MVP: 즉시 삭제 허용

  tags = { Name = "podo-${var.env}-openai-api-key" }
}

resource "aws_secretsmanager_secret" "database_url" {
  name                    = "podo/${var.env}/DATABASE_URL"
  description             = "Postgres DATABASE_URL — apply 후 RDS 엔드포인트로 주입"
  recovery_window_in_days = 0

  tags = { Name = "podo-${var.env}-database-url" }
}

resource "aws_secretsmanager_secret" "oauth_secret" {
  name                    = "podo/${var.env}/OAUTH_SECRET"
  description             = "OAuth client secret — 실값은 AWS 콘솔/CLI로 주입"
  recovery_window_in_days = 0

  tags = { Name = "podo-${var.env}-oauth-secret" }
}

# ---------------------------------------------------------------------------
# GitHub Actions OIDC — long-lived AWS key 미사용 (T-082 §3-1, T-084 소비)
# ---------------------------------------------------------------------------
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  # GitHub Actions OIDC thumbprint (2025 현재값 — 갱신 시 업데이트)
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = { Name = "podo-github-oidc" }
}

resource "aws_iam_role" "github_deploy" {
  name = "podo-${var.env}-github-deploy"
  description = "T-084 GitHub Actions 배포 역할 — OIDC AssumeRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # main 브랜치 배포만 허용 (T-082 §3-1)
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_org_repo}:ref:refs/heads/main"
        }
      }
    }]
  })

  tags = { Name = "podo-${var.env}-github-deploy" }
}

# ---------------------------------------------------------------------------
# IAM — 서비스 태스크 역할 (ECS Task Role, T-083 상세)
# 최소권한: RDS 접근(Secrets Manager 경유) + SQS SendMessage/ReceiveMessage
# ---------------------------------------------------------------------------
resource "aws_iam_role" "ecs_task" {
  name = "podo-${var.env}-ecs-task"
  description = "ECS task role — Secrets Manager read + SQS send/receive"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "podo-${var.env}-ecs-task" }
}

resource "aws_iam_policy" "ecs_task_secrets" {
  name        = "podo-${var.env}-ecs-task-secrets"
  description = "Secrets Manager GetSecretValue for podo/${var.env}/* secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ]
      Resource = [
        aws_secretsmanager_secret.openai_api_key.arn,
        aws_secretsmanager_secret.database_url.arn,
        aws_secretsmanager_secret.oauth_secret.arn,
      ]
    }]
  })
}

resource "aws_iam_policy" "ecs_task_sqs" {
  name        = "podo-${var.env}-ecs-task-sqs"
  description = "SQS SendMessage/ReceiveMessage/DeleteMessage for scoring queues"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl"
      ]
      Resource = [
        aws_sqs_queue.scoring.arn,
        aws_sqs_queue.scoring_status.arn,
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_secrets" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task_secrets.arn
}

resource "aws_iam_role_policy_attachment" "ecs_task_sqs" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task_sqs.arn
}
