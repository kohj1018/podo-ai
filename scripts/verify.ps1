# verify.ps1 — podo-ai 통합 검증 (Windows PowerShell)
# 실행: pwsh -File scripts\verify.ps1 [--changed] [--e2e]
#       또는 powershell -File scripts\verify.ps1 [--changed] [--e2e]
#
# WHY 별도 .ps1: PostToolUse hook에서 Windows PowerShell exec form으로 직접 호출 가능하도록.
#                실제 검증 로직은 verify.mjs에 위임 (단일 로직 SSOT).

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
& node "$Root\scripts\verify.mjs" @args
exit $LASTEXITCODE
