import { Module } from '@nestjs/common'
import { CoverageModule } from './coverage/coverage.module'
import { FeedModule } from './feed/feed.module'
import { HealthController } from './health.controller'

@Module({
  imports: [FeedModule, CoverageModule],
  controllers: [HealthController],
})
export class AppModule {}
