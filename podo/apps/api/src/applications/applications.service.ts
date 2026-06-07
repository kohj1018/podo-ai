import { ForbiddenException, Injectable } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'

export type ApplicationAction = 'applied' | 'skipped' | 'favorite' | 'unfavorite' | 'unskip'

// 처리완료 정리에서 기본 피드에서 빠지는 action(applied/skipped). 즐겨찾기·되돌리기는 유지.
export const CLEARED_ACTIONS: ApplicationAction[] = ['applied', 'skipped']

export interface ApplicationEventRow {
  id: number
  user_id: string
  job_posting_id: number
  action: string
  created_at: Date
}

// 지원/스킵·즐겨찾기 이벤트 기록(api 소유, ARCH §3-2). 사용자 격리 — 본인 기록만(F-016).
@Injectable()
export class ApplicationsService {
  constructor(private readonly prisma: PrismaService) {}

  // 멱등 기록: 동일 (user, job)은 최신 action으로 upsert(이벤트 로그 1행 — F-019 §12).
  async recordAction(
    userId: string,
    jobPostingId: number,
    action: ApplicationAction,
  ): Promise<ApplicationEventRow> {
    return this.prisma.applicationEvent.upsert({
      where: {
        user_id_job_posting_id: { user_id: userId, job_posting_id: jobPostingId },
      },
      update: { action },
      create: { user_id: userId, job_posting_id: jobPostingId, action },
    })
  }

  // 본인 기록만 조회(filter 지정 시 해당 action만 — 예: favorite).
  async getActions(userId: string, filter?: ApplicationAction): Promise<ApplicationEventRow[]> {
    return this.prisma.applicationEvent.findMany({
      where: { user_id: userId, ...(filter ? { action: filter } : {}) },
      orderBy: { created_at: 'desc' },
    })
  }

  // 본인 기록만 삭제 — 타인 기록 삭제 시도는 403(횡단 접근 차단, F-016 정합).
  async deleteAction(userId: string, eventId: number): Promise<void> {
    const ev = await this.prisma.applicationEvent.findUnique({ where: { id: eventId } })
    if (!ev || ev.user_id !== userId) {
      throw new ForbiddenException({
        code: 'APPLICATION_FORBIDDEN',
        message: '해당 기록에 접근할 수 없습니다.',
      })
    }
    await this.prisma.applicationEvent.delete({ where: { id: eventId } })
  }
}
