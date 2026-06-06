import { Module } from '@nestjs/common'
import { FeedModule } from './feed/feed.module'
import { HealthController } from './health.controller'

@Module({
  imports: [FeedModule],
  controllers: [HealthController],
})
export class AppModule {}
