import { Controller, Get } from '@nestjs/common'
import { type Coverage, CoverageService } from './coverage.service'

@Controller()
export class CoverageController {
  constructor(private readonly coverage: CoverageService) {}

  // GET /api/v1/coverage — 채널별 수집 상태 + last_success_at + 미수집 채널.
  @Get('api/v1/coverage')
  async getCoverage(): Promise<Coverage> {
    return this.coverage.getCoverage()
  }
}
