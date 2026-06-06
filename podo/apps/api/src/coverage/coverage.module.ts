import { Module } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'
import { CoverageController } from './coverage.controller'
import { CoverageService } from './coverage.service'

// error envelope(AllExceptionsFilter)는 FeedModule의 APP_FILTER가 전역 적용 — 재등록 불필요.
@Module({
  controllers: [CoverageController],
  providers: [CoverageService, PrismaService],
})
export class CoverageModule {}
