# T-023-worker-entry-seed

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
`python -m worker` 실행 진입점을 만든다 — config seed(합성) 이력서 + DB `job_postings`를 로드해 `run_scoring` 후 T-022 어댑터로 영속한다. M2 done-line(crawl→score→feed)의 score 단계.

## 2. 작업 범위
- `ai/worker/src/worker/__main__.py` 진입점: load seed resume → load jobs(DB) → `run_scoring` → `persist_run`(T-022).
- seed 이력서 주입: config(SPEC §9-4 USER_DOMAINS 방식)로 **합성** 이력서 로드(실 PII 아님).

## 3. 구현 항목
1. `ai/worker/src/worker/__main__.py` — 현재: 없음 → 변경: `main()` — `resume = load_seed_resume()`; `jobs = persistence.load_jobs(db)`; `result = run_scoring(resume, jobs, ranking_mode="domain_fit_bt")`; `persistence.persist_run(db, resume, jobs, result)`. `python -m worker` 동작. → 확인: 통합 실행 시 `ranking_runs`/`recommendations` 행 생성. (AC-1)
2. `ai/worker/src/worker/config.py` — 현재: 존재(env) → 변경: `load_seed_resume()` 추가(env/파일 JSON에서 합성 이력서, SPEC §9-4). → 확인: seed 로드 단위 테스트. (AC-1)
3. LLM miss 시 보류가 진입점을 중단시키지 않고 영속됨(T-022 AC-3 경유). → 확인: 일부 held fixture로 전체 완주. (AC-2)

## 4. 제외 항목
- 영속 어댑터 로직(T-022) · UI 이력서 업로드/실 PII(F-007 비범위) · 크론(T-025는 crawler) · API.

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/__main__.py`, `ai/worker/src/worker/config.py`, `ai/worker/tests/test_entry.py`

## 5. 완료 조건
`python -m worker`가 seed 이력서 + DB jobs로 run_scoring을 돌려 결과를 영속하고, 보류가 보존된다.

## 6. Acceptance Criteria
- AC-1 [Given] seed 이력서 config + DB `job_postings` [When] `python -m worker` [Then] `run_scoring`이 1회 실행되고 `ranking_runs`+`recommendations`에 결과가 영속된다.
- AC-2 [Given] 일부 공고가 LLM miss로 보류 [When] `python -m worker` [Then] 진입점이 중단 없이 완주하고 보류 공고가 `status='held'`로 영속된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_entry.py::test_AC_1_entry_runs_and_persists
- AC-2 → pytest::ai/worker/tests/test_entry.py::test_AC_2_held_does_not_abort_entry

## 6-2. TDD opt-out
<!-- TDD 적용 — LLM 단계 fake 주입, DB는 compose PG. -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-007-worker-persistence](../features/F-007-worker-persistence.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§5 스코어링 흐름)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §9-4](../../20-system/SCORING_PIPELINE_SPEC.md) (이력서 주입)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 8. 메모
- 해석 확정: seed 이력서 = 합성(config 주입, SPEC §9-4) — M2는 실 PII 비범위(M2 결정).
- repair-plan 2026-06-06 [default] P0 Plan-FAC-coverage: Adopt — held 공고는 T-022가 pending_job_ids로 projection 행 생성(진입점 중단 X, AC-2 정합).
- 구현 노트(2026-06-06): 메인 세션 수동(M2 task 포크 사망 패턴 확립 — T-018/019/021/022 모두 포크 불완전). entry는 `run(conn, *, call_fn...)`으로 분리(테스트는 fake 주입, main()은 실 LLM 기본).
- seed bootstrap: `_ensure_seed_resume`가 resumes에 합성 seed를 멱등 insert(content 동일 시 재사용). resumes는 §3-2상 api 소유이나 M2엔 api 업로드 경로 부재 → 진입점이 seed 1회 주입(M2 seed 편의, F-007 'UI 업로드 비범위'와 구분). 후속 api seed 경로 생기면 이관.
- 무키 경로(M2 §5): main() call_fn 기본 None → run_scoring 실 LLM. 무키 결정적 실행은 웜 캐시(.cache/llm)/fake 필요 — E2E 오케스트레이션 소관. 라이브 검증: DATABASE_URL 주입 시 3 테스트(seed/AC-1/AC-2) green.

## 9. 의존성
- depends_on: [T-022]
- read_set: ["ai/worker/src/worker/pipeline.py", "ai/worker/src/worker/persistence.py"]
- write_set: ["ai/worker/src/worker/__main__.py", "ai/worker/src/worker/config.py", "ai/worker/tests/test_entry.py"]
- verifier: "uv run pytest ai/worker/tests/test_entry.py"
