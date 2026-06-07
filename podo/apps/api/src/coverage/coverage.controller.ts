import { Controller, Get, UseGuards } from '@nestjs/common'
import { SessionGuard } from '../auth/session.guard'
import { type Coverage, CoverageService } from './coverage.service'

@Controller()
@UseGuards(SessionGuard)
export class CoverageController {
  constructor(private readonly coverage: CoverageService) {}

  // GET /api/v1/coverage — 소스별 수집 status(tier 포함) + last_success_at + 미수집 소스.
  // source_crawl_status 기반(전 tier 소스·정적 status 투명 노출 — T-063).
  @Get('api/v1/coverage')
  async getCoverage(): Promise<Coverage> {
    return this.coverage.getCoverage()
  }
}
