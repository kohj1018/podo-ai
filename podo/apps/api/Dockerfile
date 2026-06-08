# syntax=docker/dockerfile:1
# T-089 배포: api(NestJS) 컨테이너. 빌드 컨텍스트 = 리포 루트 (pnpm workspace lockfile 필요).
#   deploy-api.yml이 `docker build -f podo/apps/api/Dockerfile . ` (컨텍스트 '.') 로 빌드한다.
# node:22-slim — pnpm 11.x가 node:sqlite(Node 22.5+)를 요구.
FROM node:22-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends openssl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN corepack enable && corepack prepare pnpm@11.1.2 --activate

# 워크스페이스 매니페스트 + 소스. devDeps 포함 설치 — prisma CLI를 런타임 migrate에 사용.
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY podo ./podo
RUN pnpm install --filter @podo/api --frozen-lockfile \
 && pnpm --filter @podo/api exec prisma generate \
 && pnpm --filter @podo/api run build

WORKDIR /app/podo/apps/api
ENV NODE_ENV=production PORT=3000
EXPOSE 3000
# private RDS는 VPC 내부에서만 접근 가능 → api 컨테이너(같은 VPC)가 기동 시 마이그레이션
# (prisma migrate deploy는 idempotent — 매 기동 안전) 후 서버 listen.
CMD ["sh","-c","pnpm exec prisma migrate deploy && node dist/main.js"]
