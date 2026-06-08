import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { CoverageService } from '../src/coverage/coverage.service'
import { PrismaService } from '../src/prisma/prisma.service'

const hasDb = Boolean(process.env.DATABASE_URL)

describe.skipIf(!hasDb)('CoverageService (DB, source_crawl_status)', () => {
  let prisma: PrismaService
  let service: CoverageService
  const sourceIds = ['toss', 'kb-bank']

  beforeAll(async () => {
    prisma = new PrismaService()
    await prisma.$connect()
    service = new CoverageService(prisma)

    // toss=active(수집 성공) / kb-bank=login-required(미수집·투명 노출)
    await prisma.sourceCrawlStatus.upsert({
      where: { source_id: 'toss' },
      create: {
        source_id: 'toss',
        tier: '3',
        method: 'custom',
        status: 'active',
        last_success_at: new Date('2026-06-07T01:00:00Z'),
      },
      update: { status: 'active', last_success_at: new Date('2026-06-07T01:00:00Z') },
    })
    await prisma.sourceCrawlStatus.upsert({
      where: { source_id: 'kb-bank' },
      create: {
        source_id: 'kb-bank',
        tier: '5',
        method: 'incruit',
        status: 'login-required',
        last_error: 'login-required: 목록 view 로그인 필요',
      },
      update: { status: 'login-required' },
    })
  })

  const lastCrawlRunAt = new Date('2026-12-31T21:00:00Z') // 테스트 fixture 중 최신 보장

  afterAll(async () => {
    await prisma.sourceCrawlStatus.deleteMany({ where: { source_id: { in: sourceIds } } })
    await prisma.crawlRun.deleteMany({ where: { run_at: lastCrawlRunAt } })
    await prisma.$disconnect()
  })

  it('test_AC_1_sources_upsert_and_coverage_status', async () => {
    const cov = await service.getCoverage()

    const toss = cov.channels.find((c) => c.name === 'toss')
    expect(toss).toBeDefined()
    expect(toss?.status).toBe('active')
    expect(toss?.tier).toBe('3')
    expect(toss?.last_success_at?.toISOString()).toBe('2026-06-07T01:00:00.000Z')

    // kb-bank=login-required → 미수집(active 아님) + 투명 노출
    const kb = cov.channels.find((c) => c.name === 'kb-bank')
    expect(kb?.status).toBe('login-required')
    expect(cov.uncollected).toContain('kb-bank')
    // active 아닌 소스 존재 → degraded(거짓 완전성 차단)
    expect(cov.degraded).toBe(true)
  })

  it('test_AC_3_last_crawl_from_crawl_runs', async () => {
    // 동일 run_at 배치: toss 성공 + daangn 실패 → lastCrawlSuccess=false (Fail #3 가시화)
    await prisma.crawlRun.createMany({
      data: [
        { channel: 'toss', run_at: lastCrawlRunAt, status: 'success', new_count: 3 },
        { channel: 'daangn', run_at: lastCrawlRunAt, status: 'failed', error: 'network down' },
      ],
    })

    const cov = await service.getCoverage()

    expect(cov.lastCrawlAt?.toISOString()).toBe('2026-12-31T21:00:00.000Z')
    expect(cov.lastCrawlSuccess).toBe(false)
  })
})

describe('Coverage read-only (static, AC-2)', () => {
  it('test_AC_2_read_only', () => {
    const src = readFileSync(
      join(__dirname, '..', 'src', 'coverage', 'coverage.service.ts'),
      'utf-8',
    )
    expect(src).not.toMatch(/\.(create|createMany|update|updateMany|delete|deleteMany|upsert)\(/)
  })
})
