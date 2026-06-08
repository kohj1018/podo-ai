# T-083: 보안그룹 세분화
# ADR-109 D4: public subnet 보상 — SG inbound 최소화
# - api-sg: ALB source 80/443만 (T-085 ALB 생성 후 ALB SG를 source로 추가)
# - worker-sg: inbound 없음, egress 443(OpenAI·AWS API·ECR)
# - rds-sg: api-sg·worker-sg source 5432만, 0.0.0.0/0 금지

# ---------------------------------------------------------------------------
# ALB 보안그룹 — api 앞단 (인터넷→ALB)
# ---------------------------------------------------------------------------
resource "aws_security_group" "alb" {
  name        = "podo-${var.env}-alb-sg"
  description = "ALB - internet HTTP/HTTPS inbound"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP inbound from internet"
  }

  ingress {
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
    description      = "HTTPS inbound from internet"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound to api targets"
  }

  tags = { Name = "podo-${var.env}-alb-sg" }
}

# ---------------------------------------------------------------------------
# api 보안그룹 — ALB source 경유 inbound만 (ADR-109 D4)
# ---------------------------------------------------------------------------
resource "aws_security_group" "api" {
  name        = "podo-${var.env}-api-sg"
  description = "ECS api service - inbound via ALB source only"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "HTTP from ALB only"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Outbound: RDS 5432, SQS 443, Secrets Manager 443"
  }

  tags = { Name = "podo-${var.env}-api-sg" }
}

# ---------------------------------------------------------------------------
# worker 보안그룹 — inbound 없음, egress 443 (ADR-109 D2)
# ---------------------------------------------------------------------------
resource "aws_security_group" "worker" {
  name        = "podo-${var.env}-worker-sg"
  description = "ECS worker service - outbound only (ADR-109 D2, no inbound)"
  vpc_id      = aws_vpc.main.id

  # inbound 규칙 없음 — worker는 SQS poll 방식(outbound 전용)

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS outbound: OpenAI, AWS API(SQS/Secrets/ECR)"
  }

  tags = { Name = "podo-${var.env}-worker-sg" }
}

# ---------------------------------------------------------------------------
# RDS 보안그룹 — api-sg·worker-sg source 5432만 (ADR-109 D3)
# 0.0.0.0/0 inbound 절대 금지
# ---------------------------------------------------------------------------
resource "aws_security_group" "rds" {
  name        = "podo-${var.env}-rds-sg"
  description = "RDS Postgres - api/worker SG source 5432 only"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id, aws_security_group.worker.id]
    description     = "Postgres from api/worker SGs only (no 0.0.0.0/0)"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "RDS outbound (replies)"
  }

  tags = { Name = "podo-${var.env}-rds-sg" }
}
