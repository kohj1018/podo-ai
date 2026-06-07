import { Module } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'
import { QueueModule } from '../queue/queue.module'
import { RegexResumeMasker, ResumeMasker } from './resume-masker.port'
import { ResumesController } from './resumes.controller'
import { ResumesService } from './resumes.service'

@Module({
  imports: [QueueModule],
  controllers: [ResumesController],
  providers: [
    ResumesService,
    PrismaService,
    { provide: ResumeMasker, useClass: RegexResumeMasker },
  ],
})
export class ResumesModule {}
