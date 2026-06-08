import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { FeedService } from '../src/feed/feed.service'
import { PrismaService } from '../src/prisma/prisma.service'

const hasDb = Boolean(process.env.DATABASE_URL)

// T-065 AC-3: coarse 섹션은 fit_level 없이 유사도 rank만 서빙(ADR-108 D3, Guardrail 1).
describe.skipIf(!hasDb)('FeedService coarse section (T-065 AC-3, DB)', () => {
  let prisma: PrismaService
  let service: FeedService
  let userId: string
  let resumeId: number
  const jobIds: number[] = []

  beforeAll(async () => {
    prisma = new PrismaService()
    await prisma.$connect()
    service = new FeedService(prisma)

    const user = await prisma.user.create({
      data: {
        provider: 'test',
        provider_account_id: 'coarse-test-1',
        email: 'coarse@test.local',
        display_name: 'CO',
      },
    })
    userId = user.id
    const resume = await prisma.resume.create({
      data: { content: '백엔드', user_id: userId },
    })
    resumeId = resume.id
    for (let i = 0; i < 2; i++) {
      const jp = await prisma.jobPosting.create({
        data: {
          source: 'test',
          company: `CoarseCo${i}`,
          title: `BE ${i}`,
          url: `https://coarse.test/${i}`,
          raw_text: 'jd',
        },
      })
      jobIds.push(jp.id)
      await prisma.coarseCandidate.create({
        data: {
          job_posting_id: jp.id,
          resume_id: resumeId,
          user_id: userId,
          similarity_rank: 0.9 - i * 0.1,
          cache_key_version: 'v1',
        },
      })
    }
  })

  afterAll(async () => {
    await prisma.coarseCandidate.deleteMany({ where: { resume_id: resumeId } })
    await prisma.jobPosting.deleteMany({ where: { id: { in: jobIds } } })
    await prisma.resume.deleteMany({ where: { id: resumeId } })
    await prisma.user.deleteMany({ where: { id: userId } })
    await prisma.$disconnect()
  })

  it('test_AC_3_coarse_section_no_fit_level', async () => {
    const page = await service.getCoarseFeed(-1, userId)
    expect(page.items.length).toBe(2)
    // 유사도 desc 정렬(결정적)
    expect(page.items[0].similarity_rank).toBeGreaterThanOrEqual(page.items[1].similarity_rank)
    for (const item of page.items) {
      // fit_level 필드 부재(coarse = deep 분석 전)
      expect(item).not.toHaveProperty('fit_level')
      expect(typeof item.similarity_rank).toBe('number')
      expect(item.posting).toBeTruthy()
    }
  })
})
