import { Module } from '@nestjs/common'
import { AuthModule } from './auth/auth.module'
import { CoverageModule } from './coverage/coverage.module'
import { FeedModule } from './feed/feed.module'
import { HealthController } from './health.controller'
import { ResumesModule } from './resumes/resumes.module'

@Module({
  imports: [AuthModule, FeedModule, CoverageModule, ResumesModule],
  controllers: [HealthController],
})
export class AppModule {}
