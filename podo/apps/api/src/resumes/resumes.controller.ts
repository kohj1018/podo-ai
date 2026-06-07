import {
  Body,
  Controller,
  HttpCode,
  HttpException,
  HttpStatus,
  Param,
  Post,
  Req,
  UploadedFile,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common'
import { FileInterceptor } from '@nestjs/platform-express'
import { SessionGuard } from '../auth/session.guard'
import { CreateResumeDto } from './dto/create-resume.dto'
import { type CreateResumeResult, ResumesService, type ScoreResult } from './resumes.service'

// FileInterceptor가 주입하는 multer 파일의 최소 형태(@types/multer 의존 회피).
interface UploadedResumeFile {
  originalname: string
  buffer: Buffer
  size: number
}

interface AuthedRequest {
  user?: { id: string }
}

const MAX_BYTES = 100 * 1024 // 100KB

@Controller()
@UseGuards(SessionGuard)
export class ResumesController {
  constructor(private readonly resumes: ResumesService) {}

  // POST /api/v1/resumes — 파일(.txt/.md, multipart) 또는 paste(json) 업로드.
  // 마스킹은 ResumesService 내부(raw→마스킹본). 컨트롤러는 포맷·크기 경계만 검증한다.
  @Post('api/v1/resumes')
  @UseInterceptors(FileInterceptor('file'))
  async create(
    @UploadedFile() file: UploadedResumeFile | undefined,
    @Body() body: CreateResumeDto,
    @Req() req?: AuthedRequest,
  ): Promise<{ data: CreateResumeResult }> {
    let raw: string
    let source: string
    let format: string

    if (file) {
      const name = file.originalname ?? ''
      const dot = name.lastIndexOf('.')
      const ext = dot >= 0 ? name.slice(dot).toLowerCase() : ''
      if (ext !== '.txt' && ext !== '.md') {
        throw new HttpException(
          {
            code: 'RESUME_FORMAT_NOT_SUPPORTED',
            message: '.txt / .md 파일 또는 텍스트 붙여넣기만 지원합니다.',
          },
          HttpStatus.UNSUPPORTED_MEDIA_TYPE, // 415
        )
      }
      if (file.size > MAX_BYTES || file.buffer.length > MAX_BYTES) {
        throw new HttpException(
          { code: 'RESUME_TOO_LARGE', message: '이력서가 너무 큽니다(최대 100KB).' },
          HttpStatus.PAYLOAD_TOO_LARGE, // 413
        )
      }
      raw = file.buffer.toString('utf8')
      source = 'upload'
      format = ext === '.md' ? 'md' : 'txt'
    } else {
      raw = body?.text ?? ''
      if (Buffer.byteLength(raw, 'utf8') > MAX_BYTES) {
        throw new HttpException(
          { code: 'RESUME_TOO_LARGE', message: '이력서가 너무 큽니다(최대 100KB).' },
          HttpStatus.PAYLOAD_TOO_LARGE, // 413
        )
      }
      source = 'paste'
      format = 'paste'
    }

    const result = await this.resumes.create({ raw, source, format }, req?.user?.id)
    return { data: result }
  }

  // POST /api/v1/resumes/:id/score — 채점 작업을 SQS에 enqueue하고 즉시 202 반환(블로킹 X, ADR-106).
  // 소유권 인가는 ResumesService.score(타인 이력서 채점 시 403 — T-042 데이터 격리).
  @Post('api/v1/resumes/:id/score')
  @HttpCode(HttpStatus.ACCEPTED) // 202 — 작업 수락(비동기 큐 트리거)
  async score(@Param('id') id: string, @Req() req?: AuthedRequest): Promise<{ data: ScoreResult }> {
    const resumeId = Number.parseInt(id, 10)
    if (!Number.isInteger(resumeId) || resumeId <= 0) {
      throw new HttpException(
        { code: 'RESUME_NOT_FOUND', message: '잘못된 이력서 id.' },
        HttpStatus.NOT_FOUND, // 404
      )
    }
    const result = await this.resumes.score(resumeId, req?.user?.id)
    return { data: result }
  }
}
