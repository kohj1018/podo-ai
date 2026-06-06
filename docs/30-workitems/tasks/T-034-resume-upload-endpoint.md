# T-034-resume-upload-endpoint

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
NestJS `POST /api/v1/resumes`를 신설해 단일 사용자가 이력서(`.txt`/`.md` 파일 또는 paste 텍스트)를 업로드하면, **동일 요청 흐름 내에서 마스킹(F-014/T-036 인터페이스 호출) 후 마스킹본만** `resumes`에 영속하는 경로를 만든다. raw PII는 DB·로그에 남기지 않는다(F-013 §1, M3 안전 불변식). 본 task는 마스킹 **인터페이스(port)를 정의**하고 최소 stub으로 동작시키며, 실제 regex 마스킹 구현은 T-036이 채운다(F-013 §10).

## 2. 작업 범위
- NestJS `ResumesModule`: `ResumesController`(POST `/api/v1/resumes`) + `ResumesService` + `CreateResumeDto` + 마스킹 port 인터페이스 + 최소 stub.
- 입력: `multipart/form-data`(파일) + `application/json`(paste) 양쪽. 포맷 허용목록 `.txt`/`.md`/plain text, 크기 ≤100KB.
- 에러 envelope `{ error: { code, message } }`(ARCH §7-1): RESUME_FORMAT_NOT_SUPPORTED(415)·RESUME_TOO_LARGE(413)·RESUME_EMPTY(400).
- `app.module.ts` 배선 + `main.ts` 전역 `ValidationPipe` 도입.

## 3. 구현 항목
1. 의존성 설치 — 현재: `@nestjs/platform-express`(Multer FileInterceptor) 미확인 → 변경: `pnpm --filter @podo/api add @nestjs/platform-express`(용도: multipart 파일 수신). 이미 transitive로 있으면 명시 의존으로 승격. → 확인: `FileInterceptor` import 가능. (AC-1) (lockfile 변경 → §9 단독 wave)
2. `podo/apps/api/src/resumes/resume-masker.port.ts` — 현재: 없음 → 변경: 마스킹 경계 인터페이스 정의:
   ```ts
   export interface MaskResult { masked: string; placeholders: number }
   export abstract class ResumeMasker { abstract mask(raw: string): MaskResult }
   ```
   + 최소 stub `RegexResumeMaskerStub`(이메일만 `[MASKED_EMAIL]` 치환 — T-036이 전체 패턴으로 교체). → 확인: stub이 이메일 1건 치환. (AC-1)
3. `podo/apps/api/src/resumes/dto/create-resume.dto.ts` — 현재: 없음 → 변경: `class CreateResumeDto { @IsString() @IsOptional() text?: string }`(paste 경로) + class-validator 데코레이터. 파일 경로는 컨트롤러에서 Multer 버퍼 검증. → 확인: 빈 입력 → 검증 실패. (AC-1)
4. `podo/apps/api/src/resumes/resumes.service.ts` — 현재: 없음 → 변경: `create({ raw, source, format })`: (a) raw 빈값 → `RESUME_EMPTY`(400); (b) `ResumeMasker.mask(raw)` 호출 → `masked`; (c) `prisma.resume.create({ data: { content: masked, masked: true, source, upload_format: format } })`(resumes는 api 소유 — write 허용, §3-2); (d) **결정적 evidence 요약** — `parse_resume.extract_skills_evidence`의 비-LLM 헤딩 파싱을 경량 TS로 이식(스킬 불릿 수=skills, 경력 항목 수=experiences); (e) 반환 `{ resume_id, masked: true, masked_preview: masked, placeholders, evidence_summary: { skills, experiences } }`(F-015 preview 계약 — repair-plan P0). **raw를 로그·예외 메시지에 절대 출력 안 함**(F-013 §8 NFR). → 확인: `test_AC_1`이 마스킹본 저장 + masked_preview/evidence_summary 응답 + raw 미저장. (AC-1)
5. `podo/apps/api/src/resumes/resumes.controller.ts` — 현재: 없음 → 변경: `@Post('api/v1/resumes')` + `@UseInterceptors(FileInterceptor('file'))`. 파일 있으면 buffer→utf8 + 확장자 검증(`.txt`/`.md`만, 그 외 415 `RESUME_FORMAT_NOT_SUPPORTED`), 없으면 body.text(paste). 크기 >100KB → 413 `RESUME_TOO_LARGE`. coverage.controller.ts의 `@Controller()` + `@Get('api/v1/...')` 패턴 동일. → 확인: PDF→415·초과→413. (AC-2, AC-3)
6. `podo/apps/api/src/resumes/resumes.module.ts` — `ResumesController` + `ResumesService` + `{ provide: ResumeMasker, useClass: RegexResumeMaskerStub }` + `PrismaService`. → 확인: 모듈 부팅. (AC-1)
7. `podo/apps/api/src/app.module.ts:7` — 현재: `imports: [FeedModule, CoverageModule]` → 변경: `ResumesModule` 추가. (AC-1)
8. `podo/apps/api/src/main.ts:6` + `podo/apps/api/src/common/error.filter.ts:21` — 현재: 전역 ValidationPipe 없음 + `AllExceptionsFilter`가 `code = HttpStatus[status]`만 emit(413→`PAYLOAD_TOO_LARGE`, 415→`UNSUPPORTED_MEDIA_TYPE` — 도메인 code 불가) → 변경: (a) `app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }))` + `AllExceptionsFilter` 전역 적용 보장; (b) filter가 예외 response 객체의 `code` 필드 우선 사용(`const r = exception.getResponse(); code = (typeof r === 'object' && r?.code) ?? HttpStatus[status]`); (c) 컨트롤러가 `throw new HttpException({ code: 'RESUME_TOO_LARGE', message }, 413)` 식 도메인 code 주입. → 확인: 초과/PDF/빈입력이 `{ error: { code: "RESUME_*", message } }`로 직렬화. (AC-2, AC-3) (repair-plan P1-ambiguity)

## 4. 제외 항목
- 실제 PII 마스킹 regex 구현(T-036 — 본 task는 port + 이메일 stub만). · `parse_resume` 스코어링 연결(T-037). · 업로드 UI(T-038). · PDF/docx 텍스트 추출(M4). · 인증·멀티유저. · 단일 활성 이력서 교체 정책 구체화(아래 §12 열린 질문).

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/src/resumes/resume-masker.port.ts` (신규) — ResumeMasker port + RegexResumeMaskerStub(이메일만, T-036 교체 대상)
- `podo/apps/api/src/resumes/dto/create-resume.dto.ts` (신규) — paste 바디 DTO(plain — class-validator 미설치, manual validation)
- `podo/apps/api/src/resumes/evidence-summary.ts` (신규) — parse_resume 비-LLM 헤딩 파싱 경량 이식(skills/experiences 카운트)
- `podo/apps/api/src/resumes/resumes.service.ts` (신규) — 마스킹→마스킹본 영속(RESUME_EMPTY 검증, raw 미로깅)
- `podo/apps/api/src/resumes/resumes.controller.ts` (신규) — POST /api/v1/resumes(multipart+paste), 포맷/크기 도메인 envelope
- `podo/apps/api/src/resumes/resumes.module.ts` (신규) — 모듈 배선 + masker provider
- `podo/apps/api/src/app.module.ts` — ResumesModule 등록
- `podo/apps/api/src/main.ts` — AllExceptionsFilter 전역 등록(envelope 보장)
- `podo/apps/api/src/common/error.filter.ts` — 예외 response의 도메인 code 우선 사용
- `podo/apps/api/test/resumes.spec.ts` (신규) — AC-1(DB)·AC-2(415)·AC-3(413)

## 5. 완료 조건
`POST /api/v1/resumes`가 `.txt`/`.md`/paste를 받아 마스킹본을 `resumes`에 저장하고 201 + `{ data: { resume_id, masked } }`를 반환하며, 금지 포맷·초과 크기·빈 입력을 envelope 에러로 거절한다.

## 6. Acceptance Criteria
- AC-1 [Given] 유효한 `.txt` 텍스트(또는 paste) [When] `POST /api/v1/resumes` [Then] 201 + `{ data: { resume_id, masked: true, masked_preview, placeholders, evidence_summary } }`를 반환하고 `resumes.content`에 **마스킹 port를 거친 본문**이 저장된다(`masked=true`·`source`·`upload_format` 기록). 전체 직접식별자 no-raw(6표면) 검증은 **T-040 PII Safety Pass**가 담당(본 task stub은 이메일만 — 전체 PII는 T-036).
- AC-2 [Given] PDF(또는 비허용 포맷) 업로드 [When] `POST /api/v1/resumes` [Then] 415 + `{ error: { code: "RESUME_FORMAT_NOT_SUPPORTED" } }`를 반환한다.
- AC-3 [Given] 100KB 초과 텍스트 [When] `POST /api/v1/resumes` [Then] 413 + `{ error: { code: "RESUME_TOO_LARGE" } }`를 반환한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/api/test/resumes.spec.ts::test_AC_1_valid_upload_persists_masked_no_raw
- AC-2 → vitest::podo/apps/api/test/resumes.spec.ts::test_AC_2_pdf_rejected_415_envelope
- AC-3 → vitest::podo/apps/api/test/resumes.spec.ts::test_AC_3_oversize_rejected_413_envelope

## 6-2. TDD opt-out
<!-- TDD 적용 — T-026 패턴: ResumesService를 실 PrismaService로 직접 인스턴스화(AC-1, DB 주입 시), DTO/포맷/크기 검증·error envelope는 filter/pipe 직접 호출 검증(풀 Nest 부트 불요 — vitest/esbuild emitDecoratorMetadata 제약 회피). -->

## 7. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md)
- Feature: [F-013-resume-upload-api](../features/F-013-resume-upload-api.md)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) (경로·envelope·에러코드), [## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md), ADR-105(마스킹 경계 — T-036 신설)

## 8. 메모
- 해석 확정: 마스킹은 **NestJS 경계에서 수행**(raw가 `resumes.content` DB write 전 메모리 마스킹돼야 함 — F-014 §12 작업가정 정합). 본 task는 `ResumeMasker` port + 이메일 stub만; T-036이 전체 regex 구현으로 stub 교체. **최종 마스킹 런타임 위치는 ADR-105가 확정**(NestJS TS vs ai/core) — port 추상화라 위치 바뀌어도 컨트롤러/서비스 영향 최소.
- 해석 확정: `resumes`는 api 소유(§3-2) → ResumesService의 resume write 허용(feed/coverage의 read-only 제약과 별개).
- 응답 바디에 `masked_preview`(마스킹본 텍스트)·`evidence_summary` 포함(F-015 preview 계약 — repair-plan P0). raw 원문은 절대 미포함(F-013 §8 NFR 정합 — masked_preview는 이미 마스킹된 본문).
- repair-plan 2026-06-07 [default] P1 Plan-ambiguity: Adopt — error.filter.ts를 write_set+step8에 추가(도메인 code 우선), AC-1 no-raw를 port 경유로 축소(전체 6표면 검증=T-040).
- repair-plan 2026-06-07 [default] P1 Plan-sizing: Reject-conflict — 첫 엔드포인트 scaffolding(global pipe/filter 1회 설정 co-locate 자연), AC=3 ≤한계(SKILL scaffolding 예외).
- 구현 이탈(2026-06-07): (1) `@nestjs/platform-express`는 이미 dependencies에 존재(step1 no-op, lockfile 변경 없음). (2) `class-validator`/`class-transformer` 미설치 + 네트워크 차단으로 설치 불가 → step3 DTO 데코레이터·step8 ValidationPipe 대신 **manual validation**(plain DTO + 컨트롤러 수동 포맷/크기 체크 + 서비스 RESUME_EMPTY). AC-1/2/3 관측 동작 동일(201/413/415 envelope), YAGNI·ADR-006 시스템 경계 검증 원칙 부합. (3) evidence 카운트는 `evidence-summary.ts` 헬퍼로 분리(서비스 인라인 대신 — 동일 로직, 테스트 용이).

## 9. 의존성
- depends_on: [T-035]   # resumes masked/source/upload_format 컬럼 선행
- read_set: ["podo/apps/api/prisma/schema.prisma", "podo/apps/api/src/coverage/**", "ai/worker/src/worker/parse_resume.py"]
- write_set: ["podo/apps/api/src/resumes/**", "podo/apps/api/src/app.module.ts", "podo/apps/api/src/main.ts", "podo/apps/api/src/common/error.filter.ts", "podo/apps/api/test/resumes.spec.ts", "podo/apps/api/package.json", "pnpm-lock.yaml"]
- assumptions: ["T-035 마이그레이션 적용됨", "PrismaService 존재(T-026)"]
- verifier: "pnpm --filter @podo/api test"
- # lockfile race: package.json/pnpm-lock.yaml write(@nestjs/platform-express) → 단독 wave
