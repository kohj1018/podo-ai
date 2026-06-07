import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { FeedService } from '../src/feed/feed.service'
import { PrismaService } from '../src/prisma/prisma.service'

const hasDb = Boolean(process.env.DATABASE_URL)

// T-066 AC-5: worker가 영속한 resume_domains를 api(feed meta)가 read-only로 서빙한다(T-067 탭 계약).
describe.skipIf(!hasDb)('FeedService resume_domains (T-066 AC-5, DB)', () => {
  let prisma: PrismaService
  let service: FeedService
  let userId: string
  let resumeId: number

  beforeAll(async () => {
    prisma = new PrismaService()
    await prisma.$connect()
    service = new FeedService(prisma)

    const user = await prisma.user.create({
      data: {
        provider: 'test',
        provider_account_id: 'rd-test-1',
        email: 'rd@test.local',
        display_name: 'RD',
      },
    })
    userId = user.id
    const resume = await prisma.resume.create({
      data: { content: '백엔드 이력서', user_id: userId },
    })
    resumeId = resume.id
    await prisma.resumeDomains.create({
      data: {
        resume_id: resumeId,
        primary_domains: ['backend'],
        secondary_domains: ['data'],
        confidence: 'high',
        classifier_version: 'v1',
      },
    })
  })

  afterAll(async () => {
    await prisma.resumeDomains.deleteMany({ where: { resume_id: resumeId } })
    await prisma.resume.deleteMany({ where: { id: resumeId } })
    await prisma.user.deleteMany({ where: { id: userId } })
    await prisma.$disconnect()
  })

  it('test_AC_5_feed_meta_serves_resume_domains', async () => {
    const meta = await service.getFeedMeta(userId)
    expect(meta.has_resume).toBe(true)
    expect(meta.resume_domains).not.toBeNull()
    expect(meta.resume_domains?.primary_domains).toEqual(['backend'])
    expect(meta.resume_domains?.secondary_domains).toEqual(['data'])
    expect(meta.resume_domains?.confidence).toBe('high')
    expect(meta.resume_domains?.classifier_version).toBe('v1')
  })

  it('test_AC_5_no_domains_returns_null', async () => {
    const user2 = await prisma.user.create({
      data: {
        provider: 'test',
        provider_account_id: 'rd-test-2',
        email: 'rd2@test.local',
        display_name: 'RD2',
      },
    })
    const r2 = await prisma.resume.create({
      data: { content: 'no domains', user_id: user2.id },
    })
    try {
      const meta = await service.getFeedMeta(user2.id)
      expect(meta.has_resume).toBe(true)
      expect(meta.resume_domains).toBeNull()
    } finally {
      await prisma.resume.deleteMany({ where: { id: r2.id } })
      await prisma.user.deleteMany({ where: { id: user2.id } })
    }
  })
})
