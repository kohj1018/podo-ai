# T-020-prisma-schema-migration

## 0. Status
done

## 0-1. Type
migration

## 1. 작업 목적
Prisma를 스키마 SSOT로 최소 5테이블(`job_postings`·`crawl_runs`·`ranking_runs`·`recommendations`·`resumes`) + pgvector extension을 DDL로 정의·마이그레이션한다. `recommendations`(feed projection)와 `ranking_runs` 결정적 upsert 키가 핵심(cross-LLM P0/P1 회수).

## 2. 작업 범위
- `podo/apps/api/prisma/schema.prisma`: 5 모델 + 소유권(§3-2: crawler→job_postings/crawl_runs, worker→ranking_runs/recommendations, api→resumes).
- `ranking_runs` 결정적 복합 unique 키. `recommendations` scalar projection + `rank_position` 인덱스. `crawl_runs` run별 1행.
- 초기 migration + `CREATE EXTENSION vector`(raw SQL — DDL은 Prisma 소유, §3-2 규칙2).

## 3. 구현 항목
1. `podo/apps/api/prisma/schema.prisma` — 현재: 없음(T-018 scaffold) → 변경: 모델 정의 (AC-1·AC-2):
   - `job_postings`: id, source, company, title, url, raw_text, role_family, posted_at, closing_at, diff_status, fetched_at.
   - `crawl_runs`(**run별 1행**): id, channel, run_at, status, new_count, closed_count, error.
   - `ranking_runs`(worker): id, resume_id, job_set_hash, model, prompt_version, scoring_mode, ranking_mode, cache_key_version, `result Json`, created_at + `@@unique([resume_id, job_set_hash, model, prompt_version, scoring_mode, ranking_mode, cache_key_version])`.
   - `recommendations`(**feed projection**): id, run_id(FK ranking_runs), job_posting_id(FK job_postings), `rank_position Int`, **`fit_level Int?`(nullable — held 공고는 NULL)**, domain_alignment, `status`(scored|held) + `@@index([run_id, rank_position])`(**current-run 한정 커서** — cross-LLM P1 회수, rank_position 단독은 run 간 중복).
   - `resumes`: id, content, created_at.
2. 의존성 — `pnpm --filter api add -D prisma && pnpm --filter api add @prisma/client` (용도: ORM/마이그레이션). → 확인: `prisma` CLI 가용. (AC-1)
3. 초기 마이그레이션 — `pnpm --filter api prisma migrate dev --name init`. 생성된 `migration.sql` 맨 앞에 `CREATE EXTENSION IF NOT EXISTS vector;` prepend(extension이 테이블보다 먼저). → 확인: **application 테이블 5개**(`information_schema.tables WHERE table_schema='public' AND table_name IN (...)` 이름 필터 — Prisma `_prisma_migrations` 제외, 전체 `\dt` 카운트 금지) + `\dx`에 vector. (AC-1)
4. → 확인: `ranking_runs` 7-컬럼 복합 unique 제약 + `recommendations.(run_id, rank_position)` 인덱스 + `fit_level` nullable 존재(`\d ranking_runs`/`\d recommendations`). (AC-2)

## 4. 제외 항목
- vector 컬럼·HNSW·검색 DML(F-006 비범위) · Python read/write(T-021) · worker write 로직(T-022) · 추가 user 테이블.

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/prisma/schema.prisma`, `podo/apps/api/prisma/migrations/**`, `podo/apps/api/package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`(allowBuilds: prisma 빌드 승인)

## 5. 완료 조건
`prisma migrate dev`가 5테이블 + pgvector extension을 생성하고, `ranking_runs` 복합 unique 키와 `recommendations` 정렬 컬럼/인덱스가 존재한다.

## 6. Acceptance Criteria
- AC-1 [Given] schema.prisma 5모델 + extension prepend [When] `prisma migrate dev --name init` [Then] `public` 스키마에 **이름으로 필터한 5개 application 테이블**(`_prisma_migrations` 제외)과 `vector` extension이 존재한다.
- AC-2 [Given] 마이그레이션 적용 [When] DB 메타 조회 [Then] `ranking_runs`에 7-컬럼 복합 unique 제약이, `recommendations`에 `rank_position`·`fit_level`(nullable)·`status` scalar 컬럼 + `(run_id, rank_position)` 인덱스가 존재한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → (마이그레이션 검증) `prisma migrate dev` 후 `psql -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('job_postings','crawl_runs','ranking_runs','recommendations','resumes')"` = 5 + `\dx` vector
- AC-2 → pytest::ai/tests/test_schema_contract.py::test_AC_2_ranking_unique_and_recommendations_index (T-021이 실측 — 본 task는 스키마 제공)

## 6-2. TDD opt-out
- 사유: DDL 마이그레이션은 선언적 — 적용 결과를 schema-contract pytest(T-021)가 검증(2-layer: T-020 스키마 제공, T-021 계약 테스트).
- Follow-up task: T-021(schema-contract 실측).

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-006-db-schema-contract](../features/F-006-db-schema-contract.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 소유권·규칙2·3)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §11](../../20-system/SCORING_PIPELINE_SPEC.md) (JSONB 산출 → result shape)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-DB·D-CONTRACT)

## 8. 메모
- 해석 확정: `recommendations`는 cross-LLM P0(M2-repair-1) 회수 — opaque JSONB만으론 정렬 feed 불가 해소. `ranking_runs` 복합키 = M2-repair-5.
- vector는 extension만(컬럼 미생성) — F-006 §5 정합.
- repair-plan 2026-06-06 [default] P0 Plan-FAC-coverage: Adopt-modified — `fit_level Int?` nullable(held 공고 NULL 표현, T-022가 pending_job_ids로 held row).
- repair-plan 2026-06-06 [default] P1 Plan-dep: Adopt — depends_on에 T-019 추가(migrate dev는 DB 런타임 필요).
- repair-plan 2026-06-06 [default] P1 Plan-ambiguity: Adopt — `\dt` 전체 카운트→이름 필터(Prisma `_prisma_migrations` 제외).
- repair-plan 2026-06-06 [default] P1 Plan-ambiguity: Adopt — 인덱스 `(run_id, rank_position)`(current-run 한정 커서, T-026 정합).
- 구현 노트(2026-06-06): 메인 세션 수동(DB 마이그레이션 corruption 리스크 + 포크 사망 패턴). PK는 **Int autoincrement(SERIAL)** — Python(T-022/T-024)이 raw SQL write → DB측 id 생성 필수(cuid/uuid는 client-side). 컬럼 snake_case(T-021 Python 계약).
- Prisma **6.19.3로 핀**: 설치 시 최신 7.8.0이 잡혔으나 Prisma 7은 datasource `url = env(...)` 제거(→`prisma.config.ts`+driver adapter 요구)로 task 클래식 워크플로와 불일치 → 6.x 다운그레이드(task §3 정합·안정성·ADR-006). allowBuilds에 prisma/@prisma/engines/@prisma/client 빌드 승인.
- DATABASE_URL은 **.env 생성 없이** 명령 인라인 주입(AGENTS.md .env 금지 + Read deny 준수). 마이그레이션: `--create-only` 생성 → migration.sql 맨 앞 `CREATE EXTENSION IF NOT EXISTS vector` prepend → `migrate dev` 적용.
- 라이브 검증: 5 application 테이블 + vector 0.8.2 + ranking_runs 7컬럼 unique + recommendations (run_id,rank_position) 인덱스·fit_level nullable 전부 psql 확인. `migrate status`=up to date.

## 9. 의존성
- depends_on: [T-018, T-019]   # T-018 api scaffold(Prisma 위치) + T-019 docker PG(migrate dev는 DB 런타임 필요 — cross-LLM P1)
- read_set: ["docs/20-system/SCORING_PIPELINE_SPEC.md"]
- write_set: ["podo/apps/api/prisma/**", "podo/apps/api/package.json", "pnpm-lock.yaml"]
- assumptions: ["DATABASE_URL 설정됨"]
- verifier: "pnpm --filter api prisma migrate status"
- # lockfile race: package.json/pnpm-lock.yaml write → T-018과 다른 wave
