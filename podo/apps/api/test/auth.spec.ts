import 'reflect-metadata'
import { type ExecutionContext, ForbiddenException, UnauthorizedException } from '@nestjs/common'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { AuthController } from '../src/auth/auth.controller'
import { AuthService } from '../src/auth/auth.service'
import { SessionGuard } from '../src/auth/session.guard'
import { FeedService } from '../src/feed/feed.service'
import { PrismaService } from '../src/prisma/prisma.service'
import type { QueueService } from '../src/queue/queue.service'
import { RegexResumeMaskerStub } from '../src/resumes/resume-masker.port'
import { ResumesService } from '../src/resumes/resumes.service'

const hasDb = Boolean(process.env.DATABASE_URL)

function ctxWith(isAuthenticated: boolean): ExecutionContext {
  return {
    switchToHttp: () => ({ getRequest: () => ({ isAuthenticated: () => isAuthenticated }) }),
  } as unknown as ExecutionContext
}

// AC-3 — 프로덕션 빌드에서 test-session 우회 비활성(403).
describe('AuthController test-session 프로덕션 비활성 (AC-3)', () => {
  it('test_AC_3_test_session_disabled_in_production', () => {
    const prev = process.env.NODE_ENV
    process.env.NODE_ENV = 'production'
    try {
      const controller = new AuthController()
      const req = { login: () => {} } as never
      const res = { status: () => ({ json: () => {} }), redirect: () => {} } as never
      expect(() => controller.testSession({ userId: 'u1' }, req, res)).toThrow(ForbiddenException)
    } finally {
      process.env.NODE_ENV = prev
    }
  })
})

// AC-1 — test-session이 세션을 발급(req.login(userId))하고, 인증 세션으로 보호 라우트(가드) 통과.
describe('AuthController test-session 발급 + SessionGuard 통과 (AC-1)', () => {
  it('test_AC_1_test_session_issues_session_and_feed_guard_allows', () => {
    const prev = process.env.NODE_ENV
    process.env.NODE_ENV = 'test'
    try {
      const controller = new AuthController()
      const logged: Array<{ id: string }> = []
      let status = 0
      const req = {
        login: (u: { id: string }, cb: (err?: unknown) => void) => {
          logged.push(u)
          cb()
        },
      } as never
      const res = {
        status: (c: number) => {
          status = c
          return { json: () => {} }
        },
        redirect: () => {},
      } as never
      controller.testSession({ userId: 'user-A' }, req, res)
      // 세션에 userId 시드 발급(httpOnly 쿠키 — express-session 미들웨어가 직렬화)
      expect(logged).toEqual([{ id: 'user-A' }])
      expect(status).toBe(200)
    } finally {
      process.env.NODE_ENV = prev
    }

    // 발급된 세션(isAuthenticated=true)으로 보호 라우트(/api/v1/feed) 가드 통과 → 200 경로 진입.
    const guard = new SessionGuard()
    expect(guard.canActivate(ctxWith(true))).toBe(true)
  })
})

// OAuth 콜백이 세션을 직렬화(req.login)하는지 — AuthGuard는 req.user만 설정하므로 콜백에서 직접 login해야
// 세션 쿠키가 발급된다(이게 없으면 인증돼도 세션 미생성 → /auth/me 등 401). 실 배포 로그인 회귀 방지.
describe('AuthController OAuth 콜백 세션 발급', () => {
  it('test_oauth_callback_calls_req_login_then_redirects_web', () => {
    const controller = new AuthController()
    const logged: Array<{ id: string }> = []
    let redirectedTo = ''
    const req = {
      user: { id: 'u-cb' },
      login: (u: { id: string }, cb: (err?: unknown) => void) => {
        logged.push(u)
        cb()
      },
    } as never
    const res = {
      redirect: (url: string) => {
        redirectedTo = url
      },
    } as never
    controller.googleCallback(req, res)
    // 세션 직렬화 호출됨 + 성공 시 web(CORS_ALLOWED_ORIGIN fallback)으로 redirect
    expect(logged).toEqual([{ id: 'u-cb' }])
    expect(redirectedTo).toBe('http://localhost:3000')
  })

  it('test_oauth_callback_redirects_login_on_session_error', () => {
    const controller = new AuthController()
    let redirectedTo = ''
    const req = {
      user: { id: 'u-cb' },
      login: (_u: { id: string }, cb: (err?: unknown) => void) => cb(new Error('session fail')),
    } as never
    const res = {
      redirect: (url: string) => {
        redirectedTo = url
      },
    } as never
    controller.githubCallback(req, res)
    expect(redirectedTo).toBe('http://localhost:3000/login?error=session')
  })
})

// /auth/me — 인증 세션이면 userId 반환(web 클라이언트 가드 질의용). 비인증 401은 SessionGuard(AC-2)가 담당.
describe('AuthController /auth/me 세션 확인', () => {
  it('test_me_returns_userid_for_authenticated_session', () => {
    const controller = new AuthController()
    expect(controller.me({ user: { id: 'user-Z' } })).toEqual({ data: { userId: 'user-Z' } })
  })
})

// AC-2 — 횡단 접근 차단: 비인증 401 + (DB) 타인 이력서 채점 403 + (DB) 피드 사용자 격리.
describe('데이터 격리 — 횡단 접근 차단 (AC-2)', () => {
  it('test_AC_2_unauthenticated_blocked_401', () => {
    const guard = new SessionGuard()
    expect(() => guard.canActivate(ctxWith(false))).toThrow(UnauthorizedException)
  })

  const noopQueue = { enqueue: async () => {} } as unknown as QueueService

  describe.skipIf(!hasDb)('DB 격리', () => {
    let prisma: PrismaService
    const userIds: string[] = []
    const resumeIds: number[] = []
    const jobIds: number[] = []
    const runIds: number[] = []
    let userA = ''
    let userB = ''
    let resumeB = 0

    beforeAll(async () => {
      prisma = new PrismaService()
      await prisma.$connect()
      const a = await prisma.user.create({
        data: {
          provider: 'github',
          provider_account_id: 'acc-A',
          email: 'a@t.io',
          display_name: 'A',
        },
      })
      const b = await prisma.user.create({
        data: {
          provider: 'github',
          provider_account_id: 'acc-B',
          email: 'b@t.io',
          display_name: 'B',
        },
      })
      userA = a.id
      userB = b.id
      userIds.push(a.id, b.id)

      const rB = await prisma.resume.create({ data: { content: 'B resume', user_id: b.id } })
      const rA = await prisma.resume.create({ data: { content: 'A resume', user_id: a.id } })
      resumeB = rB.id
      resumeIds.push(rA.id, rB.id)

      const job = await prisma.jobPosting.create({
        data: { source: 'toss', company: 'T', title: 'FE', url: 'https://iso/1', raw_text: 'jd' },
      })
      jobIds.push(job.id)

      const base = {
        model: 'm',
        prompt_version: 'v1',
        scoring_mode: 's',
        ranking_mode: 'r',
        cache_key_version: 'v1',
      }
      // A의 run(먼저), B의 run(나중 — 전역 최신). 격리 안 되면 A 피드에 B run이 새어든다.
      const runA = await prisma.rankingRun.create({
        data: {
          ...base,
          resume_id: rA.id,
          job_set_hash: 'A',
          result: { who: 'A' },
          created_at: new Date('2026-06-06T00:00:00Z'),
        },
      })
      const runB = await prisma.rankingRun.create({
        data: {
          ...base,
          resume_id: rB.id,
          job_set_hash: 'B',
          result: { who: 'B' },
          created_at: new Date('2026-06-06T05:00:00Z'),
        },
      })
      runIds.push(runA.id, runB.id)
      await prisma.recommendation.create({
        data: {
          run_id: runA.id,
          job_posting_id: job.id,
          rank_position: 0,
          fit_level: 3,
          status: 'scored',
        },
      })
      await prisma.recommendation.create({
        data: {
          run_id: runB.id,
          job_posting_id: job.id,
          rank_position: 0,
          fit_level: 5,
          status: 'scored',
        },
      })
    })

    afterAll(async () => {
      await prisma.recommendation.deleteMany({ where: { run_id: { in: runIds } } })
      await prisma.rankingRun.deleteMany({ where: { id: { in: runIds } } })
      await prisma.jobPosting.deleteMany({ where: { id: { in: jobIds } } })
      await prisma.resume.deleteMany({ where: { id: { in: resumeIds } } })
      await prisma.user.deleteMany({ where: { id: { in: userIds } } })
      await prisma.$disconnect()
    })

    it('test_AC_2_cross_user_score_blocked_403', async () => {
      const service = new ResumesService(prisma, new RegexResumeMaskerStub(), noopQueue)
      // A 세션이 B 소유 이력서를 채점 시도 → 403(존재 노출 없이 차단)
      let caught: { getStatus(): number; getResponse(): unknown } | undefined
      try {
        await service.score(resumeB, userA)
      } catch (e) {
        caught = e as never
      }
      expect(caught?.getStatus()).toBe(403)
      expect((caught?.getResponse() as { code: string }).code).toBe('RESUME_FORBIDDEN')
    })

    it('test_AC_2_feed_scoped_to_user_no_cross_leak', async () => {
      const feed = new FeedService(prisma)
      const aFeed = await feed.getFeed(-1, userA)
      // A 피드엔 A run만 — B run이 전역 최신이어도 새어들지 않는다.
      expect(aFeed.items).toHaveLength(1)
      expect(aFeed.items[0].evidence).toEqual({ who: 'A' })

      const bFeed = await feed.getFeed(-1, userB)
      expect(bFeed.items[0].evidence).toEqual({ who: 'B' })
    })
  })
})

// AC-5 — OAuth callback이 (provider, account_id)로 upsert(최초 생성/재로그인 매칭) + 토큰 미저장.
describe.skipIf(!hasDb)('AuthService.findOrCreateUser upsert (AC-5, DB)', () => {
  let prisma: PrismaService
  const created: string[] = []

  beforeAll(async () => {
    prisma = new PrismaService()
    await prisma.$connect()
  })
  afterAll(async () => {
    if (created.length) await prisma.user.deleteMany({ where: { id: { in: created } } })
    await prisma.$disconnect()
  })

  it('test_AC_5_oauth_callback_upserts_user_and_no_token', async () => {
    const service = new AuthService(prisma)
    const profile = { providerAccountId: 'gh-AC5', email: 'x@y.io', displayName: 'X' }
    const u1 = await service.findOrCreateUser('github', profile)
    created.push(u1.id)
    const u2 = await service.findOrCreateUser('github', profile)
    // 재로그인 → 동일 계정 매칭(중복 생성 X)
    expect(u2.id).toBe(u1.id)

    const row = await prisma.user.findUnique({ where: { id: u1.id } })
    expect(row).not.toBeNull()
    expect(row?.provider).toBe('github')
    expect(row?.provider_account_id).toBe('gh-AC5')
    // OAuth access/refresh token 미영속 — users 스키마에 토큰 컬럼 부재(ADR-105 Amend1 §2)
    expect(Object.keys(row as object)).not.toContain('access_token')
    expect(Object.keys(row as object)).not.toContain('refresh_token')
  })
})
