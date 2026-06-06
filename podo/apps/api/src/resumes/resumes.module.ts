import { Module } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'
import { RegexResumeMaskerStub, ResumeMasker } from './resume-masker.port'
import { ResumesController } from './resumes.controller'
import { ResumesService } from './resumes.service'

@Module({
  controllers: [ResumesController],
  providers: [
    ResumesService,
    PrismaService,
    // T-036이 RegexResumeMasker(전체 구현)로 교체.
    { provide: ResumeMasker, useClass: RegexResumeMaskerStub },
  ],
})
export class ResumesModule {}
