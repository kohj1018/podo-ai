/**
 * T-050 ApplicationsModule 테스트 (AC-1, AC-2, AC-3)
 * DATABASE_URL 없으면 전체 skip(로컬 게이트 보호).
 */
import { ForbiddenException } from '@nestjs/common'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { ApplicationsService } from '../src/applications/applications.service'
import { FeedService } from '../src/feed/feed.service'
import { PrismaService } from '../src/prisma/prisma.service'

const hasDb = Boolean(process.env.DATABASE_URL)

describe.skipIf(!hasDb)('ApplicationsService (DB)', () => {
  let prisma: PrismaService
  let service: ApplicationsService
  let feed: FeedService

  // 테스트 데이터 ID 추적 (afterAll cleanup)
  const ids = {
    userA: '',
    userB: '',
    resumeA: 0,
    resumeB: 0,
    jobs: [] as number[],
    runIds: [] as number[],
    eventIds: [] as number[],
  }

  beforeAll(async () => {
    prisma = new PrismaService()
    await prisma.$connect()
    service = new ApplicationsService(prisma)
    feed = new FeedService(prisma)

    // 사용자 A, B 생성
    const userA = await prisma.user.create({
      data: {
        provider: 'github',
        provider_account_id: 'app-test-A',
        email: 'app-a@test.io',
        display_name: 'AppTestA',
      },
    })
    const userB = await prisma.user.create({
      data: {
        provider: 'github',
        provider_account_id: 'app-test-B',
        email: 'app-b@test.io',
        display_name: 'AppTestB',
      },
    })
    ids.userA = userA.id
    ids.userB = userB.id

    // 이력서 A
    const resumeA = await prisma.resume.create({
      data: { content: 'app test resume A', user_id: userA.id },
    })
    const resumeB = await prisma.resume.create({
      data: { content: 'app test resume B', user_id: userB.id },
    })
    ids.resumeA = resumeA.id
    ids.resumeB = resumeB.id

    // 공고 3개 생성
    const job1 = await prisma.jobPosting.create({
      data: {
        source: 'toss',
        company: 'Co1',
        title: 'FE1',
        url: 'https://apptest/j1',
        raw_text: 'jd1',
      },
    })
    const job2 = await prisma.jobPosting.create({
      data: {
        source: 'toss',
        company: 'Co2',
        title: 'FE2',
        url: 'https://apptest/j2',
        raw_text: 'jd2',
      },
    })
    const job3 = await prisma.jobPosting.create({
      data: {
        source: 'toss',
        company: 'Co3',
        title: 'FE3',
        url: 'https://apptest/j3',
        raw_text: 'jd3',
      },
    })
    ids.jobs = [job1.id, job2.id, job3.id]

    // A의 ranking_run + recommendation (3개 공고 포함)
    const runA = await prisma.rankingRun.create({
      data: {
        resume_id: resumeA.id,
        job_set_hash: 'app-hash-A',
        model: 'm',
        prompt_version: 'v1',
        scoring_mode: 's',
        ranking_mode: 'r',
        cache_key_version: 'v1',
        result: { test: 'A' },
      },
    })
    ids.runIds.push(runA.id)

    for (let i = 0; i < 3; i++) {
      await prisma.recommendation.create({
        data: {
          run_id: runA.id,
          job_posting_id: ids.jobs[i],
          rank_position: i,
          fit_level: 5 - i,
          status: 'scored',
        },
      })
    }
  })

  afterAll(async () => {
    // application_events → recommendations → ranking_runs → job_postings → resumes → users 순으로 삭제
    if (ids.eventIds.length) {
      await prisma.applicationEvent.deleteMany({ where: { id: { in: ids.eventIds } } })
    }
    // 테스트 중 생성된 나머지 이벤트도 정리
    await prisma.applicationEvent.deleteMany({
      where: { user_id: { in: [ids.userA, ids.userB].filter(Boolean) } },
    })
    if (ids.runIds.length) {
      await prisma.recommendation.deleteMany({ where: { run_id: { in: ids.runIds } } })
      await prisma.rankingRun.deleteMany({ where: { id: { in: ids.runIds } } })
    }
    if (ids.jobs.length) {
      await prisma.jobPosting.deleteMany({ where: { id: { in: ids.jobs } } })
    }
    if (ids.resumeA) await prisma.resume.deleteMany({ where: { id: ids.resumeA } })
    if (ids.resumeB) await prisma.resume.deleteMany({ where: { id: ids.resumeB } })
    if (ids.userA) await prisma.user.deleteMany({ where: { id: ids.userA } })
    if (ids.userB) await prisma.user.deleteMany({ where: { id: ids.userB } })
    await prisma.$disconnect()
  })

  // AC-1: applied/skipped 기록 후 피드에서 해당 공고 제외 (즐겨찾기는 예외)
  it('test_AC_1_applied_recorded_and_cleared_from_feed', async () => {
    // job1 → applied, job2 → skipped
    const ev1 = await service.recordAction(ids.userA, ids.jobs[0], 'applied')
    const ev2 = await service.recordAction(ids.userA, ids.jobs[1], 'skipped')
    ids.eventIds.push(ev1.id, ev2.id)

    // 기록이 user_id 포함으로 저장됐는지 확인
    expect(ev1.user_id).toBe(ids.userA)
    expect(ev1.job_posting_id).toBe(ids.jobs[0])
    expect(ev1.action).toBe('applied')
    expect(ev2.action).toBe('skipped')

    // 피드 조회 시 applied/skipped 공고 제외 — job3만 남아야 함
    const page = await feed.getFeed(-1, ids.userA)
    const postingIds = page.items.map((item) => (item.posting as { id: number }).id)
    expect(postingIds).not.toContain(ids.jobs[0]) // applied 제외
    expect(postingIds).not.toContain(ids.jobs[1]) // skipped 제외
    expect(postingIds).toContain(ids.jobs[2]) // 미처리 유지
  })

  // AC-2: favorite 기록 후 필터 조회 시 반환 (점수 무관)
  it('test_AC_2_favorite_preserved_regardless_of_score', async () => {
    const ev = await service.recordAction(ids.userA, ids.jobs[2], 'favorite')
    ids.eventIds.push(ev.id)

    const favorites = await service.getActions(ids.userA, 'favorite')
    expect(favorites.some((e) => e.job_posting_id === ids.jobs[2])).toBe(true)
    // 즐겨찾기는 피드에서 제외 안 됨 — job3이 favorite이어도 기본 피드에 유지
    const page = await feed.getFeed(-1, ids.userA)
    const postingIds = page.items.map((item) => (item.posting as { id: number }).id)
    expect(postingIds).toContain(ids.jobs[2])
  })

  // AC-3: 사용자 A 기록을 사용자 B가 조회/수정 시 403
  it('test_AC_3_cross_user_access_blocked', async () => {
    // B가 A의 application을 조회 시도 → A 기록 노출 안 됨 (격리)
    const bActions = await service.getActions(ids.userB, undefined)
    const allJobIds = bActions.map((e) => e.job_posting_id)
    // A의 job1, job2는 B 조회에 나오면 안 됨
    expect(allJobIds).not.toContain(ids.jobs[0])
    expect(allJobIds).not.toContain(ids.jobs[1])

    // B가 A의 event에 action 기록 시도 시 user_id 격리(서비스 레이어는 본인만 기록)
    // recordAction은 user_id를 파라미터로 받으므로 격리는 컨트롤러 레이어에서 보장
    // 여기서는 서비스가 cross-user delete/modify를 차단하는지 확인
    let caught: unknown
    try {
      await service.deleteAction(ids.userB, ids.eventIds[0]) // A의 event를 B가 삭제 시도
    } catch (e) {
      caught = e
    }
    expect(caught).toBeInstanceOf(ForbiddenException)
  })
})
