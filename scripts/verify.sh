#!/usr/bin/env bash
# verify.sh — podo-ai 통합 검증 (Unix/macOS)
# 실행: ./scripts/verify.sh [--changed] [--e2e]
#
# WHY 별도 .sh: PostToolUse hook에서 Unix shell exec form으로 직접 호출 가능하도록.
#               실제 검증 로직은 verify.mjs에 위임 (단일 로직 SSOT).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec node "$ROOT/scripts/verify.mjs" "$@"
