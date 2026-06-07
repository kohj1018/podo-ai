# T-064-job-embeddings-table-and-worker

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
pgvector가 extension만 설치된 상태(컬럼·코드 0건)에서 **`job_embeddings` 테이블 DDL + JD 1회 임베딩·영속 worker**를 구현한다. 이것이 F-021 비용 구조 전환(N→K)의 물질적 선행 enabler다 — T-065가 이 테이블을 읽어 후보 선별을 수행한다. 서비스하는 가정: A-12(결정성 비용 보존)·GS-1(ADR-108 D1·D6).

## 2. 작업 범위
- `job_embeddings` 테이블 DDL: Prisma raw SQL migration(`job_posting_id INTEGER FK→job_postings(id)`[**`JobPosting.id`=Int autoincrement**] `+ embedding vector(1536) + embedding_version TEXT + model_id TEXT + created_at`). HNSW 인덱스(`USING hnsw (embedding vector_cosine_ops)`).
- `resume_embeddings` 테이블 DDL: `resume_id INTEGER PK/FK→resumes(id)`[Resume.id=Int] `+ embedding vector(1536) + embedding_version TEXT + model_id TEXT + created_at`. **resume도 영속(결정 2026-06-08): OpenAI 임베딩은 호출마다 byte-identical 아님(실측 cosine 0.968~0.99999 변동) → 재사용 필수, §8).**
- `ai/worker/src/worker/embedding.py` — `embed_jd(job_posting_id, jd_text) -> None` · `embed_resume(resume_id, masked_content) -> None`: 동일 `embedding_version` 행 존재 시 재호출 없이 skip(저장 벡터 재사용, GS-1 — ADR-108 D6). 없으면 OpenAI 임베딩(`text-embedding-3-small`/1536, `OPENAI_API_KEY` 재사용) → upsert.
- `ai/worker/src/worker/embed_batch.py` — `embed_new_jobs()` 신규 JD 배치 임베딩(`input`에 list, 요청당 ≤300K 토큰). per-JD 단건 증분은 후속(ADR-108 D5).
- schema-contract 테스트에 `job_embeddings`·`resume_embeddings` + vector 컬럼 추가(ARCH §3-2).
- `EMBEDDING_VERSION = "v1-text-embedding-3-small-1536"` 상수 핀(변경 시 전 임베딩 재생성 + cache_key_version bump). 모델 silent-update 감지용 `model_id`/`created_at` 동봉.

## 3. 구현 항목
1. `podo/apps/api/prisma/migrations/YYYYMMDD_add_embeddings/migration.sql` — 신설:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE TABLE job_embeddings (
     job_posting_id INTEGER PRIMARY KEY REFERENCES job_postings(id) ON DELETE CASCADE,  -- JobPosting.id = Int
     embedding vector(1536),  -- text-embedding-3-small 차원(확정 2026-06-08)
     embedding_version TEXT NOT NULL,
     model_id TEXT NOT NULL,
     created_at TIMESTAMPTZ DEFAULT now()
   );
   CREATE INDEX ON job_embeddings USING hnsw (embedding vector_cosine_ops);
   CREATE TABLE resume_embeddings (
     resume_id INTEGER PRIMARY KEY REFERENCES resumes(id) ON DELETE CASCADE,  -- Resume.id = Int
     embedding vector(1536),
     embedding_version TEXT NOT NULL,
     model_id TEXT NOT NULL,
     created_at TIMESTAMPTZ DEFAULT now()
   );
   CREATE INDEX ON resume_embeddings USING hnsw (embedding vector_cosine_ops);
   ```
   → 확인: `pnpm --filter @podo/api prisma migrate dev` 성공 (AC-1)
2. `ai/worker/src/worker/embedding.py` — 신설.
   - `EMBEDDING_VERSION = "v1-text-embedding-3-small-1536"` 상수(변경 시 migrate + 재생성).
   - OpenAI 클라이언트(`OPENAI_API_KEY` 재사용): `client.embeddings.create(model="text-embedding-3-small", input=[...], encoding_format="float")` → `resp.data[i].embedding`.
   - `embed_jd(job_posting_id: int, jd_text: str) -> None` / `embed_resume(resume_id: int, masked_content: str) -> None`: 동일 `embedding_version` 행 존재 시 early return(skip, 저장 벡터 재사용). 없으면 API 호출 → upsert(`model_id` 동봉). → 확인: mock API 단위 테스트 (AC-2, AC-3, AC-4)
3. `ai/worker/src/worker/embed_batch.py` — 신설. `embed_new_jobs(db) -> int`: `job_postings` LEFT JOIN `job_embeddings`로 임베딩 없는 JD 목록 조회 → `embed_jd()` 배치 호출 → 처리 건수 반환. → 확인: fixture DB 단위 테스트 (AC-1, AC-2)
4. `ai/worker/tests/test_embedding.py` — 신설. AC-1~AC-3 커버.
5. `ai/tests/test_schema_contract.py` — `job_embeddings`·`resume_embeddings` 테이블·`embedding` vector 컬럼 assert 추가. → 확인: pytest pass (AC-1)

## 4. 제외 항목
- 후보 선별 로직(T-065) — 본 task는 JD·resume "임베딩 영속"까지만.
- per-JD 단건 증분 트리거 — M5 필수 아님, 후속(ADR-108 D5).

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
- AC-4 [Given] masked 이력서 [When] `embed_resume()` 1회 호출 후 재호출 [Then] 최초 1회만 API 호출·`resume_embeddings` 영속, 재호출은 저장 벡터 재사용(API 0). 임베딩 호출 비결정성을 영속으로 차단해 후보선별 입력이 결정적(GS-1 — ADR-108 D6).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_embedding.py::test_AC_1_new_job_embedded_and_persisted
- AC-2 → pytest::ai/worker/tests/test_embedding.py::test_AC_2_no_reembed_when_version_matches
- AC-3 → pytest::ai/worker/tests/test_embedding.py::test_AC_3_reembed_on_version_mismatch
- AC-4 → pytest::ai/worker/tests/test_embedding.py::test_AC_4_resume_embedding_persisted_and_reused

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-021-jd-vectorization-and-cost](../features/F-021-jd-vectorization-and-cost.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 pgvector DDL=Prisma/DML=Python, §7-3 워커)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md) (D1 DDL 경계, D6 결정성)

## 8. 메모 — 결정 확정 (2026-06-08, 사용자 승인)
- **모델/차원**: `text-embedding-3-small` / **1536** (공식문서 검증 2026-06-08 — 현재 권장 small, 후속 모델 없음). `EMBEDDING_VERSION="v1-text-embedding-3-small-1536"`.
- **API 키**: `OPENAI_API_KEY` 재사용(별도 `EMBEDDING_API_KEY` 없음 — 단순화). SDK: `client.embeddings.create(..., encoding_format="float")`. 배치는 `input` list(요청당 ≤300K 토큰), 대량 초기적재는 Batch API(50% 할인) 선택.
- **결정성(GS-1) = 영속+재사용 필수**: OpenAI 임베딩은 호출마다 byte-identical 아님(small 동일입력 cosine 0.968~0.99999 변동 실측). 동일입력 재호출이 아니라 **저장 벡터 재사용**으로 결정성 보장(ADR-108 D6 검증됨). `model_id`/`created_at` 동봉 → 모델 silent-update 감지 시 재임베딩.
- **resume 임베딩도 영속**(`resume_embeddings`, masked content + `embedding_version` 키): T-065 후보선별의 top-K_v 입력이 run마다 흔들리지 않게(GS-1). pgvector 벡터는 API가 L2 정규화 → cosine=내적.
- **무키 E2E**: fixture JD·resume 임베딩을 seed(LLM 웜캐시와 동형) → keyless 재현. T-052/e2e 배선에 반영.
- HNSW `m`/`ef_construction`은 pgvector 기본값 시작(F-023 후 튜닝). 구조화 JD JSONB는 M5 미신설, raw_text로 부족 시 F-023 후 재검토(ADR-108 D1).

## 9. 의존성
- depends_on: []
- read_set: ["podo/apps/api/prisma/schema.prisma", "ai/worker/src/worker/persistence.py", "ai/core/src/core/models.py"]
- write_set: ["podo/apps/api/prisma/migrations/**", "ai/worker/src/worker/embedding.py", "ai/worker/src/worker/embed_batch.py", "ai/worker/tests/test_embedding.py", "ai/tests/test_schema_contract.py"]
- assumptions: ["pgvector extension 설치됨(pgvector/pgvector:pg16, M4 확인)", "OPENAI_API_KEY env 설정됨(임베딩·LLM 공용 — 별도 EMBEDDING_API_KEY 없음)"]
- verifier: "uv run pytest ai/worker/tests/test_embedding.py ai/tests/test_schema_contract.py"
