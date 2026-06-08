# T-083: VPC 네트워킹 — public 서브넷(api/worker) + private DB 서브넷
# ADR-109 D2: NAT Gateway 미사용. api/worker = public subnet + assignPublicIp
# ADR-109 D3: RDS = private subnet (public 금지)

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
