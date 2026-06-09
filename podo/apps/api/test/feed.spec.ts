import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { type ArgumentsHost, BadRequestException } from '@nestjs/common'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { AllExceptionsFilter } from '../src/common/error.filter'
import { FeedService } from '../src/feed/feed.service'
import { PrismaService } from '../src/prisma/prisma.service'

const hasDb = Boolean(process.env.DATABASE_URL)

// DB 테스트: DATABASE_URL 없으면 skip(로컬 게이트 보호). FeedService를 실 Prisma로 직접 검증.
describe.skipIf(!hasDb)('FeedService (DB)', () => {
  let prisma: PrismaService
  let service: FeedService
  const ids: { resume: number; jobs: number[]; runs: number[] } = {
    resume: 0,
    jobs: [],
    runs: [],
  }

  beforeAll(async () => {
    prisma = new PrismaService()
    await prisma.$connect()
    service = new FeedService(prisma)

    const resume = await prisma.resume.create({
      data: { content: 'feed test resume' },
    })
    ids.resume = resume.id
    const job1 = await prisma.jobPosting.create({
      data: {
        source: 'toss',
        company: 'Toss',
        title: 'FE',
        url: 'https://feedtest/1',
        raw_text: 'jd1',
      },
    })
    const job2 = await prisma.jobPosting.create({
      data: {
        source: 'toss',
        company: 'Toss',
        title: 'BE',
        url: 'https://feedtest/2',
        raw_text: 'jd2',
      },
    })
    ids.jobs = [job1.id, job2.id]

    const base = {
      resume_id: resume.id,
      model: 'm',
      prompt_version: 'v1',
      scoring_mode: 's',
      ranking_mode: 'r',
      cache_key_version: 'v1',
    }
    const oldRun = await prisma.rankingRun.create({
      data: {
        ...base,
        job_set_hash: 'old',
        result: { old: true },
        created_at: new Date('2026-06-06T00:00:00Z'),
      },
    })
    const newRun = await prisma.rankingRun.create({
      data: {
        ...base,
        job_set_hash: 'new',
        result: { new: true, marker: 'EVID' },
        created_at: new Date('2026-06-06T01:00:00Z'),
      },
    })
    ids.runs = [oldRun.id, newRun.id]

    // stale rec (이전 run) — feed에 혼입되면 안 됨
    await prisma.recommendation.create({
      data: {
        run_id: oldRun.id,
        job_posting_id: job1.id,
        rank_position: 0,
        fit_level: 1,
        status: 'scored',
      },
    })
    // current run: scored(rank 0) + held(rank 1, fit null, scored 뒤)
    await prisma.recommendation.create({
      data: {
        run_id: newRun.id,
        job_posting_id: job1.id,
        rank_position: 0,
        fit_level: 5,
        domain_alignment: 'aligned',
        status: 'scored',
      },
    })
    await prisma.recommendation.create({
      data: {
        run_id: newRun.id,
        job_posting_id: job2.id,
        rank_position: 1,
        fit_level: null,
        status: 'held',
      },
    })
  })

  afterAll(async () => {
    if (ids.runs.length) {
      await prisma.recommendation.deleteMany({ where: { run_id: { in: ids.runs } } })
      await prisma.rankingRun.deleteMany({ where: { id: { in: ids.runs } } })
    }
    if (ids.jobs.length) {
      await prisma.jobPosting.deleteMany({ where: { id: { in: ids.jobs } } })
    }
    if (ids.resume) {
      await prisma.resume.deleteMany({ where: { id: ids.resume } })
    }
    await prisma.$disconnect()
  })

  it('test_AC_1_current_run_sorted_cursor_no_stale', async () => {
    const page = await service.getFeed(-1)
    // current run만(2건), 이전 run의 stale rec(fit_level 1) 미혼입
    expect(page.items).toHaveLength(2)
    expect(page.items[0].rank_position).toBe(0)
    expect(page.items[0].status).toBe('scored')
    expect(page.items[0].fit_level).toBe(5)
    expect((page.items[0].posting as { id: number }).id).toBe(ids.jobs[0])
    // held는 scored 뒤(rank 1, fit_level null)
    expect(page.items[1].rank_position).toBe(1)
    expect(page.items[1].status).toBe('held')
    expect(page.items[1].fit_level).toBeNull()
    // cursor: rank_position > 0 → held만
    const page2 = await service.getFeed(0)
    expect(page2.items).toHaveLength(1)
    expect(page2.items[0].rank_position).toBe(1)
  })

  it('test_AC_2_result_opaque_and_error_envelope', async () => {
    const page = await service.getFeed(-1)
    // opaque: 저장된 current run result 그대로(파싱·변형 없음)
    expect(page.items[0].evidence).toEqual({ new: true, marker: 'EVID' })

    // error envelope: 필터가 { error: { code, message } }로 직렬화
    const captured: { status?: number; body?: unknown } = {}
    const host = {
      switchToHttp: () => ({
        getResponse: () => ({
          status: (c: number) => {
            captured.status = c
            return {
              json: (b: unknown) => {
                captured.body = b
              },
            }
          },
        }),
      }),
    } as unknown as ArgumentsHost
    new AllExceptionsFilter().catch(new BadRequestException('bad cursor'), host)
    expect(captured.status).toBe(400)
    expect(captured.body).toEqual({
      error: { code: 'BAD_REQUEST', message: 'bad cursor' },
    })
  })
})

describe('Feed read-only (static, AC-3)', () => {
  it('test_AC_3_read_only_no_writes', () => {
    const src = readFileSync(join(__dirname, '..', 'src', 'feed', 'feed.service.ts'), 'utf-8')
    // worker/crawler 소유 테이블에 write 메서드 호출 0 (read-only, §3-2 규칙1)
    expect(src).not.toMatch(/\.(create|createMany|update|updateMany|delete|deleteMany|upsert)\(/)
  })
})

// T-092 AC-2 — include_recent_processed=7d면 최근 7일 처리분이 재노출되고, 7일보다 오래된 처리는 계속 제외.
// fake Prisma로 getFeed의 제외 로직을 결정적으로 검증(DB 불필요 — 키리스 게이트 실행).
describe('FeedService include_recent_processed (AC-2)', () => {
  const REC1 = {
    job_posting_id: 1,
    job_posting: { id: 1 },
    fit_level: 5,
    rank_position: 0,
    status: 'scored',
    run: { result: { e: 1 } },
  }
  const REC2 = {
    job_posting_id: 2,
    job_posting: { id: 2 },
    fit_level: 4,
    rank_position: 1,
    status: 'scored',
    run: { result: { e: 1 } },
  }

  function makeService(captured: { processedWhere?: Record<string, unknown> }) {
    const prisma = {
      rankingRun: { findFirst: async () => ({ id: 99 }) },
      // job1=최근 처리, job2=오래된 처리. created_at 필터(includeRecentProcessed) 있으면 오래된 것만 제외.
      applicationEvent: {
        findMany: async ({ where }: { where: Record<string, unknown> }) => {
          captured.processedWhere = where
          return where.created_at
            ? [{ job_posting_id: 2 }]
            : [{ job_posting_id: 1 }, { job_posting_id: 2 }]
        },
      },
      recommendation: {
        findMany: async ({ where }: { where: { job_posting_id?: { notIn?: number[] } } }) => {
          const excluded = where.job_posting_id?.notIn ?? []
          return [REC1, REC2].filter((r) => !excluded.includes(r.job_posting_id))
        },
      },
    }
    return new FeedService(prisma as unknown as PrismaService)
  }

  it('test_AC_2_include_recent_processed', async () => {
    const captured: { processedWhere?: Record<string, unknown> } = {}
    const service = makeService(captured)

    // 기본(플래그 없음): job1·job2 모두 처리완료 → 제외 → 빈 피드.
    const base = await service.getFeed(-1, 'u1')
    expect(base.items).toHaveLength(0)
    expect(captured.processedWhere?.created_at).toBeUndefined()

    // include_recent_processed: 최근 처리(job1) 재노출, 오래된 처리(job2)는 계속 제외.
    const resurfaced = await service.getFeed(-1, 'u1', 20, undefined, true)
    expect(resurfaced.items).toHaveLength(1)
    expect((resurfaced.items[0].posting as { id: number }).id).toBe(1)

    // 컷오프는 ~7일 전(now - 7d). lt 방향(오래된 것 제외) 검증.
    const cutoff = (captured.processedWhere?.created_at as { lt: Date }).lt
    const daysAgo = (Date.now() - cutoff.getTime()) / (24 * 60 * 60 * 1000)
    expect(daysAgo).toBeGreaterThan(6.9)
    expect(daysAgo).toBeLessThan(7.1)
  })
})
