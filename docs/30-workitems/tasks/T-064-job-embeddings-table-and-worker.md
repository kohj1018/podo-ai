# T-064-job-embeddings-table-and-worker

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
pgvector가 extension만 설치된 상태(컬럼·코드 0건)에서 **`job_embeddings` 테이블 DDL + JD 1회 임베딩·영속 worker**를 구현한다. 이것이 F-021 비용 구조 전환(N→K)의 물질적 선행 enabler다 — T-065가 이 테이블을 읽어 후보 선별을 수행한다. 서비스하는 가정: A-12(결정성 비용 보존)·GS-1(ADR-108 D1·D6).

## 2. 작업 범위
- `job_embeddings` 테이블 DDL: Prisma raw SQL migration(`job_posting_id INTEGER FK→job_postings(id)`[**`JobPosting.id`=Int autoincrement** — TEXT 아님] `+ embedding vector(N) + embedding_version TEXT + created_at`). HNSW 인덱스(`CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`).
- `ai/worker/src/worker/embedding.py` — JD 임베딩 worker: `embed_jd(job_posting_id) -> None`. 신규 JD(embedding 없음) 배치 감지 → embedding API 호출 → `job_embeddings` upsert. **이미 `embedding_version` 일치하는 행이 있으면 재임베딩 없이 skip**(GS-1 결정성: 저장된 벡터 재사용, 재호출 없음 — ADR-108 D6).
- `ai/worker/src/worker/embed_batch.py` — K-batch 진입점: `embed_new_jobs()` 신규 JD 배치 임베딩. M5 필수는 배치(per-JD 단건 증분은 후속 — ADR-108 D5).
- schema-contract 테스트에 `job_embeddings` + vector 컬럼 추가(ARCH §3-2).
- 임베딩 모델·차원·버전은 `embedding_version` 상수로 핀(변경 시 전 JD 재임베딩 + cache_key_version bump 필요 — 열린 질문에 명시).

## 3. 구현 항목
1. `podo/apps/api/prisma/migrations/YYYYMMDD_add_job_embeddings/migration.sql` — 신설:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE TABLE job_embeddings (
     job_posting_id INTEGER PRIMARY KEY REFERENCES job_postings(id) ON DELETE CASCADE,  -- JobPosting.id = Int(autoincrement), TEXT 아님
     embedding vector(1536),  -- 모델 차원: 열린 질문, 초기값 1536(OpenAI text-embedding-3-small)
     embedding_version TEXT NOT NULL,
     created_at TIMESTAMPTZ DEFAULT now()
   );
   CREATE INDEX ON job_embeddings USING hnsw (embedding vector_cosine_ops);
   ```
   → 확인: `pnpm --filter @podo/api prisma migrate dev` 성공 (AC-1)
2. `ai/worker/src/worker/embedding.py` — 신설.
   - `EMBEDDING_VERSION = "v1-text-embedding-3-small-1536"` 상수(변경 금지 — 변경 시 migrate 필요).
   - `embed_jd(job_posting_id: str, jd_text: str) -> None`: `job_embeddings`에 해당 `job_posting_id`·동일 `embedding_version` 행 존재 시 early return(skip). 없으면 embedding API 호출 → upsert. → 확인: mock API 단위 테스트 (AC-2, AC-3)
3. `ai/worker/src/worker/embed_batch.py` — 신설. `embed_new_jobs(db) -> int`: `job_postings` LEFT JOIN `job_embeddings`로 임베딩 없는 JD 목록 조회 → `embed_jd()` 배치 호출 → 처리 건수 반환. → 확인: fixture DB 단위 테스트 (AC-1, AC-2)
4. `ai/worker/tests/test_embedding.py` — 신설. AC-1~AC-3 커버.
5. `ai/tests/test_schema_contract.py` — 기존 schema-contract 테스트에 `job_embeddings` 테이블·`embedding` vector 컬럼 assert 추가. → 확인: pytest pass (AC-1)

## 4. 제외 항목
- 후보 선별 로직(T-065) — 본 task는 "임베딩 영속"까지만.
- resume 임베딩 영속 — 선택적, T-065에서 채점 시 1회 생성(영속은 재검토).
- per-JD 단건 증분 트리거 — M5 필수 아님, 후속(ADR-108 D5).
- 임베딩 모델 선택 최종 확정 — 열린 질문(초기값 사용).

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/prisma/migrations/` (신규 migration)
- `ai/worker/src/worker/embedding.py` (신설)
- `ai/worker/src/worker/embed_batch.py` (신설)
- `ai/worker/tests/test_embedding.py` (신설)
- `ai/tests/test_schema_contract.py` (job_embeddings assert 추가)

## 5. 완료 조건
`job_embeddings` 테이블이 HNSW 인덱스와 함께 생성되고, 신규 JD가 배치 임베딩되어 영속된다. 재채점 시 동일 JD는 재임베딩 없이 저장 벡터를 재사용한다.

## 6. Acceptance Criteria
- AC-1 [Given] `job_postings`에 JD ≥1개, `job_embeddings` 행 없음 [When] `embed_new_jobs()` 실행 [Then] 해당 JD가 `job_embeddings`에 `embedding_version` 포함 upsert되고 schema-contract 테스트가 vector 컬럼을 확인한다.
- AC-2 [Given] `job_embeddings`에 동일 `job_posting_id`·동일 `embedding_version` 행 존재 [When] `embed_jd()` 재호출 [Then] embedding API를 호출하지 않고 early return한다(재임베딩 0 — GS-1 결정성, ADR-108 D6).
- AC-3 [Given] `embedding_version` 불일치 행 존재(구버전) [When] `embed_jd()` 호출(신버전) [Then] 신버전으로 upsert하고 API를 1회 호출한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_embedding.py::test_AC_1_new_job_embedded_and_persisted
- AC-2 → pytest::ai/worker/tests/test_embedding.py::test_AC_2_no_reembed_when_version_matches
- AC-3 → pytest::ai/worker/tests/test_embedding.py::test_AC_3_reembed_on_version_mismatch

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-021-jd-vectorization-and-cost](../features/F-021-jd-vectorization-and-cost.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 pgvector DDL=Prisma/DML=Python, §7-3 워커)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md) (D1 DDL 경계, D6 결정성)

## 8. 메모
- 열린 질문(builder 착수 전 확정 필요): 임베딩 모델·차원(초기값 text-embedding-3-small/1536 — 변경 시 `EMBEDDING_VERSION` bump + 전 JD 재임베딩). HNSW `m`·`ef_construction` 파라미터는 pgvector 기본값으로 시작(F-023 측정 후 튜닝).
- 구조화 JD JSONB 영속 여부(ADR-108 D1 재검토 — T-065에서 스킬 매칭 시 raw_text로 충분한지 확인 후 결정).

## 9. 의존성
- depends_on: []
- read_set: ["podo/apps/api/prisma/schema.prisma", "ai/worker/src/worker/persistence.py", "ai/core/src/core/models.py"]
- write_set: ["podo/apps/api/prisma/migrations/**", "ai/worker/src/worker/embedding.py", "ai/worker/src/worker/embed_batch.py", "ai/worker/tests/test_embedding.py", "ai/tests/test_schema_contract.py"]
- assumptions: ["pgvector extension이 DB에 설치되어 있음(M4 확인)", "embedding API key env 변수 설정됨(EMBEDDING_API_KEY)"]
- verifier: "uv run pytest ai/worker/tests/test_embedding.py ai/tests/test_schema_contract.py"
