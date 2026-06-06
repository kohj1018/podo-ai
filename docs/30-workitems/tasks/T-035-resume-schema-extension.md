# T-035-resume-schema-extension

## 0. Status
draft

## 0-1. Type
migration

## 1. 작업 목적
`resumes` 테이블을 실 이력서 업로드 메타로 확장한다 — `masked`(마스킹 적용 여부)·`source`(업로드 출처)·`upload_format`(포맷) 컬럼 추가. **`content`는 마스킹본 전용(raw 원문 컬럼 없음 — M3 안전 불변식, F-013 §4).** Prisma DDL = 폴리글랏 계약 SSOT(ARCH §3-2)이므로 schema-contract pytest를 동반 갱신해 무음 drift(R6)를 차단한다.

## 2. 작업 범위
- `podo/apps/api/prisma/schema.prisma` `Resume` 모델에 3개 컬럼 추가(기존 `content`·`created_at`·`ranking_runs` 유지).
- Prisma migration 생성·적용.
- `ai/tests/test_schema_contract.py`에 `resumes` 신규 컬럼 존재 assert 추가.

## 3. 구현 항목
1. `podo/apps/api/prisma/schema.prisma:81-88` `model Resume` — 현재: `id`·`content`·`created_at`·`ranking_runs[]`만 (주석 "config/seed 합성 이력서") → 변경: 3컬럼 추가 + 주석을 M3로 갱신:
   ```prisma
   model Resume {
     id            Int          @id @default(autoincrement())
     content       String       // 마스킹본 전용 (raw PII 미저장 — M3 안전 불변식)
     masked        Boolean      @default(false)
     source        String       @default("seed")   // seed | upload | paste
     upload_format String       @default("txt")     // txt | md | paste
     created_at    DateTime     @default(now())
     ranking_runs  RankingRun[]
     @@map("resumes")
   }
   ```
   → 확인: `prisma format` + `prisma validate` 통과. (AC-1)
2. 마이그레이션 — 현재: 기존 seed row 존재(non-null 컬럼은 default 필요) → 변경: `pnpm --filter @podo/api exec prisma migrate dev --name resume_upload_fields`(DATABASE_URL 인라인 주입, .env 생성 금지 — T-020 메모 패턴). default가 기존 row를 채움. → 확인: `\d resumes`에 masked(boolean)·source(text)·upload_format(text) 존재. (AC-1)
3. `ai/tests/test_schema_contract.py:69` 부근 — 현재: `recommendations`/`ranking_runs` 등 assert만, `resumes` 미점검 → 변경: `resumes` 컬럼 assert 블록 추가:
   ```python
   rs = _columns("resumes")
   for col in ("content", "masked", "source", "upload_format"):
       assert col in rs, f"resumes.{col} 누락 (M3 업로드 메타)"
   assert rs.get("masked") == "boolean", f"resumes.masked != boolean: {rs.get('masked')}"
   ```
   → 확인: `DATABASE_URL=... uv run pytest ai/tests/test_schema_contract.py` green. (AC-1)

## 4. 제외 항목
- raw 원문 PII 컬럼·암호화 저장(M3 비범위 — `content`=마스킹본만). · 업로드 엔드포인트 코드(T-034). · 마스킹 로직(T-036). · resumes에 user/auth FK(멀티유저 M4).

## 4-1. 변경 예정 파일/경로
<!-- 구현 시점에 채운다. -->

## 5. 완료 조건
`resumes`에 masked·source·upload_format 컬럼이 마이그레이션되고, schema-contract pytest가 그 존재를 검증하며 green이다.

## 6. Acceptance Criteria
- AC-1 [Given] `Resume` 모델에 masked/source/upload_format 추가 + migration 적용 [When] `prisma migrate dev` 후 `uv run pytest ai/tests/test_schema_contract.py`(DATABASE_URL 주입) [Then] `resumes` 테이블에 masked(boolean)·source·upload_format 컬럼이 존재하고 schema-contract 테스트가 green이며, raw 원문 전용 컬럼은 추가되지 않는다(`content`만 텍스트 본문).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/tests/test_schema_contract.py::test_AC_2_dependent_columns_present_else_fail (resumes 컬럼 assert 추가 — 마이그레이션 전 red, 후 green)

## 6-2. TDD opt-out
- 사유: DDL 마이그레이션은 선언적 — 적용 결과를 schema-contract pytest가 검증(2-layer: 본 task가 스키마+계약 테스트 동시 제공, T-020 패턴 정합).
- Follow-up task: 해당 없음(본 task가 계약 테스트까지 포함).

## 7. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md)
- Feature: [F-013-resume-upload-api](../features/F-013-resume-upload-api.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 폴리글랏 DDL SSOT·규칙2·schema-contract)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-DB·D-CONTRACT)

## 8. 메모
- 해석 확정: 기존 seed row 보존 위해 신규 컬럼은 `@default` 부여(`masked=false`·`source="seed"`·`upload_format="txt"`). M3 keyless E2E의 마스킹 fixture seed는 `masked=true`로 명시 주입(T-037/stabilize). raw 원문 컬럼 없음(M3 안전 불변식).
- DATABASE_URL은 .env 생성 없이 명령 인라인 주입(AGENTS.md .env 금지 — T-020 메모 패턴). `--create-only`로 SQL 확인 후 적용 권장.

## 9. 의존성
- depends_on: [T-020]   # 기존 resumes 테이블(T-020 init migration) 위에 컬럼 추가
- read_set: ["podo/apps/api/prisma/schema.prisma"]
- write_set: ["podo/apps/api/prisma/schema.prisma", "podo/apps/api/prisma/migrations/**", "ai/tests/test_schema_contract.py"]
- assumptions: ["DATABASE_URL(마이그레이션된 PG) 설정됨", "T-020 init migration 적용됨"]
- verifier: "pnpm --filter @podo/api exec prisma migrate status"
- # T-034(엔드포인트)는 본 스키마 확장 후 시작 — schema.prisma write_set 선행
