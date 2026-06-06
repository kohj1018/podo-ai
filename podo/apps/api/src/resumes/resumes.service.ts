import { HttpException, HttpStatus, Injectable } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'
import { type EvidenceSummary, summarizeEvidence } from './evidence-summary'
import { ResumeMasker } from './resume-masker.port'

export interface CreateResumeInput {
  raw: string
  source: string // upload | paste
  format: string // txt | md | paste
}

export interface CreateResumeResult {
  resume_id: number
  masked: true
  masked_preview: string // 마스킹본 텍스트(이미 직접식별자 치환됨 — raw 아님)
  placeholders: number
  evidence_summary: EvidenceSummary
}

// resumes는 api 소유(§3-2) → write 허용(feed/coverage의 read-only 제약과 별개).
@Injectable()
export class ResumesService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly masker: ResumeMasker,
  ) {}

  // raw → 마스킹(메모리) → 마스킹본만 영속. raw는 DB·로그·예외 메시지에 절대 남기지 않는다(F-013 §8 NFR).
  async create(input: CreateResumeInput): Promise<CreateResumeResult> {
    if (!input.raw || input.raw.trim().length === 0) {
      throw new HttpException(
        { code: 'RESUME_EMPTY', message: '이력서 내용이 비어 있습니다.' },
        HttpStatus.BAD_REQUEST,
      )
    }
    const { masked, placeholders } = this.masker.mask(input.raw)
    const evidence = summarizeEvidence(masked)
    const row = await this.prisma.resume.create({
      data: {
        content: masked, // 마스킹본 전용 — raw 미저장(M3 안전 불변식)
        masked: true,
        source: input.source,
        upload_format: input.format,
      },
    })
    return {
      resume_id: row.id,
      masked: true,
      masked_preview: masked,
      placeholders,
      evidence_summary: evidence,
    }
  }
}
