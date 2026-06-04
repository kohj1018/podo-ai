# T-016-golden-pairs

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
골든 페어(사람 라벨) 정확도 + GS-1/GS-2 게이트 측정 + 스코어링 ablation(`rescore_persona`)을 `ai/eval`에 이식한다. LLM 호출 없이 저장 산출물만 읽는 외부 정답 기반 정확도 (SPEC §10-3).

## 2. 작업 범위
- `propose_pairs`(하드 케이스 자동 추출, 라벨 X) / `load_pairs`(라벨 검증, 빈 라벨 분리, A=기본모드 상위 규약, LABELS·CATEGORIES) / `evaluate_pairs` / `aggregate_metrics`(strict pairwise + tie-aware + 페르소나/난이도/카테고리별 + 모드 불일치 + 시스템≠사람).
- `rescore_persona(eval_root, persona, scoring_mode)`: 저장 산출물만으로 compute_fit 재계산 + **실제 aggregate() 재사용** → LLM 없이 ablation(baseline | dedup_required_preferred).
- GS-1(N회 캐시 hit 변동 0 / miss top-k 변동 0) + GS-2(표본 ≥30 hallucinated requirement ≤2%) 측정 경로.

## 3. 구현 항목
- `ai/eval/golden_pairs.py` — propose/load/evaluate/aggregate_metrics/rescore_persona + 산출물 reader(`_read_json`, unavailable 처리 — 재수집 X).
- `ai/eval/gates.py` — GS-1 결정성(N=10 반복 hit/miss) + GS-2 사실성(근거 vs JD 원문 span) 측정 + 판정.

## 4. 제외 항목
- 회귀(T-014) · 페르소나 진단(T-015) · dedup 기본 승격(실험 유지) · A-3 τ 1회 실행(T-017).

## 4-1. 변경 예정 파일/경로
- `ai/eval/golden_pairs.py`, `ai/eval/gates.py`, `ai/eval/tests/test_golden_pairs.py`

## 5. 완료 조건
골든 페어 strict/tie-aware 정확도가 모드별로 산출되고, rescore가 LLM 없이 ablation하며, GS-1·GS-2 게이트가 측정·판정된다.

## 6. Acceptance Criteria
- AC-1 [Given] 라벨된 골든 페어 + 저장 산출물 [When] `aggregate_metrics` [Then] strict pairwise(분모 A_better/B_better)와 tie-aware 정확도가 모드별로 산출되고, 산출물에 없는 공고는 unavailable(재수집 X)로 처리된다.
- AC-2 [Given] 표본 공고 ≥30의 매칭표·JD 원문 [When] GS-2 측정 [Then] 표시 근거 중 JD 원문에 실재하지 않는 요구 비율을 산출하고 ≤2% 게이트를 판정한다.
- AC-3 [Given] 동일 (이력서, JD) [When] N=10회 (a)캐시 hit (b)miss 재계산 [Then] (a) 점수 변동 0, (b) 상위 fit top-k 순서 변동 0을 측정·판정한다(GS-1).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/eval/tests/test_golden_pairs.py::test_AC_1_strict_and_tie_aware_metrics
- AC-2 → pytest::ai/eval/tests/test_golden_pairs.py::test_AC_2_gs2_factuality_gate
- AC-3 → pytest::ai/eval/tests/test_golden_pairs.py::test_AC_3_gs1_determinism_gate

## 6-2. TDD opt-out
<!-- TDD 적용 — 저장 산출물 fixture로 결정적. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md) (§5 게이트 실증)
- Feature: [F-004-eval-harness](../features/F-004-eval-harness.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§6 GS-1·GS-2·GS-3)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §10-3·§10-4](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
`rescore_persona`는 실제 aggregate() 재사용 — 랭킹 로직 100% 동일, fit만 변경(ablation 충실성). dedup 승격 4조건 미충족 시 실험 유지(SPEC §10-4).

## 9. 의존성
- depends_on: [T-011]
- read_set: ["ai/worker/**", "ai/core/models.py"]
- write_set: ["ai/eval/golden_pairs.py", "ai/eval/gates.py", "ai/eval/tests/test_golden_pairs.py"]
- verifier: "uv run pytest ai/eval/tests/test_golden_pairs.py"
