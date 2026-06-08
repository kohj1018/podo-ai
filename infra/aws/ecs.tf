# T-089 배포(turnkey): 컨테이너 호스팅 계층 — ECR·ECS 클러스터·ALB·태스크 정의·서비스.
# main.tf(RDS/SQS/Secrets)·networking.tf·security_groups.tf·iam.tf의 리소스를 참조한다.
# 이 파일 적용으로 `terraform apply` 한 번에 호스팅까지 생성된다(수동 CLI 부트스트랩 불필요).

locals {
  # api 공개 URL: 커스텀 HTTPS 도메인이 있으면 그걸, 없으면 ALB DNS(HTTP).
  # OAuth 콜백·CORS가 이 값을 쓴다. Google OAuth는 HTTPS 필수 → 도메인 붙으면 var.api_public_url 설정.
  api_url = var.api_public_url != "" ? var.api_public_url : "http://${aws_lb.api.dns_name}"
}

# ---------------------------------------------------------------------------
# 추가 시크릿 껍데기 (값은 사용자 주입 — 커밋 금지). main.tf의 3개에 더해 프로덕션 필수분.
# ---------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "session_secret" {
  name                    = "podo/${var.env}/SESSION_SECRET"
  description             = "express-session 서명 키 — `openssl rand -base64 32`"
  recovery_window_in_days = 0
  tags                    = { Name = "podo-${var.env}-session-secret" }
}

resource "aws_secretsmanager_secret" "github_client_secret" {
  name                    = "podo/${var.env}/GITHUB_CLIENT_SECRET"
  description             = "GitHub OAuth App client secret (사용자 발급)"
  recovery_window_in_days = 0
  tags                    = { Name = "podo-${var.env}-github-client-secret" }
}

resource "aws_secretsmanager_secret" "google_client_secret" {
  name                    = "podo/${var.env}/GOOGLE_CLIENT_SECRET"
  description             = "Google OAuth client secret (사용자 발급)"
  recovery_window_in_days = 0
  tags                    = { Name = "podo-${var.env}-google-client-secret" }
}

# ---------------------------------------------------------------------------
# ECR — 컨테이너 이미지 레지스트리
# ---------------------------------------------------------------------------
resource "aws_ecr_repository" "api" {
  name                 = "podo-api"
  image_tag_mutability = "MUTABLE" # :latest 갱신 허용(GHA가 force-new-deployment로 재배포)
  force_delete         = true      # MVP: destroy 시 이미지째 삭제
  image_scanning_configuration { scan_on_push = true }
  tags = { Name = "podo-${var.env}-ecr-api" }
}

resource "aws_ecr_repository" "worker" {
  name                 = "podo-worker"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration { scan_on_push = true }
  tags = { Name = "podo-${var.env}-ecr-worker" }
}

# ---------------------------------------------------------------------------
# CloudWatch 로그 + ECS 클러스터
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "main" {
  name              = "/ecs/podo-${var.env}"
  retention_in_days = 14
  tags              = { Name = "podo-${var.env}-logs" }
}

resource "aws_ecs_cluster" "main" {
  name = "podo-${var.env}"
  tags = { Name = "podo-${var.env}-cluster" }
}

# ---------------------------------------------------------------------------
# ECS 실행 역할(execution role) — ECR pull + 시크릿 주입(env). 태스크 역할과 별개.
# ---------------------------------------------------------------------------
resource "aws_iam_role" "ecs_exec" {
  name = "podo-${var.env}-ecs-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = { Name = "podo-${var.env}-ecs-exec" }
}

resource "aws_iam_role_policy_attachment" "ecs_exec_managed" {
  role       = aws_iam_role.ecs_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# 시크릿 주입을 위해 실행 역할이 podo/<env>/* 시크릿을 읽을 수 있어야 한다.
resource "aws_iam_role_policy" "ecs_exec_secrets" {
  name = "podo-${var.env}-ecs-exec-secrets"
  role = aws_iam_role.ecs_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = ["arn:aws:secretsmanager:${var.aws_region}:*:secret:podo/${var.env}/*"]
    }]
  })
}

# ---------------------------------------------------------------------------
# GitHub Actions(deploy-api/worker) 배포 권한 — github_deploy 역할에 부착.
# T-082는 OIDC trust만 만들고 권한 정책을 안 붙여, ECR 로그인부터 막혔다(런타임 권한).
# 필요한 것: ECR 인증·push + ECS 강제 재배포(update-service)·안정화 대기(describe-services).
# ---------------------------------------------------------------------------
resource "aws_iam_role_policy" "github_deploy_perms" {
  name = "podo-${var.env}-github-deploy-perms"
  role = aws_iam_role.github_deploy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EcrAuth" # GetAuthorizationToken은 리소스 * 필수(AWS 제약)
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = ["*"]
      },
      {
        Sid    = "EcrPushPull" # podo-api / podo-worker 리포에 한정
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
        ]
        Resource = [aws_ecr_repository.api.arn, aws_ecr_repository.worker.arn]
      },
      {
        Sid      = "EcsDeploy" # update-service --force-new-deployment + wait services-stable
        Effect   = "Allow"
        Action   = ["ecs:UpdateService", "ecs:DescribeServices"]
        Resource = ["*"]
      },
    ]
  })
}

# ---------------------------------------------------------------------------
# ALB — api 공개 엔드포인트 (HTTP 80; HTTPS는 사용자 도메인+ACM, GUIDE §HTTPS)
# ---------------------------------------------------------------------------
resource "aws_lb" "api" {
  name               = "podo-${var.env}-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_b.id]
  tags               = { Name = "podo-${var.env}-alb" }
}

resource "aws_lb_target_group" "api" {
  name        = "podo-${var.env}-api-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip" # Fargate awsvpc → ip 필수(EC2 인스턴스 아님)
  health_check {
    path                = "/api/v1/health"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    interval            = 30
    timeout             = 5
    matcher             = "200"
  }
  tags = { Name = "podo-${var.env}-api-tg" }
}

resource "aws_lb_listener" "api_http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ---------------------------------------------------------------------------
# 태스크 정의 — api / worker (이미지 :latest, GHA가 force-new-deployment로 갱신)
# ---------------------------------------------------------------------------
resource "aws_ecs_task_definition" "api" {
  family                   = "podo-${var.env}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_exec.arn
  task_role_arn            = aws_iam_role.api.arn

  container_definitions = jsonencode([{
    name      = "podo-api"
    image     = "${aws_ecr_repository.api.repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 3000, protocol = "tcp" }]
    environment = [
      { name = "NODE_ENV", value = "production" },
      { name = "PORT", value = "3000" },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "SQS_QUEUE_URL", value = aws_sqs_queue.scoring.url },
      { name = "SQS_STATUS_QUEUE_URL", value = aws_sqs_queue.scoring_status.url },
      { name = "CORS_ALLOWED_ORIGIN", value = var.vercel_origin },
      { name = "GITHUB_CLIENT_ID", value = var.github_client_id },
      { name = "GOOGLE_CLIENT_ID", value = var.google_client_id },
      { name = "GITHUB_CALLBACK_URL", value = "${local.api_url}/auth/github/callback" },
      { name = "GOOGLE_CALLBACK_URL", value = "${local.api_url}/auth/google/callback" },
    ]
    secrets = [
      { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn },
      { name = "SESSION_SECRET", valueFrom = aws_secretsmanager_secret.session_secret.arn },
      { name = "GITHUB_CLIENT_SECRET", valueFrom = aws_secretsmanager_secret.github_client_secret.arn },
      { name = "GOOGLE_CLIENT_SECRET", valueFrom = aws_secretsmanager_secret.google_client_secret.arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.main.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
  tags = { Name = "podo-${var.env}-api-td" }
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "podo-${var.env}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_exec.arn
  task_role_arn            = aws_iam_role.worker.arn

  container_definitions = jsonencode([{
    name      = "podo-worker"
    image     = "${aws_ecr_repository.worker.repository_url}:latest"
    essential = true
    environment = [
      { name = "AWS_REGION", value = var.aws_region },
      { name = "SQS_QUEUE_URL", value = aws_sqs_queue.scoring.url },
      { name = "SQS_STATUS_QUEUE_URL", value = aws_sqs_queue.scoring_status.url },
      { name = "OPENAI_MODEL", value = "gpt-5.4-mini" },
      { name = "SCHEMA_VERSION", value = "v1" },
      { name = "PROMPT_VERSION", value = "v1" },
    ]
    secrets = [
      { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn },
      { name = "OPENAI_API_KEY", valueFrom = aws_secretsmanager_secret.openai_api_key.arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.main.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])
  tags = { Name = "podo-${var.env}-worker-td" }
}

# ---------------------------------------------------------------------------
# ECS 서비스 — Fargate, public subnet + public IP(NAT 없음, ADR-109 D2)
# ---------------------------------------------------------------------------
resource "aws_ecs_service" "api" {
  name            = "podo-${var.env}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_a.id, aws_subnet.public_b.id]
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = true # NAT 없음 → ECR pull·OpenAI outbound는 public IP 경유(필수)
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "podo-api"
    container_port   = 3000
  }

  health_check_grace_period_seconds = 120
  depends_on                        = [aws_lb_listener.api_http]

  # GHA가 force-new-deployment로 재배포(태스크 정의 미변경)하므로 desired_count만 무시.
  lifecycle {
    ignore_changes = [desired_count]
  }
  tags = { Name = "podo-${var.env}-api-svc" }
}

resource "aws_ecs_service" "worker" {
  name            = "podo-${var.env}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_a.id, aws_subnet.public_b.id]
    security_groups  = [aws_security_group.worker.id]
    assign_public_ip = true
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
  tags = { Name = "podo-${var.env}-worker-svc" }
}
