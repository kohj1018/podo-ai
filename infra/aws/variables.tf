# T-082: Terraform 변수 — staging/prod 환경 구분
variable "env" {
  description = "배포 환경 (staging | prod)"
  type        = string
  default     = "staging"
  validation {
    condition     = contains(["staging", "prod"], var.env)
    error_message = "env는 staging 또는 prod 이어야 합니다."
  }
}

variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "db_password" {
  description = "RDS 마스터 패스워드 — 실값은 환경변수(TF_VAR_db_password)로 주입. 커밋 금지."
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS 인스턴스 클래스 (ADR-109 D3: MVP 최소사양)"
  type        = string
  default     = "db.t3.micro"
}

variable "github_org_repo" {
  description = "GitHub OIDC sub claim 패턴 (예: myorg/podo-ai)"
  type        = string
}
