import { Injectable } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'

export interface ChannelCoverage {
  name: string // source_id
  tier: string | null
  status: string // active/blocked/captcha/login-required/no-korea-jobs/unsupported
  last_success_at: Date | null
}

export interface Coverage {
  channels: ChannelCoverage[]
  uncollected: string[]
  degraded: boolean // active 아닌 소스 존재 → "전부 수집" 거짓 인상 차단(Fail #3)
  lastCrawlAt: Date | null // 가장 최근 crawl_runs run_at(일일 cron 마지막 실행 시각). 런 없으면 null.
  lastCrawlSuccess: boolean | null // 그 run_at 배치 전 채널 성공이면 true, 실패 채널 있으면 false, 런 없으면 null.
}

@Injectable()
export class CoverageService {
  constructor(private readonly prisma: PrismaService) {}

  // source_crawl_status(소스별 현재 스냅샷)에서 커버리지 파생(read-only — crawler 단일 writer).
  // crawl_runs(런 히스토리)와 역할 분리: 전 tier 소스 + 정적 status(login-required/no-korea-jobs/
  // unsupported 포함)를 그대로 투명 노출한다(KNOWN_CHANNELS 하드코딩 제거 — T-063).
  async getCoverage(): Promise<Coverage> {
    const rows = await this.prisma.sourceCrawlStatus.findMany({
      orderBy: [{ tier: 'asc' }, { source_id: 'asc' }],
      select: { source_id: true, tier: true, status: true, last_success_at: true },
    })

    const channels: ChannelCoverage[] = rows.map((r) => ({
      name: r.source_id,
      tier: r.tier,
      status: r.status,
      last_success_at: r.last_success_at,
    }))

    // 미수집 = status가 active가 아닌 모든 소스(차단/로그인/미지원/한국공고없음 — 투명 노출).
    const uncollected = channels.filter((c) => c.status !== 'active').map((c) => c.name)
    const degraded = uncollected.length > 0

    // crawl_runs(런 히스토리)에서 마지막 크롤 실행 시각·성공 여부 파생(T-085 AC-3, Fail #3 가시화).
    // 한 번의 크롤 = 동일 run_at의 채널별 행 다수 → 성공 = 그 run_at 배치에 비-success 채널 0건.
    const lastRun = await this.prisma.crawlRun.findFirst({
      orderBy: { run_at: 'desc' },
      select: { run_at: true },
    })
    let lastCrawlAt: Date | null = null
    let lastCrawlSuccess: boolean | null = null
    if (lastRun) {
      lastCrawlAt = lastRun.run_at
      const failedInBatch = await this.prisma.crawlRun.count({
        where: { run_at: lastRun.run_at, status: { not: 'success' } },
      })
      lastCrawlSuccess = failedInBatch === 0
    }

    return { channels, uncollected, degraded, lastCrawlAt, lastCrawlSuccess }
  }
}
