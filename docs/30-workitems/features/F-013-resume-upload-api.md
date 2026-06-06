# F-013-resume-upload-api: NestJS 이력서 업로드 엔드포인트 + DB 스키마 확장

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
단일 사용자가 자신의 이력서(`.txt`/`.md`/paste 텍스트)를 NestJS API에 업로드하면 `resumes` 테이블에 영속되는 경로를 만든다. **raw PII는 이 시점에는 API가 받지만 PII 마스킹(F-014)이 동일 요청 흐름 내에서 처리된 뒤 마스킹본만 DB에 저장**된다. `resumes` 스키마 확장(M3 신규 필드), schema-contract test 갱신, OpenAPI 계약 스펙이 함께 산출된다.

근거 insight: I-1 (분산 채널·스코어링 입력 신뢰 — DISCOVERY §15)

## 2. 사용자 가치 (User Story)
- As a **유진(신입/졸업예정 개발자 구직자)**, I want to upload my resume (`.txt`/`.md` or paste), so that the system can score job postings against my actual skills and experience.

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 사용자가 UI(F-015)에서 `.txt` 파일을 선택하거나 텍스트 영역에 붙여넣기.
2. `POST /api/v1/resumes` 호출 → DTO 검증(파일 크기 ≤100KB, content-type 허용 목록).
3. API가 요청 본문(raw text)을 F-014 마스킹 파이프로 전달 → 마스킹본 반환.
4. 마스킹본을 `resumes.content` 컬럼에 저장, `resumes.masked=true`, `resumes.source` 기록.
5. 201 응답 + `{ data: { resume_id, masked: true, evidence_count } }`.
### Alternate path
1. 사용자가 paste 방식으로 텍스트 직접 입력 → 동일 엔드포인트, `source=paste` 기록.
### Fail path
1. 🔴 파일 크기 초과(>100KB) → 413 + 에러 바디 `{ error: { code: "RESUME_TOO_LARGE", ... } }`.
2. 🔴 금지 포맷(PDF/docx) → 415 + `RESUME_FORMAT_NOT_SUPPORTED`.
3. 🔴 DB write 실패 → 500 + `INTERNAL_ERROR` (raw PII 로그 금지).

## 4. 범위
- NestJS `ResumesModule`: `ResumesController`(POST `/api/v1/resumes`) + `ResumesService` + DTO(`CreateResumeDto`) + exception filter 활용.
- Prisma 스키마 확장: `resumes` 테이블에 `masked: Boolean`, `source: String`, `upload_format: String` 필드 추가. **`content` 컬럼 = 마스킹본 전용 (raw 원문 컬럼 없음).**
- Prisma migration 파일 생성 + `pnpm --filter api prisma migrate dev`.
- schema-contract pytest 갱신: `resumes` 신규 컬럼 존재 확인 테스트.
- F-014(PII 마스킹 모듈)는 동일 요청 흐름 내에서 호출됨 — F-013은 마스킹 로직을 직접 구현하지 않고 F-014 산출 인터페이스에 의존(구현 전 인터페이스 계약 정의).

## 5. 비범위
- PII 마스킹 로직 구현 (F-014).
- UI 업로드 화면 (F-015).
- PDF/docx 업로드 (M4 이후).
- 이력서 버전 관리·다중 이력서 A/B.
- raw 원문 PII 영속·암호화 저장.
- 인증·멀티유저.

## 6. 요구사항
- `POST /api/v1/resumes`: 파일 업로드(`multipart/form-data`) + 텍스트 붙여넣기(`application/json`) 양쪽 지원.
- DTO 검증: 파일 크기 ≤100KB, 허용 포맷 `.txt`/`.md`/plain text.
- `resumes.content` = 마스킹본만 저장 (raw 원문 저장 금지 — M3 안전 불변식).
- 에러 바디: `{ error: { code: string, message: string } }` (ARCH §7-1 컨벤션).
- schema-contract test: `resumes` 테이블 신규 컬럼(masked, source, upload_format) 존재 pytest로 검증.

## 7. Feature-level Acceptance Criteria
- **FAC-1:** `POST /api/v1/resumes`에 유효한 `.txt` 텍스트를 보내면 201 + `{ data: { resume_id, masked: true } }`를 반환하고 DB `resumes.content`에 마스킹본이 저장된다.
- **FAC-2:** PDF 파일을 업로드하면 415 + `{ error: { code: "RESUME_FORMAT_NOT_SUPPORTED" } }`를 반환한다.
- **FAC-3:** 100KB 초과 텍스트를 전송하면 413 + `{ error: { code: "RESUME_TOO_LARGE" } }`를 반환한다.
- **FAC-4:** schema-contract pytest가 `resumes` 테이블 신규 컬럼(masked, source, upload_format) 존재를 검증하고 green이다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-034:AC-1
- FAC-2 → T-034:AC-2
- FAC-3 → T-034:AC-3
- FAC-4 → T-035:AC-1

## 8. Non-functional Requirements
- 요청 처리 중 raw PII가 NestJS 애플리케이션 로그에 출력되지 않아야 한다.
- `content` 필드는 응답 바디에 미포함(preview는 F-015에서 별도 엔드포인트 또는 업로드 응답에 마스킹 preview만).

## 8-1. UX 흐름 품질
(해당 없음) — API 레이어, UI 없음.

## 9. 엣지 케이스
- 빈 파일 업로드 → 400 + `RESUME_EMPTY`.
- 동일 사용자가 이미 이력서를 보유 중 재업로드 → 현재 이력서 교체(단일 활성 이력서 원칙). 이전 `resume_id` 비활성화 or `resumes.active` 플래그 관리(T-034에서 구체 설계).

## 10. 의존성
- F-012(doc-reconcile) — 용어 정합 선행. 단, API 코드 구현은 F-012 완료와 무관하게 병렬 가능.
- F-014(PII 마스킹) — 마스킹 인터페이스를 F-013 구현 전 계약 정의 필요(T-034가 stub 또는 계약 먼저 정의, T-036이 구현).

## 11. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§4 G4, §8 흐름2)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1), [## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 12. 열린 질문
- 단일 활성 이력서 교체 시 기존 `ranking_runs`와의 연결을 어떻게 처리할지 (이전 resume_id 기반 캐시 키 보존 여부) → T-034에서 결정.
- F-014 마스킹 모듈이 NestJS 서비스 내부에서 호출되는지 vs Python worker로 위임되는지 → 경계 결정 필요 (현재 가정: NestJS 내 TypeScript 마스킹 모듈, 단순 regex 기반).
