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
