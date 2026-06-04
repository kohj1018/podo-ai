#!/usr/bin/env node
/**
 * verify.mjs — podo-ai 통합 검증 스크립트 (cross-platform)
 *
 * 스택: TS (pnpm + Biome + tsc + Vitest) + Python (uv + ruff + mypy + pytest)
 * 실행: node scripts/verify.mjs [--changed] [--e2e]
 *
 * --changed : git diff 기반 변경 파일만 해당 런타임 단계 실행 (incremental, ADR-020)
 * --e2e     : Playwright e2e 추가 실행 (stabilize-milestone 용)
 *
 * WHY Node.js: mixed env(Windows+macOS) 에서 sh/ps1 이중 유지보수 없이
 *              단일 verify 스크립트로 동작. pnpm(TS) + uv(Python) 양쪽 호출 가능.
 */

import { execSync, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..')

const args = process.argv.slice(2)
const CHANGED_ONLY = args.includes('--changed')
const WITH_E2E = args.includes('--e2e')

// ─── 유틸 ───────────────────────────────────────────────────────────────────

function run(cmd, opts = {}) {
  console.log(`\n[verify] ${cmd}`)
  const result = spawnSync(cmd, { shell: true, cwd: ROOT, stdio: 'inherit', ...opts })
  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

function getChangedFiles() {
  try {
    const out = execSync('git diff --name-only HEAD', { cwd: ROOT }).toString().trim()
    const staged = execSync('git diff --name-only --cached', { cwd: ROOT }).toString().trim()
    return [...new Set([...(out ? out.split('\n') : []), ...(staged ? staged.split('\n') : [])])]
  } catch {
    // git 사용 불가 환경이면 전체 실행으로 fallback
    return []
  }
}

function hasChangedExt(files, ...exts) {
  if (!CHANGED_ONLY || files.length === 0) return true
  return files.some(f => exts.some(ext => f.endsWith(ext)))
}

// ─── 스택 존재 감지 ──────────────────────────────────────────────────────────

const hasTsStack = existsSync(resolve(ROOT, 'podo'))
const hasPyStack = existsSync(resolve(ROOT, 'ai')) || existsSync(resolve(ROOT, 'crawler'))
const hasPnpmWorkspace = existsSync(resolve(ROOT, 'pnpm-workspace.yaml'))
const hasRootPnpm = existsSync(resolve(ROOT, 'podo', 'package.json'))

// ─── 변경 파일 감지 (--changed) ──────────────────────────────────────────────

const changedFiles = CHANGED_ONLY ? getChangedFiles() : []
const tsChanged = hasChangedExt(changedFiles, '.ts', '.tsx', '.js', '.mjs', '.cjs')
const pyChanged = hasChangedExt(changedFiles, '.py')

// ─── missing 단계 수집 ───────────────────────────────────────────────────────

const missing = []

// ─── TS 스택 (podo/) ─────────────────────────────────────────────────────────
if (hasTsStack && tsChanged) {
  console.log('\n══ TS stack (podo/) ══')

  // format + lint (Biome — format/lint 통합)
  if (existsSync(resolve(ROOT, 'podo', 'node_modules', '.bin', 'biome')) ||
      existsSync(resolve(ROOT, 'podo', 'biome.json'))) {
    run('pnpm --filter "./podo/**" exec biome check --apply .', { cwd: ROOT })
  } else {
    missing.push('TS format/lint (biome not found in podo/)')
  }

  // typecheck
  run('pnpm --filter "./podo/**" exec tsc --noEmit', { cwd: ROOT })

  // unit test (Vitest)
  if (existsSync(resolve(ROOT, 'podo', 'vitest.config.ts')) ||
      existsSync(resolve(ROOT, 'podo', 'vitest.config.js'))) {
    run('pnpm --filter "./podo/**" exec vitest run', { cwd: ROOT })
  } else {
    missing.push('TS unit test (vitest.config not found in podo/)')
  }

  // e2e (Playwright) — validate:e2e 전용
  if (WITH_E2E) {
    run('pnpm --filter "./podo/apps/web" exec playwright test', { cwd: ROOT })
  }
} else if (!hasTsStack) {
  console.log('\n[verify] podo/ 미생성 — TS 단계 skip (scaffold 후 활성화)')
  missing.push('TS stack (podo/ not yet scaffolded)')
}

// ─── Python 스택 (ai/ + crawler/) ────────────────────────────────────────────
if (hasPyStack && pyChanged) {
  console.log('\n══ Python stack (ai/ + crawler/) ══')

  // format (ruff format --check)
  run('uv run ruff format --check .', { cwd: ROOT })

  // lint (ruff check)
  run('uv run ruff check .', { cwd: ROOT })

  // typecheck (mypy)
  if (existsSync(resolve(ROOT, 'pyproject.toml'))) {
    run('uv run mypy --strict ai/ crawler/', { cwd: ROOT })
  } else {
    missing.push('Python typecheck (pyproject.toml not found at root)')
  }

  // unit test + schema-contract (pytest)
  run('uv run pytest', { cwd: ROOT })

} else if (!hasPyStack) {
  console.log('\n[verify] ai/ + crawler/ 미생성 — Python 단계 skip (scaffold 후 활성화)')
  missing.push('Python stack (ai/ + crawler/ not yet scaffolded)')
}

// ─── 결과 ─────────────────────────────────────────────────────────────────────

if (missing.length > 0) {
  console.log('\n[verify] missing 단계:')
  missing.forEach(m => console.log(`  - ${m}`))
}

console.log('\n[verify] done ✓')
