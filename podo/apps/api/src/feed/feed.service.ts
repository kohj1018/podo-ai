import { Injectable } from '@nestjs/common'
// NestJS DI: value import 필수(import type은 emitDecoratorMetadata에서 erase → DI 실패).
import { PrismaService } from '../prisma/prisma.service'

export interface FeedItem {
  posting: unknown
  fit_level: number | null
  rank_position: number
  status: string
  // ranking_runs.result — opaque evidence. 파싱·분기 금지(§3-2 규칙3 / ARCH §7-1).
  evidence: unknown
}

export interface FeedPage {
  items: FeedItem[]
  nextCursor: number | null
}

@Injectable()
export class FeedService {
  constructor(private readonly prisma: PrismaService) {}

  // worker 산출 recommendations를 current run 한정 + rank_position 커서로 서빙(read-only).
  // userId 주어지면 그 사용자 이력서의 run으로 범위 격리(멀티유저, T-042). 미지정 시 전역(하위호환).
  async getFeed(cursor: number, userId?: string, take = 20): Promise<FeedPage> {
    // (a) current run = (해당 사용자) 최신 ranking_runs (run 간 stale 혼입 차단 — cross-LLM P1)
    const currentRun = await this.prisma.rankingRun.findFirst({
      where: userId ? { resume: { user_id: userId } } : undefined,
      // 동일 ms 두 run insert 시 tie 비결정 방지 — id desc 보조 정렬(QA-M2-006).
      orderBy: [{ created_at: 'desc' }, { id: 'desc' }],
      select: { id: true },
    })
    if (!currentRun) {
      return { items: [], nextCursor: null }
    }

    // (b) current run 한정 + rank_position > cursor 오름차순. held(fit_level null) 포함.
    const recs = await this.prisma.recommendation.findMany({
      where: { run_id: currentRun.id, rank_position: { gt: cursor } },
      orderBy: { rank_position: 'asc' },
      take,
      include: { job_posting: true, run: { select: { result: true } } },
    })

    const seen = new Set<number>()
    const items: FeedItem[] = []
    for (const r of recs) {
      // 방어적 dedup — 불변식은 recommendations @@unique([run_id, job_posting_id])가 DB 보장(QA-M2-002).
      if (seen.has(r.job_posting_id)) continue
      seen.add(r.job_posting_id)
      items.push({
        posting: r.job_posting,
        fit_level: r.fit_level,
        rank_position: r.rank_position,
        status: r.status,
        evidence: r.run.result, // opaque pass-through (파싱 X)
      })
    }

    const nextCursor = recs.length === take ? recs[recs.length - 1].rank_position : null
    return { items, nextCursor }
  }
}
