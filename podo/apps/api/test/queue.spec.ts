import 'reflect-metadata'
import { HttpException } from '@nestjs/common'
import { describe, expect, it } from 'vitest'
import type { PrismaService } from '../src/prisma/prisma.service'
import { QueueService } from '../src/queue/queue.service'
import type { ResumeMasker } from '../src/resumes/resume-masker.port'
import { ResumesController } from '../src/resumes/resumes.controller'
import { ResumesService } from '../src/resumes/resumes.service'
import { ScoringJobsController } from '../src/scoring-jobs/scoring-jobs.controller'

// AC-3 — subprocess spawn 코드 부재 (소스 grep으로 확인)
describe('AC-3 no subprocess spawn in source', () => {
  it('test_AC_3_no_subprocess_spawn_in_source', async () => {
    // worker-runner.port.ts에는 SubprocessWorkerRunner가 남아있을 수 있으나
    // resumes.service.ts / resumes.controller.ts에서 spawn 직접 사용이 없어야 함.
    // resumes.service.ts가 WorkerRunner를 직접 spawn하지 않고 QueueService를 사용하는지 확인.
    const { ResumesService } = await import('../src/resumes/resumes.service')
    const src = ResumesService.toString()
    // score() 메서드가 workerRunner.run()을 호출하지 않음
    expect(src).not.toContain('workerRunner.run')
    expect(src).not.toContain('uv run python')
  })
})

// AC-1 — POST /resumes/:id/score → 202 + { job_id, status: 'queued' }
describe('AC-1 score endpoint enqueues and returns 202 queued', () => {
  it('test_AC_1_score_endpoint_enqueues_and_returns_202_queued', async () => {
    const enqueuedMessages: Array<{ resumeId: number; jobId: string }> = []

    const fakeQueueService = {
      enqueue: async (resumeId: number, jobId: string) => {
        enqueuedMessages.push({ resumeId, jobId })
      },
    } as unknown as QueueService

    const fakePrisma = {
      resume: {
        findUnique: async ({ where }: { where: { id: number } }) =>
          where.id === 1 ? { id: 1, user_id: 'user-1' } : null,
      },
      scoringJob: {
        create: async ({ data }: { data: { resume_id: number; status: string } }) => ({
          id: 'job-abc-123',
          resume_id: data.resume_id,
          status: data.status,
        }),
      },
    } as unknown as PrismaService

    const service = new ResumesService(
      fakePrisma,
      { mask: (t: string) => ({ masked: t, placeholders: 0 }) } as unknown as ResumeMasker,
      fakeQueueService,
    )
    const controller = new ResumesController(service)

    const result = await controller.score('1', { user: { id: 'user-1' } })

    expect(result.data.status).toBe('queued')
    expect(result.data.job_id).toBeDefined()
    expect(typeof result.data.job_id).toBe('string')
    expect(enqueuedMessages).toHaveLength(1)
    expect(enqueuedMessages[0].resumeId).toBe(1)
  })

  it('test_AC_1_score_unknown_resume_404', async () => {
    const fakePrisma = {
      resume: { findUnique: async () => null },
    } as unknown as PrismaService

    const service = new ResumesService(
      fakePrisma,
      { mask: (t: string) => ({ masked: t, placeholders: 0 }) } as unknown as ResumeMasker,
      { enqueue: async () => {} } as unknown as QueueService,
    )
    const controller = new ResumesController(service)

    let caught: HttpException | undefined
    try {
      await controller.score('999', { user: { id: 'user-1' } })
    } catch (e) {
      caught = e as HttpException
    }
    expect(caught).toBeInstanceOf(HttpException)
    expect(caught?.getStatus()).toBe(404)
  })
})

// AC-2 — GET /scoring-jobs/:job_id → status 반환, 타 사용자 접근 시 404
describe('AC-2 scoring jobs polling returns status and blocks cross-user', () => {
  it('test_AC_2_scoring_jobs_polling_returns_status', async () => {
    const fakePrisma = {
      scoringJob: {
        findUnique: async ({ where }: { where: { id: string } }) =>
          where.id === 'job-123'
            ? { id: 'job-123', resume_id: 1, status: 'queued', resume: { user_id: 'user-1' } }
            : null,
      },
      // ranking_run 없음 → join 미충족 → queued 유지(아직 미채점)
      rankingRun: { findFirst: async () => null },
    } as unknown as PrismaService

    const controller = new ScoringJobsController(fakePrisma)

    const result = await controller.getJob('job-123', { user: { id: 'user-1' } })

    expect(result.data.job_id).toBe('job-123')
    expect(result.data.status).toBe('queued')
    expect(result.data.resume_id).toBe(1)
  })

  it('test_AC_2_done_via_ranking_run_join', async () => {
    // 저장 status는 queued이나 worker 산출물(ranking_run) 존재 → join으로 done 판정(T-045)
    const fakePrisma = {
      scoringJob: {
        findUnique: async () => ({
          id: 'job-123',
          resume_id: 1,
          status: 'queued',
          resume: { user_id: 'user-1' },
        }),
      },
      rankingRun: { findFirst: async () => ({ id: 42 }) },
    } as unknown as PrismaService

    const controller = new ScoringJobsController(fakePrisma)
    const result = await controller.getJob('job-123', { user: { id: 'user-1' } })
    expect(result.data.status).toBe('done')
  })

  it('test_AC_2_cross_user_job_returns_404', async () => {
    const fakePrisma = {
      scoringJob: {
        findUnique: async ({ where }: { where: { id: string } }) =>
          where.id === 'job-123'
            ? { id: 'job-123', resume_id: 1, status: 'done', resume: { user_id: 'owner-user' } }
            : null,
      },
    } as unknown as PrismaService

    const controller = new ScoringJobsController(fakePrisma)

    let caught: HttpException | undefined
    try {
      await controller.getJob('job-123', { user: { id: 'attacker-user' } })
    } catch (e) {
      caught = e as HttpException
    }
    expect(caught).toBeInstanceOf(HttpException)
    expect(caught?.getStatus()).toBe(404)
  })

  it('test_AC_2_missing_job_returns_404', async () => {
    const fakePrisma = {
      scoringJob: {
        findUnique: async () => null,
      },
    } as unknown as PrismaService

    const controller = new ScoringJobsController(fakePrisma)

    let caught: HttpException | undefined
    try {
      await controller.getJob('nonexistent', { user: { id: 'user-1' } })
    } catch (e) {
      caught = e as HttpException
    }
    expect(caught).toBeInstanceOf(HttpException)
    expect(caught?.getStatus()).toBe(404)
  })
})
