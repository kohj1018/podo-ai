# 크롤 수집 — ECS 스케줄드 태스크 (EventBridge Scheduler → ecs:RunTask, 하루 1회).
# worker 이미지를 재사용하되 command를 `python -m crawler`로 override(같은 uv 워크스페이스,
# 별도 프로세스/태스크 — worker의 SQS 채점과 분리). GH Actions 러너가 private RDS에 못 닿는
# 문제를 "VPC 내부 1회성 태스크"로 해결한다(크롤=in-VPC 직접 쓰기, worker와 동일 방식).
# 비용: 하루 몇 분 Fargate 실행분만(월 ~$0.1~0.3).

# ---------------------------------------------------------------------------
# 크롤 task definition — worker 이미지 + crawler 진입점. crawl은 LLM 무관 → DATABASE_URL만.
# ---------------------------------------------------------------------------
resource "aws_ecs_task_definition" "crawl" {
  family                   = "podo-${var.env}-crawl"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256" # 크롤은 httpx+bs4(경량) → 최소 사양
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_exec.arn # ECR pull + 시크릿 주입
  # task_role 불요 — crawler는 AWS API(SDK) 호출 없음(httpx 크롤 + psycopg RDS 기록뿐).

  container_definitions = jsonencode([{
    name      = "podo-crawl"
    image     = "${aws_ecr_repository.worker.repository_url}:latest" # worker 이미지 재사용
    essential = true
    # worker 이미지의 기본 CMD(`python -m worker`)를 크롤 진입점으로 override.
    command = ["uv", "run", "--no-dev", "--frozen", "python", "-m", "crawler"]
    secrets = [
      { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.main.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "crawl"
      }
    }
  }])
  tags = { Name = "podo-${var.env}-crawl-td" }
}

# ---------------------------------------------------------------------------
# EventBridge Scheduler가 RunTask를 호출하기 위한 역할(ecs:RunTask + PassRole).
# ---------------------------------------------------------------------------
resource "aws_iam_role" "crawl_scheduler" {
  name = "podo-${var.env}-crawl-scheduler"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = { Name = "podo-${var.env}-crawl-scheduler" }
}

resource "aws_iam_role_policy" "crawl_scheduler" {
  name = "podo-${var.env}-crawl-scheduler-runtask"
  role = aws_iam_role.crawl_scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "RunCrawlTask"
        Effect   = "Allow"
        Action   = ["ecs:RunTask"]
        Resource = [aws_ecs_task_definition.crawl.arn] # 특정 리비전(테라폼이 동기 유지)
        Condition = {
          ArnLike = { "ecs:cluster" = aws_ecs_cluster.main.arn }
        }
      },
      {
        Sid      = "PassExecRole" # RunTask가 execution role을 태스크에 부여하려면 PassRole 필요
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.ecs_exec.arn]
      },
    ]
  })
}

# ---------------------------------------------------------------------------
# 스케줄 — 매일 1회(서울 06:00, 트래픽 낮은 시간). Fargate, worker SG/서브넷 재사용.
# ---------------------------------------------------------------------------
resource "aws_scheduler_schedule" "crawl" {
  name                         = "podo-${var.env}-crawl-daily"
  schedule_expression          = "cron(0 6 * * ? *)"
  schedule_expression_timezone = "Asia/Seoul"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.crawl_scheduler.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.crawl.arn
      launch_type         = "FARGATE"

      # 퍼블릭 서브넷 + 퍼블릭 IP(NAT 없음) → 채용사이트 443 + RDS 5432. worker-sg 재사용
      # (egress 443+5432 보유). 인바운드 없음.
      network_configuration {
        subnets          = [aws_subnet.public_a.id, aws_subnet.public_b.id]
        security_groups  = [aws_security_group.worker.id]
        assign_public_ip = true
      }
    }

    retry_policy {
      maximum_retry_attempts = 1
    }
  }
}
