import { Module } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'
import { RegexResumeMasker, ResumeMasker } from './resume-masker.port'
import { ResumesController } from './resumes.controller'
import { ResumesService } from './resumes.service'
import { SubprocessWorkerRunner, WorkerRunner } from './worker-runner.port'

@Module({
  controllers: [ResumesController],
  providers: [
    ResumesService,
    PrismaService,
    { provide: ResumeMasker, useClass: RegexResumeMasker },
    { provide: WorkerRunner, useClass: SubprocessWorkerRunner },
  ],
})
export class ResumesModule {}
