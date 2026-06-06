import { Module } from '@nestjs/common'
import { CoverageModule } from './coverage/coverage.module'
import { FeedModule } from './feed/feed.module'
import { HealthController } from './health.controller'
import { ResumesModule } from './resumes/resumes.module'

@Module({
  imports: [FeedModule, CoverageModule, ResumesModule],
  controllers: [HealthController],
})
export class AppModule {}
