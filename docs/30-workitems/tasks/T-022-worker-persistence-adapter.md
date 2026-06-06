# T-022-worker-persistence-adapter

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
worker가 DB에서 `job_postings`+seed 이력서를 읽고, `run_scoring` 산출을 `ranking_runs.result`(verbatim JSONB) + `recommendations`(scalar feed projection)에 영속하는 어댑터를 만든다. 기존 `cache.py` `CacheAdapter` seam 위에 Postgres 어댑터. **GS-1(결정론)은 DB 경로를 통과해도 보존**(cross-LLM P0/P1 회수: recommendations·복합키).

## 2. 작업 범위
- worker 영속 어댑터: `job_postings`·`resumes` read, `ranking_runs`+`recommendations` write(자기 소유만, §3-2 규칙1).
- `recommendations` 도출: `run_scoring`의 `final_ranking.ranking[]`에서 `rank_position`(순서)·`fit_level`·`domain_alignment`·`status`(scored|held).
- `ranking_runs` upsert: 복합키 `(resume_id, job_set_hash, model, prompt_version, scoring_mode, ranking_mode, cache_key_version)`.
- GS-1-through-DB 라운드트립 테스트.

## 3. 구현 항목
1. `ai/worker/src/worker/persistence.py` — 현재: 없음 → 변경: `load_jobs(db) -> list` (job_postings read), `persist_run(db, resume, jobs, result) -> run_id`. `result`(run_scoring 산출)를 `ranking_runs.result`에 **verbatim JSONB**로 저장(파싱·변형 금지, §3-2 규칙3) + 복합키 upsert. → 확인: 신규 `test_persistence.py`가 upsert+재upsert 시 1행 유지. (AC-1)
2. `persistence.py` — `recommendations` 도출 (**scored + held 둘 다** — cross-LLM P0 회수: held는 `pending_job_ids`에 있고 `ranking`엔 없음, pipeline.py:379/report.py:52):
   - scored: `for i, fr in enumerate(result["final_ranking"]["ranking"]): row(run_id, job_posting_id=fr["job_id"], rank_position=i, fit_level=fr["fit_level"], domain_alignment=fr["domain_alignment"], status="scored")`.
   - held: `for k, jid in enumerate(result["pending_job_ids"]): row(run_id, job_posting_id=jid, rank_position=len(ranking)+k, fit_level=None, domain_alignment=None, status="held")` (보류 — fit_level NULL, scored 뒤 배치).
   → 확인: projection 행수 = `len(ranking)+len(pending_job_ids)`, scored 순서 보존 + held가 뒤에 fit_level NULL. (AC-1·AC-3)
3. `ai/worker/src/worker/cache.py` — 현재: `CacheAdapter` 인터페이스 + `make_key` → 변경: Postgres `CacheAdapter` 구현 추가(키 *개념* 불변 — `make_key` 바이트 동일, 시간/랜덤/env 혼입 0). → 확인: `make_key` 산출이 변경 전후 동일(기존 cache 테스트 green). (AC-2)
4. GS-1-through-DB — 동일 (resume, jobs) 2회 `persist_run` → 저장된 `result` JSONB 바이트 동일 + `recommendations` 순서 동일. → 확인: 라운드트립 테스트. (AC-2)
5. LLM miss 보류(`held`) → `recommendations.status='held'` + `result`에 보류 보존(가짜 점수 X). → 확인: held fixture 테스트. (AC-3)

## 4. 제외 항목
- worker 실행 진입점(T-023) · crawler 영속(T-024) · API 서빙(T-026) · vector 검색.

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/persistence.py`, `ai/worker/src/worker/cache.py`, `ai/worker/tests/test_persistence.py`

## 5. 완료 조건
worker가 DB jobs로 run_scoring 결과를 `ranking_runs`+`recommendations`에 영속하고, 동일 입력 2회 시 바이트 동일하며, 보류가 보존된다.

## 6. Acceptance Criteria
- AC-1 [Given] DB `job_postings` + resume + `run_scoring` 산출(일부 `pending_job_ids` 포함) [When] `persist_run` [Then] `ranking_runs`에 result JSONB가 verbatim 저장되고(복합키 upsert — 재실행 시 1행), `recommendations`가 `final_ranking` 순서대로 scored 행(`rank_position`/`fit_level`/`status='scored'`) + `pending_job_ids`마다 held 행(`fit_level`=NULL·`status='held'`·scored 뒤 `rank_position`)으로 영속된다.
- AC-2 [Given] 동일 (resume, jobs) + 웜 캐시 [When] `persist_run` 2회 [Then] 저장된 `result` JSONB가 바이트 동일하고 `recommendations` 순서가 동일하다(GS-1-through-DB). worker는 `ranking_runs`/`recommendations`에만 write한다.
- AC-3 [Given] LLM miss로 `pending_job_ids`에 들어간 공고 [When] `persist_run` [Then] `recommendations`에 `status='held'`·`fit_level`=NULL 행이 생성되고 `result.pending_job_ids`에 보존되며 가짜 `fit_level`/점수가 없다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_persistence.py::test_AC_1_upsert_ranking_and_recommendations
- AC-2 → pytest::ai/worker/tests/test_persistence.py::test_AC_2_gs1_through_db_byte_identical
- AC-3 → pytest::ai/worker/tests/test_persistence.py::test_AC_3_held_status_preserved

## 6-2. TDD opt-out
<!-- TDD 적용 — DB는 docker compose PG, run_scoring 산출은 fixture. -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-007-worker-persistence](../features/F-007-worker-persistence.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-1 결정론, §3-2 규칙1·3)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §8·§11](../../20-system/SCORING_PIPELINE_SPEC.md)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) (D3) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-CONTRACT)

## 8. 메모
- 해석 확정: `recommendations` 도출 = cross-LLM P0(M2-repair-1). upsert 복합키 = M2-repair-5. result는 verbatim(파싱 금지).
- repair-plan 2026-06-06 [default] P0 Plan-FAC-coverage: Adopt-modified — held projection을 `pending_job_ids`에서 생성(fit_level NULL, scored 뒤). ranking-only 도출은 held 누락 결함이었음.

## 9. 의존성
- depends_on: [T-020, T-021]
- read_set: ["ai/worker/src/worker/pipeline.py", "ai/worker/src/worker/cache.py"]
- write_set: ["ai/worker/src/worker/persistence.py", "ai/worker/src/worker/cache.py", "ai/worker/tests/test_persistence.py"]
- assumptions: ["T-020 마이그레이션 DB", "T-021 core.db 가용"]
- verifier: "uv run pytest ai/worker/tests/test_persistence.py"
