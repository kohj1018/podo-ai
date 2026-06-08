# T-082: Terraform outputs — F-025(T-086)·T-083이 소비
output "rds_endpoint" {
  description = "RDS Postgres 엔드포인트 (host:port)"
  value       = aws_db_instance.main.endpoint
}

output "rds_host" {
  description = "RDS Postgres 호스트명 (port 제외)"
  value       = aws_db_instance.main.address
}

output "sqs_queue_url" {
  description = "채점 트리거 큐 URL (ADR-106 SQS 엔드포인트)"
  value       = aws_sqs_queue.scoring.url
}

output "sqs_queue_arn" {
  description = "채점 트리거 큐 ARN"
  value       = aws_sqs_queue.scoring.arn
}

output "sqs_status_queue_url" {
  description = "채점 상태 큐 URL (worker→api 이벤트)"
  value       = aws_sqs_queue.scoring_status.url
}

output "sqs_status_queue_arn" {
  description = "채점 상태 큐 ARN"
  value       = aws_sqs_queue.scoring_status.arn
}

output "github_deploy_role_arn" {
  description = "GitHub Actions OIDC AssumeRole ARN (T-084 소비)"
  value       = aws_iam_role.github_deploy.arn
}

output "ecs_task_role_arn" {
  description = "ECS 태스크 역할 ARN (T-083 소비)"
  value       = aws_iam_role.ecs_task.arn
}

output "vpc_id" {
  description = "VPC ID (T-083 소비)"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "public 서브넷 ID 목록 (api/worker ECS, T-083 소비)"
  value       = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

output "private_subnet_ids" {
  description = "private 서브넷 ID 목록 (RDS subnet group)"
  value       = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

output "api_sg_id" {
  description = "api ECS 서비스 SG ID (T-083 소비)"
  value       = aws_security_group.api.id
}

output "worker_sg_id" {
  description = "worker ECS 서비스 SG ID (T-083 소비)"
  value       = aws_security_group.worker.id
}
