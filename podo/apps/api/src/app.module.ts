import { Module } from '@nestjs/common'
import { ApplicationsModule } from './applications/applications.module'
import { AuthModule } from './auth/auth.module'
import { CoverageModule } from './coverage/coverage.module'
import { FeedModule } from './feed/feed.module'
import { HealthController } from './health.controller'
import { ResumesModule } from './resumes/resumes.module'
import { ScoringJobsModule } from './scoring-jobs/scoring-jobs.module'

@Module({
  imports: [
    AuthModule,
    FeedModule,
    CoverageModule,
    ResumesModule,
    ScoringJobsModule,
    ApplicationsModule,
  ],
  controllers: [HealthController],
})
export class AppModule {}
