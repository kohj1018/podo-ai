import { Controller, Get, HttpException, HttpStatus, Param, Req, UseGuards } from '@nestjs/common'
import { SessionGuard } from '../auth/session.guard'
import { PrismaService } from '../prisma/prisma.service'

interface AuthedRequest {
  user?: { id: string }
}

export interface ScoringJobResponse {
  job_id: string
  status: string
  resume_id: number
}

// GET /api/v1/scoring-jobs/:id — 채점 작업 상태 폴링(T-044 AC-2).
// 타 사용자 job 조회 시 404(횡단 접근 차단 — resume.user_id 비교).
@Controller('api/v1/scoring-jobs')
@UseGuards(SessionGuard)
export class ScoringJobsController {
  constructor(private readonly prisma: PrismaService) {}

  @Get(':id')
  async getJob(
    @Param('id') id: string,
    @Req() req?: AuthedRequest,
  ): Promise<{ data: ScoringJobResponse }> {
    const job = await this.prisma.scoringJob.findUnique({
      where: { id },
      include: { resume: { select: { user_id: true } } },
    })

    // 존재하지 않거나 타 사용자 소유 이력서의 job: 404(정보 노출 방지).
    if (!job || job.resume.user_id !== req?.user?.id) {
      throw new HttpException(
        { code: 'SCORING_JOB_NOT_FOUND', message: '채점 작업을 찾을 수 없습니다.' },
        HttpStatus.NOT_FOUND,
      )
    }

    // done 판정 = worker 산출물(ranking_run) 존재 기반 join (ADR-006 단순성, T-045 §8).
    // worker는 scoring_jobs에 직접 write 못 함(ARCH §3-2 단일 writer)이므로, 미종료 작업은
    // 해당 이력서의 ranking_run 존재로 done을 판정한다. (running/failed 상태 큐 신호의 api
    // 반영은 후속 — worker는 scoring-status-queue로 신호 emit, 본 task는 done join까지.)
    let status = job.status
    if (status !== 'done' && status !== 'failed') {
      const run = await this.prisma.rankingRun.findFirst({
        where: { resume_id: job.resume_id },
        select: { id: true },
      })
      if (run) {
        status = 'done'
      }
    }

    return {
      data: {
        job_id: job.id,
        status,
        resume_id: job.resume_id,
      },
    }
  }
}
