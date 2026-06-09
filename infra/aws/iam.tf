# T-083: IAM 역할 세분화 — api-role / worker-role 최소권한
# api-role: Secrets Manager read + SQS SendMessage
# worker-role: Secrets Manager read + SQS ReceiveMessage/DeleteMessage + RDS IAM auth
# 불필요한 Action:"*" 없음

# ---------------------------------------------------------------------------
# GitHub Actions OIDC identity provider (T-084 소비)
# ---------------------------------------------------------------------------
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  # GitHub Actions OIDC thumbprint (2025 현재값 — 갱신 시 업데이트)
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = { Name = "podo-github-oidc" }
}

resource "aws_iam_role" "github_deploy" {
  name        = "podo-${var.env}-github-deploy"
  description = "T-084 GitHub Actions deploy role - OIDC AssumeRole"

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
# api-role — Secrets Manager read + SQS SendMessage
# ---------------------------------------------------------------------------
resource "aws_iam_role" "api" {
  name        = "podo-${var.env}-api-role"
  description = "ECS api task role - Secrets Manager read + SQS SendMessage"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "podo-${var.env}-api-role" }
}

resource "aws_iam_policy" "api_secrets" {
  name        = "podo-${var.env}-api-secrets"
  description = "api: Secrets Manager GetSecretValue — podo/${var.env}/* 범위"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ]
      # T-089: 프로덕션 시크릿 세트(SESSION_SECRET·OAuth client 등) 추가 → prefix 와일드카드로 확장.
      Resource = ["arn:aws:secretsmanager:${var.aws_region}:*:secret:podo/${var.env}/*"]
    }]
  })
}

resource "aws_iam_policy" "api_sqs_send" {
  name        = "podo-${var.env}-api-sqs-send"
  description = "api: SQS SendMessage to scoring queue only"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:SendMessage",
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

resource "aws_iam_role_policy_attachment" "api_secrets" {
  role       = aws_iam_role.api.name
  policy_arn = aws_iam_policy.api_secrets.arn
}

resource "aws_iam_role_policy_attachment" "api_sqs_send" {
  role       = aws_iam_role.api.name
  policy_arn = aws_iam_policy.api_sqs_send.arn
}

# ---------------------------------------------------------------------------
# worker-role — Secrets Manager read + SQS ReceiveMessage/DeleteMessage + RDS IAM auth
# ---------------------------------------------------------------------------
resource "aws_iam_role" "worker" {
  name        = "podo-${var.env}-worker-role"
  description = "ECS worker task role - Secrets read + SQS consume + RDS IAM auth"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "podo-${var.env}-worker-role" }
}

resource "aws_iam_policy" "worker_secrets" {
  name        = "podo-${var.env}-worker-secrets"
  description = "worker: Secrets Manager GetSecretValue — podo/${var.env}/* 범위"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ]
      # T-089: prefix 와일드카드로 확장(프로덕션 시크릿 세트 정합).
      Resource = ["arn:aws:secretsmanager:${var.aws_region}:*:secret:podo/${var.env}/*"]
    }]
  })
}

resource "aws_iam_policy" "worker_sqs_consume" {
  name        = "podo-${var.env}-worker-sqs-consume"
  description = "worker: scoring 큐 소비(Receive/Delete) + status 큐 신호(Send)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ConsumeScoringQueue"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [aws_sqs_queue.scoring.arn]
      },
      {
        # worker는 처리 상태(running/done/failed)를 status 큐로 emit한다(_emit_status).
        # SendMessage 누락 시 첫 _emit_status에서 AccessDenied → 채점 시작도 못 하고 crash.
        Sid    = "EmitStatusQueue"
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [aws_sqs_queue.scoring_status.arn]
      },
    ]
  })
}

resource "aws_iam_policy" "worker_rds_connect" {
  name        = "podo-${var.env}-worker-rds-connect"
  description = "worker: RDS IAM auth — rds-db:connect (최소권한, DB user 한정)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["rds-db:connect"]
      # rds-db:connect ARN 형식: arn:aws:rds-db:<region>:<account-id>:dbuser:<db-resource-id>/<db-user>
      # 실 account-id·db-resource-id는 apply 후 사용자가 좁힌다 (현재는 리전 스코프로 허용)
      Resource = ["arn:aws:rds-db:${var.aws_region}:*:dbuser:*/podo"]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "worker_secrets" {
  role       = aws_iam_role.worker.name
  policy_arn = aws_iam_policy.worker_secrets.arn
}

resource "aws_iam_role_policy_attachment" "worker_sqs_consume" {
  role       = aws_iam_role.worker.name
  policy_arn = aws_iam_policy.worker_sqs_consume.arn
}

resource "aws_iam_role_policy_attachment" "worker_rds_connect" {
  role       = aws_iam_role.worker.name
  policy_arn = aws_iam_policy.worker_rds_connect.arn
}
