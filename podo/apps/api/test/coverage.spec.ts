import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { CoverageService } from '../src/coverage/coverage.service'
import { PrismaService } from '../src/prisma/prisma.service'

const hasDb = Boolean(process.env.DATABASE_URL)

describe.skipIf(!hasDb)('CoverageService (DB)', () => {
  let prisma: PrismaService
  let service: CoverageService
  const runIds: number[] = []

  beforeAll(async () => {
    prisma = new PrismaService()
    await prisma.$connect()
    service = new CoverageService(prisma)

    const mk = async (status: string, iso: string): Promise<void> => {
      const r = await prisma.crawlRun.create({
        data: { channel: 'toss', status, run_at: new Date(iso) },
      })
      runIds.push(r.id)
    }
    await mk('success', '2026-06-06T00:00:00Z')
    await mk('success', '2026-06-06T01:00:00Z') // MAX success
    await mk('failed', '2026-06-06T02:00:00Z') // 최신 status
  })

  afterAll(async () => {
    if (runIds.length) {
      await prisma.crawlRun.deleteMany({ where: { id: { in: runIds } } })
    }
    await prisma.$disconnect()
  })

  it('test_AC_1_last_success_at_per_channel', async () => {
    const cov = await service.getCoverage()
    const toss = cov.channels.find((c) => c.name === 'toss')
    expect(toss).toBeDefined()
    expect(toss?.status).toBe('failed') // 최신 run status
    // last_success_at = MAX(run_at WHERE success) — 최신(failed)이 아니라 직전 success
    expect(toss?.last_success_at?.toISOString()).toBe('2026-06-06T01:00:00.000Z')
    // daangn: 수집 0 → uncollected
    expect(cov.uncollected).toContain('daangn')
    const daangn = cov.channels.find((c) => c.name === 'daangn')
    expect(daangn?.status).toBeNull()
    expect(daangn?.last_success_at).toBeNull()
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
