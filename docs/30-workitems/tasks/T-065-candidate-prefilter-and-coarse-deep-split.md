# T-065-candidate-prefilter-and-coarse-deep-split

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
T-064가 영속한 `job_embeddings`를 읽어 **하이브리드 합집합(벡터 top-K_v ∪ 도메인/role_family ∪ 스킬/키워드)으로 후보 K개를 선별**하고, 파이프라인 본체(`run_scoring`)를 K개에만 호출하는 비용 구조 전환(N→K)을 완성한다. 후보 밖 공고는 coarse projection에 materialize(fit_level 없음)하고 api가 read-only 서빙한다. 이 task가 F-021의 핵심 비용 레버다(ADR-108 D2~D4).

## 2. 작업 범위
- `ai/worker/src/worker/prefilter.py` — 하이브리드 후보 선별: `select_candidates(resume_embedding, job_embeddings, resume_domains, K_v, K_max) -> CandidateSet`.
  - 벡터: pgvector HNSW ANN → top-K_v(유사도 내림차순).
  - 도메인/role_family: `resume.primary_domains / secondary_domains ↔ job.role_family` 매칭.
  - 스킬/키워드: resume 스킬 ↔ **`job_postings.raw_text` 키워드 매칭**(현 Prisma `JobPosting`에 `tech_stack` 컬럼 없음 — raw_text 기반. 구조화 JD JSONB 영속은 ADR-108 D1 후속 옵션, M5 미도입).
  - 합집합 → K_max cap, **결정적 tie-break(유사도 desc, job_id asc)**.
- `ai/worker/src/worker/scoring_runner.py` (또는 기존 `run_scoring` 호출 래퍼) — `prefilter` 결과 K개를 `run_scoring(resume, candidates)` 입력으로 사용. 파이프라인 본체(step1~12)·캐시 키·`recommendations` 구조 **불변**(ADR-108 D4).
- `ai/worker/src/worker/coarse_materialize.py` — 후보 밖 공고 coarse projection: `(job_posting_id, similarity_rank, scored_at)` worker-소유 테이블에 저장. **fit_level 없음**. api/feed는 직접 vector 쿼리 수행 금지(ADR-108 D3).
- `podo/apps/api/src/feed/feed.controller.ts` 확장 — coarse 섹션 endpoint(또는 쿼리 파라미터): `GET /api/v1/feed?section=coarse`. `coarse_candidates` 테이블 read-only 조회 → `{job_posting_id, similarity_rank}` 반환(**fit_level·추천 배지 없음**).
- coarse 섹션 UI(`CoarseSection`) — **섹션 wrapper**(새 카드 컴포넌트 아님): 기존 `JobCard`를 `showFitBadge=false` variant로 렌더(FitScoreRing/PassBand 제거, DESIGN §7-3), 유사도순 목록, "아직 깊이 안 본 공고예요" copy. **deep 피드와 별도 cursor**(ADR-108 D3).
- `cache_key_version`에 임베딩 모델·후보선별 버전·K 반영(변경 시 결정적 무효화 — ADR-108 D6).
- Prisma migration: `coarse_candidates` 테이블(`job_posting_id INTEGER FK→job_postings(id)` [JobPosting.id=Int], `user_id TEXT FK→users(id)` [User.id=String cuid], `similarity_rank`, `scored_at`).

## 3. 구현 항목
1. `podo/apps/api/prisma/migrations/YYYYMMDD_add_coarse_candidates/migration.sql` — `coarse_candidates` 테이블 신설(job_posting_id FK, user_id FK, similarity_rank FLOAT, scored_at TIMESTAMPTZ). → 확인: migrate 성공 (AC-3)
2. `ai/worker/src/worker/prefilter.py` — 신설. `select_candidates(...)`: pgvector `<=>` 연산자로 top-K_v 조회(SQL: `ORDER BY embedding <=> $resume_vec LIMIT $K_v`), 도메인·스킬 매칭 집합 계산, 합집합 → K_max cap → 유사도 desc/job_id asc 정렬 → `CandidateSet` 반환. → 확인: 단위 테스트(합집합 로직·tie-break 결정성) (AC-1, AC-4)
3. `ai/worker/src/worker/scoring_runner.py` — 신설(또는 기존 진입점 수정). `run_full_scoring(resume, all_jobs, db)`:
   - resume 임베딩: T-064 `embed_resume()`로 영속·재사용(매 채점 재생성 금지 — 임베딩 호출 비결정성 차단, GS-1).
   - `select_candidates()` → K개.
   - K개에만 `run_scoring(resume, candidates)` 호출 — 본체 불변.
   - 후보 밖 공고 → `coarse_materialize()`.
   - `cache_key_version` 검증(버전 불일치 시 결정적 무효화). → 확인: 단위 테스트(K개 호출 확인·비용 실측 mock) (AC-2)
4. `ai/worker/src/worker/coarse_materialize.py` — 신설. `materialize_coarse(non_candidates, similarity_scores, user_id, db)`: `coarse_candidates` upsert(fit_level 컬럼 없음, similarity_rank만). → 확인: 단위 테스트 (AC-3)
5. `podo/apps/api/src/feed/feed.controller.ts` — coarse 섹션 쿼리 추가(`?section=coarse`). `coarse_candidates` 조회 → `fit_level` 필드 없는 응답. vector 쿼리 코드 api 레이어에 0줄 — worker materialize만 읽음. → 확인: jest (AC-3)
6. `podo/apps/web/components/CoarseSection.tsx` — 신설. 기존 `JobCard` 재사용(props에 `showFitBadge=false`). "아직 깊이 안 본 공고예요 — 원하면 분석할게요" copy. deep 피드와 별도 cursor/scroll. → 확인: 스냅샷 또는 Playwright (AC-3)
7. `ai/worker/tests/test_prefilter.py` — AC-1·AC-4 커버(합집합·tie-break·K_max cap·결정성).
8. `ai/worker/tests/test_scoring_runner.py` — AC-2 커버(K개 호출 상한·coarse 분기).

## 4. 제외 항목
- per-JD 단건 증분 deep scoring — 후속(ADR-108 D5).
- 모델 티어링(저가/고가 분리) — F-023 측정 후(ADR-108 D7).
- on-demand coarse→deep 승격(사용자가 "분석" 요청) — M5 비범위, 엣지 케이스 등록.
- api/feed 직접 vector 쿼리 — 금지(ADR-108 D3 위반).

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/prisma/migrations/` (coarse_candidates 신규 migration)
- `ai/worker/src/worker/prefilter.py` (신설)
- `ai/worker/src/worker/scoring_runner.py` (신설 또는 기존 확장)
- `ai/worker/src/worker/coarse_materialize.py` (신설)
- `ai/worker/tests/test_prefilter.py` (신설)
- `ai/worker/tests/test_scoring_runner.py` (신설)
- `podo/apps/api/src/feed/feed.controller.ts` (coarse 섹션 추가)
- `podo/apps/web/components/CoarseSection.tsx` (신설)

## 5. 완료 조건
채점이 후보 K개에만 LLM deep 분석을 수행하고, 후보 밖 공고는 coarse projection(fit_level 없음, 유사도순)에 materialize되어 피드에 별도 섹션으로 노출된다. 동일 입력 2회 채점 결과 변동 0.

## 6. Acceptance Criteria
- AC-1 [Given] N개 JD + 이력서 임베딩 [When] `select_candidates()` 호출 [Then] 벡터+도메인+스킬 합집합이 K_max 이하로 cap되고 동일 입력에 동일 후보 집합을 반환한다(tie-break: 유사도 desc/job_id asc, 결정적).
- AC-2 [Given] N개 JD 중 후보 K개 선별 [When] `run_full_scoring()` 실행 [Then] `run_scoring` 내부 LLM 매칭/검증 호출이 N이 아니라 K에 비례하며(mock 검증), `recommendations`에 K개 이내 deep 결과만 저장된다.
- AC-3 [Given] 후보 밖 N-K개 공고 [When] coarse materialize 후 `GET /api/v1/feed?section=coarse` 요청 [Then] `fit_level` 필드 없이 유사도 rank만 포함된 응답이 반환되고, CoarseSection UI에 FitScoreRing/PassBand 배지 없이 노출된다.
- AC-4 [Given] 동일 (이력서, 공고집합) [When] 2회 연속 `select_candidates()` 호출 [Then] 동일 후보 집합 반환(GS-1 — 영속된 임베딩 재사용, tie-break 결정적).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_prefilter.py::test_AC_1_hybrid_union_and_deterministic_tiebreak
- AC-2 → pytest::ai/worker/tests/test_scoring_runner.py::test_AC_2_llm_calls_proportional_to_K
- AC-3 → vitest::podo/apps/api/test/feed_coarse.spec.ts::test_AC_3_coarse_section_no_fit_level + vitest::podo/apps/web/test/coarse_section.spec.tsx::test_AC_3_coarse_no_badge
- AC-4 → pytest::ai/worker/tests/test_prefilter.py::test_AC_4_deterministic_candidates_gs1

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-021-jd-vectorization-and-cost](../features/F-021-jd-vectorization-and-cost.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 pgvector DML=Python/api read-only, §7-3 워커)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) (coarse 섹션 endpoint `GET /api/v1/feed?section=coarse`)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (step1~12 불변 — K개 입력만)
- Design: [DESIGN](../../20-system/DESIGN.md) (§7-3 CoarseSection — 배지 없음)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md) (D2 합집합, D3 coarse/deep 분리, D4 본체 불변, D6 결정성)

## 8. 메모
- K_v·K_max 초기값: K_v≈50/K_max≈80(ADR-108 D2 — F-023 recall 측정 후 축소).
- 스킬 매칭은 `job_postings.raw_text` 키워드 기반으로 확정한다(**현 schema에 `tech_stack` 컬럼 없음** — 2026-06-08 결정). 구조화 JD JSONB 영속(ADR-108 D1)은 raw_text로 recall 부족이 드러날 때만 F-023 이후 재검토(충분하면 미신설).
- 열린 질문: pgvector ANN top-K_v 쿼리 정확도(ef_search 파라미터) — F-023 recall 측정 후 튜닝.

## 9. 의존성
- depends_on: [T-064, T-066]
- read_set: ["ai/worker/src/worker/embedding.py", "ai/worker/src/worker/persistence.py", "ai/core/src/core/models.py", "podo/apps/api/src/feed/feed.controller.ts"]
- write_set: ["ai/worker/src/worker/prefilter.py", "ai/worker/src/worker/scoring_runner.py", "ai/worker/src/worker/coarse_materialize.py", "podo/apps/api/prisma/migrations/**", "podo/apps/api/src/feed/feed.controller.ts", "podo/apps/web/components/CoarseSection.tsx"]
- assumptions: ["T-064 완료(job_embeddings 영속 가능)", "T-066 완료(resume.primary/secondary_domains 채워짐 — 도메인 매칭 입력)", "run_scoring(resume, jobs) 시그니처 불변"]
- verifier: "uv run pytest ai/worker/tests/test_prefilter.py ai/worker/tests/test_scoring_runner.py && pnpm --filter @podo/api test && pnpm --filter @podo/web test coarse_section"
