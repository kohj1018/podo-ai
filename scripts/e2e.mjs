#!/usr/bin/env node
/**
 * e2e.mjs — podo-ai fresh-clone E2E 오케스트레이션 (graduation §5 #3).
 *
 * 단일 명령으로 crawl(fixture) → score(웜캐시) → api 서빙 → feed/coverage 검증을 완주한다.
 * 무키(OPENAI_API_KEY 없음) 기본 — 커밋된 웜캐시(ai/worker/fixtures/llm_cache)로 외부 호출 0회.
 *
 *   node scripts/e2e.mjs              무키 E2E 검증(기본). 웜캐시 필요.
 *   node scripts/e2e.mjs --warm       웜캐시 (재)생성 — OPENAI_API_KEY 필요(1회 키 실행).
 *   node scripts/e2e.mjs --no-compose 외부 제공 DB 사용(CI postgres service). docker compose 생략.
 *   node scripts/e2e.mjs --down       끝나면 docker compose down.
 *
 * WHY Node: verify.mjs와 동일 — Windows/macOS/CI 단일 스크립트로 pnpm(TS)+uv(Python) 호출.
 */

import { spawn, spawnSync } from 'node:child_process'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..')

// 루트 .env 로드 — Python config.py는 .env를 직접 읽지만 node는 안 읽으므로, --warm 키
// 감지·자식 프로세스 전파를 위해 여기서 로드한다(override=false: 셸 환경변수 우선). 값은
// 출력하지 않는다(시크릿). 폴리글랏 단일 env 소스(config.py 주석 참조).
function loadDotenv() {
  const envPath = resolve(ROOT, '.env')
  if (!existsSync(envPath)) return
  for (const line of readFileSync(envPath, 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/)
    if (!m || process.env[m[1]] !== undefined) continue
    let val = m[2]
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1)
    }
    process.env[m[1]] = val
  }
}
loadDotenv()

const args = process.argv.slice(2)
const WARM = args.includes('--warm')
const SKIP_COMPOSE = args.includes('--no-compose') || process.env.E2E_SKIP_COMPOSE === '1'
const TEARDOWN = args.includes('--down')

const API_PORT = process.env.PORT ?? '3001'
const DATABASE_URL =
  process.env.DATABASE_URL ?? 'postgresql://podo:podo@localhost:5432/podo'
const LLM_CACHE_DIR = resolve(ROOT, 'ai/worker/fixtures/llm_cache')
const CRAWL_FIXTURE = resolve(ROOT, 'crawler/fixtures/seed_jobs.txt')
const COMPOSE = ['-f', resolve(ROOT, 'infra/docker-compose.yml')]
const API_DIR = resolve(ROOT, 'podo/apps/api')
const FEED_URL = `http://localhost:${API_PORT}/api/v1/feed`
const COVERAGE_URL = `http://localhost:${API_PORT}/api/v1/coverage`

// ─── 유틸 ───────────────────────────────────────────────────────────────────

function log(msg) {
  console.log(`\n[e2e] ${msg}`)
}

function run(cmd, { env = {}, cwd = ROOT, allowFail = false } = {}) {
  log(cmd)
  const r = spawnSync(cmd, {
    shell: true,
    cwd,
    stdio: 'inherit',
    env: { ...process.env, ...env },
  })
  if (r.status !== 0 && !allowFail) {
    fail(`명령 실패(exit ${r.status}): ${cmd}`)
  }
  return r.status ?? 1
}

let apiChild = null
let exiting = false

// 자식(api) 종료. Windows에서 apiChild.kill()은 libuv child 핸들 close 경로를 타며
// process.exit과 겹치면 UV_HANDLE_CLOSING assertion으로 abort(비0 종료)하므로, win32는
// taskkill로 *외부* 종료해 그 경로를 우회한다. posix는 표준 kill.
function killApi() {
  if (!apiChild || apiChild.killed) return
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/pid', String(apiChild.pid), '/t', '/f'], { stdio: 'ignore' })
  } else {
    apiChild.kill()
  }
}

// 종료 단일 경로 — 자식을 먼저 정리한 뒤 process.exit(중복 진입 차단).
function finishAndExit(code) {
  if (exiting) return
  exiting = true
  killApi()
  if (TEARDOWN && !SKIP_COMPOSE) {
    run(`docker compose ${COMPOSE.join(' ')} down`, { allowFail: true })
  }
  process.exit(code)
}

function fail(msg) {
  console.error(`\n[e2e] ✗ ${msg}`)
  finishAndExit(1)
}

async function sleep(ms) {
  await new Promise((r) => setTimeout(r, ms))
}

async function waitFor(label, check, { tries = 30, gapMs = 2000 } = {}) {
  for (let i = 0; i < tries; i++) {
    if (await check()) return
    await sleep(gapMs)
  }
  fail(`${label} 대기 시간 초과(${(tries * gapMs) / 1000}s)`)
}

// ─── phase 0: 사전 점검 ───────────────────────────────────────────────────────

function warmCacheEntries() {
  if (!existsSync(LLM_CACHE_DIR)) return 0
  return readdirSync(LLM_CACHE_DIR).filter((f) => f.endsWith('.json')).length
}

if (!WARM && warmCacheEntries() === 0) {
  fail(
    `웜캐시 비어있음(${LLM_CACHE_DIR}). 무키 E2E는 커밋된 웜캐시가 필요하다.\n` +
      `      OPENAI_API_KEY를 보유한 상태에서 한 번 \`pnpm e2e:warm\`을 돌린 뒤\n` +
      `      \`git add ai/worker/fixtures/llm_cache\`로 캐시를 커밋하세요.`,
  )
}
if (WARM && !process.env.OPENAI_API_KEY) {
  fail('--warm은 OPENAI_API_KEY가 필요합니다(웜캐시 생성을 위한 1회 실 LLM 호출).')
}

// ─── 메인 ─────────────────────────────────────────────────────────────────────

async function main() {
  // phase 1: DB 기동(외부 제공이면 생략)
  if (!SKIP_COMPOSE) {
    run(`docker compose ${COMPOSE.join(' ')} up -d`)
    await waitFor('postgres healthy', () => {
      const r = spawnSync(
        `docker compose ${COMPOSE.join(' ')} exec -T postgres pg_isready -U podo -d podo`,
        { shell: true, cwd: ROOT, stdio: 'ignore' },
      )
      return r.status === 0
    })
  }

  // phase 2: 스키마 마이그레이션 + prisma client
  const dbEnv = { DATABASE_URL }
  run('pnpm --filter @podo/api exec prisma migrate deploy', { env: dbEnv })
  // generate는 비치명 — Windows에서 실행 중 프로세스가 query engine DLL을 잡으면 *이미
  // 올바른* client를 덮어쓰지 못해 EPERM. 기존 client로 진행하고 api 부팅이 유효성을 검증한다.
  if (run('pnpm --filter @podo/api exec prisma generate', { env: dbEnv, allowFail: true })) {
    log('⚠ prisma generate 실패(기존 client로 진행) — DLL 잠금 가능. api 부팅이 검증.')
  }

  // phase 3: crawl (fixture — 네트워크/키 불요)
  run('uv run python -m crawler', { env: { ...dbEnv, CRAWL_FIXTURE } })

  // phase 4: score (웜캐시 — 무키 기본 / --warm은 실 LLM로 캐시 생성)
  const scoreEnv = { ...dbEnv, LLM_CACHE_DIR }
  if (!WARM) {
    // 무키 검증: 키를 제거해 cache miss가 조용히 통과하지 못하게 한다(genuine keyless).
    scoreEnv.OPENAI_API_KEY = ''
  }
  run('uv run python -m worker', { env: scoreEnv })
  if (WARM) {
    log(`웜캐시 생성됨: ${warmCacheEntries()}개 항목 → \`git add ai/worker/fixtures/llm_cache\` 후 커밋`)
  }

  // phase 5: api 빌드 + 기동
  run('pnpm --filter @podo/api run build', { env: dbEnv })
  log('api 기동(node dist/main.js)')
  apiChild = spawn('node', ['dist/main.js'], {
    cwd: API_DIR,
    stdio: 'inherit',
    env: { ...process.env, ...dbEnv, PORT: API_PORT },
  })
  apiChild.on('exit', (code) => {
    if (code && code !== 0 && !apiChild.killed) fail(`api 프로세스 종료(exit ${code})`)
  })
  await waitFor('api ready', async () => {
    try {
      const res = await fetch(COVERAGE_URL)
      return res.ok
    } catch {
      return false
    }
  })

  // phase 6: feed/coverage 검증
  await assertFeedAndCoverage()

  log('✓ E2E 통과 — crawl(fixture) → score(웜캐시) → feed/coverage 재현 완료')
  finishAndExit(0)
}

async function assertFeedAndCoverage() {
  log('feed/coverage assert')

  const coverage = await (await fetch(COVERAGE_URL)).json()
  const byName = Object.fromEntries((coverage.channels ?? []).map((c) => [c.name, c]))
  for (const name of ['toss', 'daangn']) {
    const ch = byName[name]
    if (!ch) fail(`coverage에 ${name} 채널 없음`)
    if (ch.status !== 'success') fail(`${name} 채널 status=${ch.status} (expected success)`)
    if (!ch.last_success_at) fail(`${name} last_success_at 누락(수집 미반영)`)
  }
  if ((coverage.uncollected ?? []).length) {
    fail(`uncollected 채널 존재: ${coverage.uncollected.join(', ')}`)
  }

  const feed = await (await fetch(FEED_URL)).json()
  const items = feed.items ?? []
  if (!items.length) fail('feed 비어있음 — 수집/채점 미반영')

  const scored = items.filter((it) => it.status === 'scored')
  if (!scored.length) {
    fail('scored 공고 0건 — 무키 score가 전부 held(웜캐시 miss 가능). 캐시 재생성 필요.')
  }
  for (const it of scored) {
    if (!Number.isInteger(it.fit_level) || it.fit_level < 1 || it.fit_level > 5) {
      fail(`scored 공고 fit_level 비정상: ${it.fit_level} (1..5 기대)`)
    }
    if (it.evidence == null) fail(`scored 공고 evidence 누락(job=${it.rank_position})`)
  }

  // 토스·당근 양쪽 공고가 피드에 존재 + 중복 제거(공고 id 유일).
  const sources = new Set(items.map((it) => it.posting?.source))
  for (const name of ['toss', 'daangn']) {
    if (!sources.has(name)) fail(`feed에 ${name} 공고 없음`)
  }
  const ids = items.map((it) => it.posting?.id)
  if (new Set(ids).size !== ids.length) fail('feed에 중복 공고(dedup 위반)')

  log(`assert 통과 — scored ${scored.length} / held ${items.length - scored.length} / sources ${[...sources].join('+')}`)
}

process.on('SIGINT', () => finishAndExit(130))

main().catch((err) => fail(String(err?.stack ?? err)))
