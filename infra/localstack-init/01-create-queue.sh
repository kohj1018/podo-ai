#!/usr/bin/env bash
# LocalStack ready hook — 채점 트리거 큐 생성(T-044, ADR-106).
# /etc/localstack/init/ready.d 에 마운트되어 LocalStack 기동 후 1회 실행된다.
set -euo pipefail

awslocal sqs create-queue --queue-name scoring-queue

echo "[localstack-init] scoring-queue created"
