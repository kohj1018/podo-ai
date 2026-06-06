import { Module } from '@nestjs/common'
import { APP_FILTER } from '@nestjs/core'
import { AllExceptionsFilter } from '../common/error.filter'
import { PrismaService } from '../prisma/prisma.service'
import { FeedController } from './feed.controller'
import { FeedService } from './feed.service'

@Module({
  controllers: [FeedController],
  providers: [FeedService, PrismaService, { provide: APP_FILTER, useClass: AllExceptionsFilter }],
})
export class FeedModule {}
