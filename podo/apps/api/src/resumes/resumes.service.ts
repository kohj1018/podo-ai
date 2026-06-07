import { HttpException, HttpStatus, Injectable } from '@nestjs/common'
import { PrismaService } from '../prisma/prisma.service'
import { type EvidenceSummary, summarizeEvidence } from './evidence-summary'
import { ResumeMasker } from './resume-masker.port'
import { WorkerRunner } from './worker-runner.port'

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

export interface ScoreResult {
  resume_id: number
  status: 'scored'
}

// resumes는 api 소유(§3-2) → write 허용(feed/coverage의 read-only 제약과 별개).
@Injectable()
export class ResumesService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly masker: ResumeMasker,
    private readonly workerRunner: WorkerRunner,
  ) {}

  // raw → 마스킹(메모리) → 마스킹본만 영속. raw는 DB·로그·예외 메시지에 절대 남기지 않는다(F-013 §8 NFR).
  // userId 주어지면 그 사용자 소유로 저장(멀티유저 격리, T-042). 미지정 시 소유자 없음(seed/하위호환).
  async create(input: CreateResumeInput, userId?: string): Promise<CreateResumeResult> {
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
        user_id: userId ?? null,
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

  // 업로드 이력서(resume_id) 스코어링 기동 — worker가 그 id로 채점·영속(ranking_runs/recommendations).
  // M3 로컬: SubprocessWorkerRunner가 `python -m worker --resume-id N`을 완주까지 실행(완료 시 200).
  // 소유권 인가(T-042): 이력서에 소유자가 있고 요청자와 다르면 403(타인 이력서 채점 불가).
  async score(resumeId: number, userId?: string): Promise<ScoreResult> {
    const resume = await this.prisma.resume.findUnique({ where: { id: resumeId } })
    if (!resume) {
      throw new HttpException(
        { code: 'RESUME_NOT_FOUND', message: '이력서를 찾을 수 없습니다.' },
        HttpStatus.NOT_FOUND,
      )
    }
    if (resume.user_id && resume.user_id !== userId) {
      throw new HttpException(
        { code: 'RESUME_FORBIDDEN', message: '해당 이력서에 접근할 수 없습니다.' },
        HttpStatus.FORBIDDEN,
      )
    }
    await this.workerRunner.run(resumeId)
    return { resume_id: resumeId, status: 'scored' }
  }
}
