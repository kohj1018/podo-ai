#!/usr/bin/env node
/**
 * e2e.mjs — podo-ai 멀티유저 fresh-clone E2E 오케스트레이션 (M4 graduation §5, T-052).
 *
 * 단일 명령으로: docker compose(Postgres + LocalStack SQS) → migrate + 사용자 2명 시드 →
 * crawl(fixture) → api 기동(NODE_ENV=test, SQS enqueue) → worker 기동(SQS consumer) →
 * **사용자 A·B OAuth 우회 로그인 → 각자 이력서 업로드(마스킹) → score(enqueue) → 큐 드레인 →
 * 각자 격리 피드(적합도 배지·근거·커버리지) → 데이터 격리 차단 → 지원 기록 처리완료 정리 →
 * PII 스캔(이력서 raw + 계정 PII)** 까지 완주한다. M4 done-line(로컬 멀티유저 E2E)을 자동 게이트로 실증.
 * 무키(OPENAI_API_KEY 없음) 기본 — 커밋된 웜캐시로 외부 호출 0회.
 *
 *   node scripts/e2e.mjs              무키 멀티유저 E2E(기본). 업로드 fixture 웜캐시 필요.
 *   node scripts/e2e.mjs --warm       웜캐시 (재)생성 — OPENAI_API_KEY 필요(1회 키 실행).
 *   node scripts/e2e.mjs --no-compose 외부 제공 DB·SQS 사용(CI service). docker compose 생략.
 *   node scripts/e2e.mjs --down       끝나면 docker compose down.
 *
 * WHY 큐 경로: M4(T-044/045)가 subprocess spawn을 SQS enqueue/consume로 교체 → api는 enqueue,
 *   worker는 상시 consumer. 본 스크립트가 그 경로 + 멀티유저 격리를 구동한다.
 */

import { spawn, spawnSync } from 'node:child_process'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..')

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
const PII_FIXTURE = resolve(ROOT, 'ai/tests/fixtures/pii_resume.txt')
const SEED_USERS_SQL = resolve(ROOT, 'scripts/e2e_seed_users.sql')
const PRISMA_SCHEMA = resolve(ROOT, 'podo/apps/api/prisma/schema.prisma')
const COMPOSE = ['-f', resolve(ROOT, 'infra/docker-compose.yml')]
const API_DIR = resolve(ROOT, 'podo/apps/api')

const SQS_ENDPOINT_URL = process.env.SQS_ENDPOINT_URL ?? 'http://localhost:4566'
const SQS_QUEUE_URL =
  process.env.SQS_QUEUE_URL ?? 'http://localhost:4566/000000000000/scoring-queue'
const SQS_STATUS_QUEUE_URL =
  process.env.SQS_STATUS_QUEUE_URL ??
  'http://localhost:4566/000000000000/scoring-status-queue'

const base = `http://localhost:${API_PORT}`
const FEED_URL = `${base}/api/v1/feed`
const COVERAGE_URL = `${base}/api/v1/coverage`
const RESUMES_URL = `${base}/api/v1/resumes`
const SCORING_JOBS_URL = `${base}/api/v1/scoring-jobs`
const APPLICATIONS_URL = `${base}/api/v1/applications`
const TEST_SESSION_URL = `${base}/auth/test-session`

// 시드 사용자(e2e_seed_users.sql와 일치) — 고정 id로 test-session 우회.
const USERS = {
  A: { id: 'e2e-user-a', email: 'e2e-acct-a@example.test' },
  B: { id: 'e2e-user-b', email: 'e2e-acct-b@example.test' },
}

// ─── 유틸 ───────────────────────────────────────────────────────────────────

function log(msg) {
  console.log(`\n[e2e] ${msg}`)
}

function run(cmd, { env = {}, cwd = ROOT, allowFail = false } = {}) {
  log(cmd)
  const r = spawnSync(cmd, { shell: true, cwd, stdio: 'inherit', env: { ...process.env, ...env } })
  if (r.status !== 0 && !allowFail) fail(`명령 실패(exit ${r.status}): ${cmd}`)
  return r.status ?? 1
}

const children = []
let exiting = false

function killChild(child) {
  if (!child || child.killed) return
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/pid', String(child.pid), '/t', '/f'], { stdio: 'ignore' })
  } else {
    child.kill()
  }
}

function finishAndExit(code) {
  if (exiting) return
  exiting = true
  for (const c of children) killChild(c)
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

// fetch Set-Cookie → "name=value; name2=value2" Cookie 헤더(세션 쿠키 수동 보관 — Node fetch는 cookie jar 없음).
function cookieFrom(res) {
  const list = res.headers.getSetCookie?.() ?? []
  return list.map((c) => c.split(';')[0]).join('; ')
}

// ─── phase 0: 사전 점검(웜캐시) ────────────────────────────────────────────────

function warmCacheEntries() {
  if (!existsSync(LLM_CACHE_DIR)) return 0
  return readdirSync(LLM_CACHE_DIR).filter((f) => f.endsWith('.json')).length
}

if (!WARM && warmCacheEntries() === 0) {
  fail(
    `웜캐시 비어있음(${LLM_CACHE_DIR}). 무키 E2E는 커밋된 웜캐시가 필요하다.\n` +
      `      OPENAI_API_KEY 보유 상태에서 \`pnpm e2e:warm\` 1회 → \`git add ai/worker/fixtures/llm_cache\`.`,
  )
}
if (WARM && !process.env.OPENAI_API_KEY) {
  fail('--warm은 OPENAI_API_KEY가 필요합니다(웜캐시 생성을 위한 1회 실 LLM 호출).')
}

const dbEnv = { DATABASE_URL }
// worker/api 공통 SQS·캐시 env. 무키 검증은 OPENAI_API_KEY=''로 강제(cache miss가 조용히 통과 못 하게).
// AWS 자격증명은 LocalStack용 더미(SDK/boto3는 서명에 자격증명이 *존재*해야 함 — 값은 무관).
const sqsEnv = {
  SQS_ENDPOINT_URL,
  SQS_QUEUE_URL,
  SQS_STATUS_QUEUE_URL,
  AWS_ACCESS_KEY_ID: process.env.AWS_ACCESS_KEY_ID ?? 'test',
  AWS_SECRET_ACCESS_KEY: process.env.AWS_SECRET_ACCESS_KEY ?? 'test',
  AWS_REGION: process.env.AWS_REGION ?? 'us-east-1',
  AWS_DEFAULT_REGION: process.env.AWS_DEFAULT_REGION ?? 'us-east-1',
}
const keyEnv = { OPENAI_API_KEY: WARM ? (process.env.OPENAI_API_KEY ?? '') : '' }

// ─── 메인 ─────────────────────────────────────────────────────────────────────

async function main() {
  // phase 1: 인프라 기동(Postgres + LocalStack SQS)
  if (!SKIP_COMPOSE) {
    run(`docker compose ${COMPOSE.join(' ')} up -d`)
    await waitFor('postgres healthy', () => {
      const r = spawnSync(
        `docker compose ${COMPOSE.join(' ')} exec -T postgres pg_isready -U podo -d podo`,
        { shell: true, cwd: ROOT, stdio: 'ignore' },
      )
      return r.status === 0
    })
    // LocalStack 큐 생성(init 스크립트)까지 대기 — awslocal로 scoring-queue 존재 확인.
    await waitFor(
      'localstack scoring-queue',
      () => {
        const r = spawnSync(
          `docker compose ${COMPOSE.join(' ')} exec -T localstack awslocal sqs get-queue-url --queue-name scoring-queue`,
          { shell: true, cwd: ROOT, stdio: 'ignore' },
        )
        return r.status === 0
      },
      { tries: 40, gapMs: 2000 },
    )
  }

  // phase 2: 스키마 마이그레이션 + prisma client + 사용자 2명 시드
  run('pnpm --filter @podo/api exec prisma migrate deploy', { env: dbEnv })
  if (run('pnpm --filter @podo/api exec prisma generate', { env: dbEnv, allowFail: true })) {
    log('⚠ prisma generate 실패(기존 client로 진행) — DLL 잠금 가능. api 부팅이 검증.')
  }
  run(
    `pnpm --filter @podo/api exec prisma db execute --file "${SEED_USERS_SQL}" --schema "${PRISMA_SCHEMA}"`,
    { env: dbEnv },
  )

  // phase 3: crawl (fixture)
  run('uv run python -m crawler', {
    env: { ...dbEnv, CRAWL_FIXTURE: resolve(ROOT, 'crawler/fixtures/seed_jobs.txt') },
  })

  // phase 4: api 빌드 + 기동(NODE_ENV=test → test-session 우회 활성, SQS enqueue)
  run('pnpm --filter @podo/api run build', { env: dbEnv })
  const apiEnv = { ...dbEnv, ...sqsEnv, PORT: API_PORT, NODE_ENV: 'test' }
  log('api 기동(node dist/main.js, NODE_ENV=test)')
  const apiChild = spawn('node', ['dist/main.js'], {
    cwd: API_DIR,
    stdio: 'inherit',
    env: { ...process.env, ...apiEnv },
  })
  children.push(apiChild)
  apiChild.on('exit', (code) => {
    if (code && code !== 0 && !apiChild.killed && !exiting) fail(`api 프로세스 종료(exit ${code})`)
  })
  await waitFor('api ready', async () => {
    try {
      return (await fetch(`${base}/api/v1/health`)).ok
    } catch {
      return false
    }
  })

  // phase 5: worker 기동(SQS consumer 상시 — 호스트 프로세스, M4는 컨테이너 아님)
  log(`worker 기동(uv run python -m worker — SQS consumer)${WARM ? ' (실 LLM, 캐시 생성)' : ' (웜캐시)'}`)
  const workerChild = spawn('uv', ['run', 'python', '-m', 'worker'], {
    cwd: ROOT,
    stdio: 'inherit',
    env: { ...process.env, ...dbEnv, ...sqsEnv, ...keyEnv, LLM_CACHE_DIR, REPO_ROOT: ROOT },
  })
  children.push(workerChild)
  workerChild.on('exit', (code) => {
    if (code && code !== 0 && !workerChild.killed && !exiting) fail(`worker 프로세스 종료(exit ${code})`)
  })

  // phase 6: 사용자 A·B — OAuth 우회 로그인 → 업로드 → score(enqueue) → 큐 드레인
  const fixture = readFileSync(PII_FIXTURE, 'utf8')
  const session = {}
  for (const key of ['A', 'B']) {
    const u = USERS[key]
    const sres = await fetch(TEST_SESSION_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId: u.id }),
    })
    if (!sres.ok) fail(`test-session 실패 user=${u.id} → ${sres.status} (NODE_ENV=test 확인)`)
    const cookie = cookieFrom(sres)
    if (!cookie) fail(`test-session 쿠키 미발급 user=${u.id}`)

    const upRes = await fetch(RESUMES_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Cookie: cookie },
      body: JSON.stringify({ text: fixture }),
    })
    if (!upRes.ok) fail(`업로드 실패 user=${u.id} → ${upRes.status}`)
    const resumeId = (await upRes.json()).data.resume_id

    const scRes = await fetch(`${RESUMES_URL}/${resumeId}/score`, {
      method: 'POST',
      headers: { Cookie: cookie },
    })
    if (scRes.status !== 202) {
      fail(`score enqueue 실패 user=${u.id} resume=${resumeId} → ${scRes.status} (202 기대)`)
    }
    const jobId = (await scRes.json()).data.job_id
    session[key] = { ...u, cookie, resumeId, jobId }
    log(`user ${key}: login + upload(resume=${resumeId}) + enqueue(job=${jobId})`)
  }

  // 큐 드레인 — worker가 소비해 ranking_run 생성 → api join으로 done.
  for (const key of ['A', 'B']) {
    const s = session[key]
    await waitFor(
      `user ${key} scoring-job ${s.jobId} done`,
      async () => {
        const res = await fetch(`${SCORING_JOBS_URL}/${s.jobId}`, { headers: { Cookie: s.cookie } })
        if (!res.ok) return false
        const st = (await res.json()).data.status
        if (st === 'failed') fail(`user ${key} scoring-job ${s.jobId} failed`)
        return st === 'done'
      },
      { tries: 60, gapMs: 1500 },
    )
    log(`user ${key}: scoring-job done (큐 드레인 완료)`)
  }

  // phase 7: 각자 격리 피드 검증(적합도 배지·근거·커버리지)
  for (const key of ['A', 'B']) {
    await assertUserFeed(session[key], key)
  }

  // phase 8: 데이터 격리 — A 세션으로 B 자원 접근 차단
  await assertIsolation(session.A, session.B)

  // phase 9: 지원 기록 → 처리완료 정리(누락 0)
  await assertApplicationTracking(session.A)

  // phase 10: PII 스캔 — 이력서 raw(실 masker) + 계정 PII(스코어링 경로 미유입)
  run('uv run python scripts/e2e_pii_scan.py', {
    env: { ...dbEnv, E2E_RESUME_ID: String(session.A.resumeId) },
  })
  run('uv run python scripts/e2e_account_pii_scan.py', { env: { ...dbEnv, LLM_CACHE_DIR } })

  if (WARM) {
    log(`웜캐시 생성됨: ${warmCacheEntries()}개 → \`git add ai/worker/fixtures/llm_cache\` 후 커밋`)
  }
  log('✓ 멀티유저 E2E 통과 — 2-user OAuth 우회 → 업로드 → 큐 채점 → 격리 피드 → 지원 기록 → PII 0')
  finishAndExit(0)
}

async function assertUserFeed(s, label) {
  log(`user ${label} feed/coverage assert`)
  const meta = await (await fetch(`${FEED_URL}/meta`, { headers: { Cookie: s.cookie } })).json()
  if (meta.scoring_status !== 'done') fail(`user ${label} feed meta scoring_status=${meta.scoring_status} (done 기대)`)

  const feed = await (await fetch(FEED_URL, { headers: { Cookie: s.cookie } })).json()
  const items = feed.items ?? []
  if (!items.length) fail(`user ${label} feed 비어있음 — 채점 미반영`)
  const scored = items.filter((it) => it.status === 'scored')
  if (!scored.length) fail(`user ${label} scored 0건 — 무키 채점 전부 held(웜캐시 miss 가능). 캐시 재생성 필요.`)
  for (const it of scored) {
    if (!Number.isInteger(it.fit_level) || it.fit_level < 1 || it.fit_level > 5) {
      fail(`user ${label} scored fit_level 비정상: ${it.fit_level}`)
    }
    if (it.evidence == null) fail(`user ${label} scored evidence 누락`)
  }
  const coverage = await (await fetch(COVERAGE_URL, { headers: { Cookie: s.cookie } })).json()
  if (!Array.isArray(coverage.channels) || !coverage.channels.length) {
    fail(`user ${label} coverage 채널 없음`)
  }
  log(`user ${label} assert 통과 — scored ${scored.length} / held ${items.length - scored.length}`)
}

async function assertIsolation(a, b) {
  log('데이터 격리 assert — A 세션으로 B 자원 접근 차단')
  // 비인증 차단 — 쿠키 없이 피드 접근 → 401
  const anon = await fetch(FEED_URL)
  if (anon.status !== 401) fail(`비인증 피드 접근 차단 실패: ${anon.status} (401 기대)`)

  // A가 B 이력서 채점 시도 → 403/404
  const xs = await fetch(`${RESUMES_URL}/${b.resumeId}/score`, {
    method: 'POST',
    headers: { Cookie: a.cookie },
  })
  if (xs.status !== 403 && xs.status !== 404) {
    fail(`격리 위반: A→B(resume ${b.resumeId}) score = ${xs.status} (403/404 기대)`)
  }
  // A가 B 작업 상태 조회 → 404(존재 노출 금지)
  const xj = await fetch(`${SCORING_JOBS_URL}/${b.jobId}`, { headers: { Cookie: a.cookie } })
  if (xj.status !== 404) fail(`격리 위반: A→B(job ${b.jobId}) 조회 = ${xj.status} (404 기대)`)
  log('격리 assert 통과 — 비인증 401 · A→B 차단(403/404)')
}

async function assertApplicationTracking(s) {
  log('지원 기록 → 처리완료 정리 assert')
  const before = await (await fetch(FEED_URL, { headers: { Cookie: s.cookie } })).json()
  const target = (before.items ?? []).find((it) => it.status === 'scored')
  if (!target) fail('지원 대상 scored 공고 없음')
  const jobId = target.posting.id

  const rec = await fetch(APPLICATIONS_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Cookie: s.cookie },
    body: JSON.stringify({ job_posting_id: jobId, action: 'applied' }),
  })
  if (rec.status !== 201) fail(`지원 기록 실패 → ${rec.status} (201 기대)`)

  const after = await (await fetch(FEED_URL, { headers: { Cookie: s.cookie } })).json()
  if ((after.items ?? []).some((it) => it.posting.id === jobId)) {
    fail(`처리완료 정리 실패: job ${jobId}이 지원 후에도 피드에 잔존`)
  }
  log(`지원 기록 assert 통과 — job ${jobId} applied → 피드 정리`)
}

process.on('SIGINT', () => finishAndExit(130))

main().catch((err) => fail(String(err?.stack ?? err)))
