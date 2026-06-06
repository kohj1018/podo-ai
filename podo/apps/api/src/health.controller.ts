import { Controller, Get } from '@nestjs/common'

// AC-1: GET /api/v1/health → { status: 'ok' } (ARCH §7-1 경로 /api/v1).
@Controller()
export class HealthController {
  @Get('api/v1/health')
  check(): { status: string } {
    return { status: 'ok' }
  }
}
