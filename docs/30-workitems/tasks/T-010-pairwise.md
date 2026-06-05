# T-010-pairwise

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
pairwise 비교(단계 9)를 `ai/worker`에 이식한다: 후보 쌍을 A/B·B/A 양방향 비교, 양방향 일치(agreed)일 때만 outcome 확정(순서 편향 차단) (SPEC §7-4).

## 2. 작업 범위
- `run_pairwise(tables, candidate_ids, domain_ctx)`: 압축표 기반 모든 후보 쌍 A/B + B/A 비교(`pairwise_compare` 프롬프트) → agreed면 outcome=공통 승자(confidence=min), 불일치면 outcome=tie/low.

## 3. 구현 항목
- `ai/worker/src/worker/compare_pairwise.py` — `_compare_once`(winner a/b/tie clamp) + `run_pairwise`(A/B·B/A, agreed 판정, PairwiseResult 조립). `compress_table`은 T-009에서 재사용(import).

## 4. 제외 항목
- 후보 집합 *구성* 로직(T-011 오케스트레이션이 후보 ids 결정) · BT 집계(T-008) · 프롬프트 작성(T-005).

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/compare_pairwise.py`, `ai/worker/tests/test_pairwise.py`

## 5. 완료 조건
각 후보 쌍이 양방향 비교되고, 순서 불일치는 tie/low로 처리되어 순서 편향이 제거된다.

## 6. Acceptance Criteria
- AC-1 [Given] 두 후보 a,b [When] `run_pairwise([a,b])` [Then] A/B와 B/A 두 비교가 수행되고 양방향 승자가 같으면 outcome=그 승자, agreed=True가 된다.
- AC-2 [Given] A/B는 a 승, B/A는 b 승(불일치) [When] run_pairwise [Then] outcome="tie"·confidence="low"·agreed=False로 기록된다(순서 편향 차단).
- AC-3 [Given] 후보 3개 [When] run_pairwise [Then] 모든 (i<j) 쌍에 대해 결과가 생성된다(누락 없음).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_pairwise.py::test_AC_1_agreed_outcome
- AC-2 → pytest::ai/worker/tests/test_pairwise.py::test_AC_2_disagreement_is_tie
- AC-3 → pytest::ai/worker/tests/test_pairwise.py::test_AC_3_all_pairs_covered

## 6-2. TDD opt-out
<!-- TDD 적용 — LLM fake 주입. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-003-relative-ranking](../features/F-003-relative-ranking.md)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §7-4](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모

## 9. 의존성
- depends_on: [T-005, T-009]
- read_set: ["ai/core/src/core/models.py", "ai/worker/src/worker/prompts/pairwise_compare.md", "ai/worker/src/worker/rerank_listwise.py", "ai/worker/src/worker/llm.py"]
- write_set: ["ai/worker/src/worker/compare_pairwise.py", "ai/worker/tests/test_pairwise.py"]
- verifier: "uv run pytest ai/worker/tests/test_pairwise.py"
