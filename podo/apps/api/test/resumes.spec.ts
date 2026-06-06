import 'reflect-metadata'
import { HttpException } from '@nestjs/common'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { PrismaService } from '../src/prisma/prisma.service'
import { RegexResumeMaskerStub } from '../src/resumes/resume-masker.port'
import { ResumesController } from '../src/resumes/resumes.controller'
import { ResumesService } from '../src/resumes/resumes.service'

const hasDb = Boolean(process.env.DATABASE_URL)

interface UploadedResumeFile {
  originalname: string
  buffer: Buffer
  size: number
}
function asFile(content: string, name: string): UploadedResumeFile {
  const buffer = Buffer.from(content, 'utf8')
  return { originalname: name, buffer, size: buffer.length }
}

// AC-1 — 유효 업로드 → 마스킹본 저장 + 응답(masked_preview·evidence_summary) + raw 미저장(DB 주입 시).
describe.skipIf(!hasDb)('ResumesService 업로드 (DB)', () => {
  let prisma: PrismaService
  let service: ResumesService
  const ids: number[] = []

  beforeAll(async () => {
    prisma = new PrismaService()
    await prisma.$connect()
    service = new ResumesService(prisma, new RegexResumeMaskerStub())
  })
  afterAll(async () => {
    if (ids.length) await prisma.resume.deleteMany({ where: { id: { in: ids } } })
    await prisma.$disconnect()
  })

  it('test_AC_1_valid_upload_persists_masked_no_raw', async () => {
    const raw = [
      '홍길동 이력서',
      '이메일: hong@example.com',
      '## Skills',
      '- Python, TypeScript',
      '- React, Next.js',
      '## 경력',
      '- A사 백엔드 엔지니어 2년',
    ].join('\n')

    const result = await service.create({ raw, source: 'paste', format: 'paste' })
    ids.push(result.resume_id)

    expect(result.masked).toBe(true)
    expect(result.masked_preview).toContain('[MASKED_EMAIL]')
    expect(result.masked_preview).not.toContain('hong@example.com')
    expect(result.placeholders).toBeGreaterThanOrEqual(1)
    expect(result.evidence_summary.skills).toBe(2)
    expect(result.evidence_summary.experiences).toBe(1)

    // DB에는 마스킹본만 — raw 이메일 미저장
    const row = await prisma.resume.findUnique({ where: { id: result.resume_id } })
    expect(row?.content).toContain('[MASKED_EMAIL]')
    expect(row?.content).not.toContain('hong@example.com')
    expect(row?.masked).toBe(true)
    expect(row?.source).toBe('paste')
    expect(row?.upload_format).toBe('paste')
  })
})

// AC-2 / AC-3 — 컨트롤러 포맷·크기 경계가 도메인 code envelope로 거절(service 미도달).
describe('ResumesController 포맷·크기 경계', () => {
  const controller = new ResumesController({
    create: async () => {
      throw new Error('service should not be reached')
    },
  } as unknown as ResumesService)

  it('test_AC_2_pdf_rejected_415_envelope', async () => {
    const pdf = asFile('%PDF-1.4 fake', 'resume.pdf')
    let caught: HttpException | undefined
    try {
      await controller.create(pdf, {})
    } catch (e) {
      caught = e as HttpException
    }
    expect(caught).toBeInstanceOf(HttpException)
    expect(caught?.getStatus()).toBe(415)
    expect((caught?.getResponse() as { code: string }).code).toBe('RESUME_FORMAT_NOT_SUPPORTED')
  })

  it('test_AC_3_oversize_rejected_413_envelope', async () => {
    const big = 'a'.repeat(100 * 1024 + 1)
    let caught: HttpException | undefined
    try {
      await controller.create(undefined, { text: big })
    } catch (e) {
      caught = e as HttpException
    }
    expect(caught).toBeInstanceOf(HttpException)
    expect(caught?.getStatus()).toBe(413)
    expect((caught?.getResponse() as { code: string }).code).toBe('RESUME_TOO_LARGE')
  })
})
