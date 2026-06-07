import { Controller, Get, UseGuards } from '@nestjs/common'
import { SessionGuard } from '../auth/session.guard'
import { type Coverage, CoverageService } from './coverage.service'

@Controller()
@UseGuards(SessionGuard)
export class CoverageController {
  constructor(private readonly coverage: CoverageService) {}

  // GET /api/v1/coverage — 채널별 수집 상태 + last_success_at + 미수집 채널(채널 전역 — 비격리).
  @Get('api/v1/coverage')
  async getCoverage(): Promise<Coverage> {
    return this.coverage.getCoverage()
  }
}
