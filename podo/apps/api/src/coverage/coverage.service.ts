import { Injectable } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'

// 알려진 수집 채널(Charter §5 — 토스·당근). 미수집 표시는 이 목록 대비로 파생.
const KNOWN_CHANNELS = ['toss', 'daangn'] as const

export interface ChannelCoverage {
  name: string
  status: string | null // 최신 run status (수집 0이면 null)
  last_success_at: Date | null // MAX(run_at WHERE status='success')
}

export interface Coverage {
  channels: ChannelCoverage[]
  uncollected: string[]
  degraded: boolean // 수집 실패/미수집 존재 → "전부 수집" 거짓 인상 차단(Fail #3, T-046 AC-2)
}

@Injectable()
export class CoverageService {
  constructor(private readonly prisma: PrismaService) {}

  // crawl_runs(run별 1행)에서 채널별 최신 status + last_success_at 파생(read-only).
  async getCoverage(): Promise<Coverage> {
    const channels: ChannelCoverage[] = []
    const uncollected: string[] = []

    for (const name of KNOWN_CHANNELS) {
      const latest = await this.prisma.crawlRun.findFirst({
        where: { channel: name },
        orderBy: { run_at: 'desc' },
        select: { status: true },
      })
      const lastSuccess = await this.prisma.crawlRun.findFirst({
        where: { channel: name, status: 'success' },
        orderBy: { run_at: 'desc' },
        select: { run_at: true },
      })

      if (!latest) {
        uncollected.push(name)
        channels.push({ name, status: null, last_success_at: null })
      } else {
        channels.push({
          name,
          status: latest.status,
          last_success_at: lastSuccess?.run_at ?? null,
        })
      }
    }

    // degraded = 미수집 채널 존재 또는 최신 run이 success가 아닌 채널 존재(수집 실패 노출).
    const degraded =
      uncollected.length > 0 ||
      channels.some((c) => c.status !== null && c.status !== 'success')

    return { channels, uncollected, degraded }
  }
}
