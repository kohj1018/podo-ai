import { Module } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'
import { ScoringJobsController } from './scoring-jobs.controller'

@Module({
  controllers: [ScoringJobsController],
  providers: [PrismaService],
})
export class ScoringJobsModule {}
