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

    return { channels, uncollected }
  }
}
