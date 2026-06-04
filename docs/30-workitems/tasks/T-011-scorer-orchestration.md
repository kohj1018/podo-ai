# T-011-scorer-orchestration

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
Scorer 파이프라인 단계 1~12를 하나의 결정적 오케스트레이션으로 묶고(`ai/worker` 진입점), 산출물 계약(JSONB `ranking_runs.result` + 리포트 필드)을 만든다. compute_fit 1회 공유 + pairwise 후보 집합 + miss 실패 시 보류 (SPEC §2·§7-4·§11·§12).

## 2. 작업 범위
- 단계 시퀀스: 추출(T-005) → JD 구조화(T-005) → 도메인 정렬(T-003) → 매칭(T-006) → 검증(T-007) → **compute_fit 1회**(T-003) → listwise(T-009) → pairwise 후보 집합 구성 → pairwise(T-010) → BT/aggregate(T-008) → 리포트/JSON.
- pairwise 후보 집합(결정적, SPEC §7-4 `_build_pairwise_candidates` **그대로 이식**): 4단 누적 포함 — ① listwise top-K(`TOP_K_PAIRWISE=5`) ② fit≥4(엔지니어링 한정) ③ strong frontend/fullstack 구제(fit > 집합 최약) ④ strong-domain catch-all 구제(더 낮은-fit adjacent/weak가 비교될 때). 상한 `MAX_PAIRWISE_CANDIDATES=8`(bound 정렬 `(-fit,-DOM_RANK,listwise_rank)`). 산출 `pairwise_info{pairwise_candidate_set, rescued_strong_domain, strong_domain_excluded}`.
- 산출물: `final_ranking`(note "fit≠합격확률" + user_profile + guard_moves + ranking[FitResult]), `matching_tables`, `pairwise_comparisons`(BT + candidate_set + comparisons). ARCH §3-2 JSONB pass-through 계약(NestJS는 파싱 안 함).
- miss LLM 실패 시 **가짜 점수 금지, 보류 상태**(FAC-5 / Charter §7-4 보류 표현).

## 3. 구현 항목
- `ai/worker/pipeline.py`(또는 `worker/__main__.py`) — `run_scoring(resume, jobs, ranking_mode="domain_fit_bt")` 오케스트레이션 + 후보 집합 헬퍼.
- `ai/worker/report.py` — FitResult/coverage 필드 → JSONB 계약 직렬화(SPEC §12). 합격확률/% 출력 금지 + BT="상대 강도" 명시 보존.
- compute_fit 결과 dict를 listwise·pairwise 후보·aggregate에 **공유**(재계산 금지).

## 4. 제외 항목
- DB 영속(Postgres 쓰기) 구체 — 스키마 확정 후 어댑터(본 task는 JSONB dict 계약까지). · CLI 콘솔 UI(rich 버림) · 알림/피드 UI.

## 4-1. 변경 예정 파일/경로
- `ai/worker/pipeline.py`, `ai/worker/report.py`, `ai/worker/tests/test_pipeline.py`

## 5. 완료 조건
(이력서, 공고집합)에서 단계 1~12가 순서대로 돌아 최종 랭킹·근거·JSONB 산출물을 만들고, 동일 입력+캐시에 동일 출력이며, LLM 실패는 보류로 처리된다.

## 6. Acceptance Criteria
- AC-1 [Given] LLM miss 경로에서 한 공고의 호출이 실패 [When] `run_scoring` [Then] 가짜 점수를 만들지 않고 해당 공고를 보류 상태로 표시한다(전체 파이프라인은 나머지로 계속).
- AC-2 [Given] 정상 입력 [When] run_scoring → 산출물 [Then] `final_ranking`에 note(fit≠합격확률)·user_profile·guard_moves·ranking[FitResult], `matching_tables`(job_id→table), `pairwise_comparisons`(BT+candidate_set+comparisons)가 포함되고 합격확률/% 필드가 없다.
- AC-3 [Given] 동일 (이력서, 공고집합) + 웜 캐시 [When] run_scoring 2회 [Then] 최종 ranking 순서·fit_level이 변동 0이다(GS-1 결정성).
- AC-4 [Given] strong frontend/fullstack 공고가 listwise top-5 밖이고 더 낮은 fit의 adjacent/weak 공고가 후보집합에 있는 입력 [When] pairwise 후보집합 구성 [Then] 그 strong 공고가 구제되어 후보집합에 포함되고 `rescued_strong_domain`에 기록된다(SPEC §7-4 ③·④). 후보 수 > 8이면 `MAX_PAIRWISE_CANDIDATES=8`로 bound되고 제외분은 `strong_domain_excluded`/`[bounded out]` 사유로 남는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_pipeline.py::test_AC_1_miss_failure_holds_not_fakes
- AC-2 → pytest::ai/worker/tests/test_pipeline.py::test_AC_2_output_contract_no_percent
- AC-3 → pytest::ai/worker/tests/test_pipeline.py::test_AC_3_deterministic_on_cache_hit
- AC-4 → pytest::ai/worker/tests/test_pipeline.py::test_AC_4_strong_domain_rescue_and_bound

## 6-2. TDD opt-out
<!-- TDD 적용 — 모든 LLM 단계 fake 주입, 결정적 단계는 실제. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-001-core-value](../features/F-001-core-value.md) (+ [F-003](../features/F-003-relative-ranking.md) 통합)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 JSONB 계약, §5 스코어링 흐름)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) (JSONB pass-through), [## 7-3](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §2·§11·§12](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
이 task가 F-001·F-003을 통합하는 진입점. eval 하니스(T-014/T-016)가 본 산출물을 읽는다. AC 4개는 통합 task(6 deps 묶음)라 정당 — 추가 분해보다 진입점 1개 유지가 정합(SPEC §2 단계 시퀀스 단일 소유).

## 9. 의존성
- depends_on: [T-003, T-006, T-007, T-008, T-009, T-010]
- read_set: ["ai/worker/**", "ai/core/models.py"]
- write_set: ["ai/worker/pipeline.py", "ai/worker/report.py", "ai/worker/tests/test_pipeline.py"]
- verifier: "uv run pytest ai/worker/tests/test_pipeline.py"
