# T-082: RDS(Postgres+pgvector)·SQS·Secrets Manager IaC
# ADR-109 D3: db.t4g.micro, Multi-AZ off, backup_retention_period=0
# T-083: VPC 네트워킹(networking.tf) + 보안그룹(security_groups.tf) + IAM(iam.tf)로 분리

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
# RDS — Postgres 16.5+, private subnet, backup off
# ADR-109 D3: Multi-AZ off, backup_retention_period=0 (데이터 유실 risk accepted)
# ---------------------------------------------------------------------------
resource "aws_db_instance" "main" {
  identifier              = "podo-${var.env}-pg"
  engine                  = "postgres"
  engine_version          = "16.5"
  instance_class          = var.db_instance_class
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

# IAM 역할·정책은 iam.tf에 정의 (T-083 분리)
