# T-014-regression-invariants

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
고정 3-JD 픽스처에 대한 제품 수준 불변식 회귀(10종)를 `ai/eval`에 이식한다. 정확한 fit 수치가 아닌 *관계 불변식*으로 GS-1 결정성·제품 규칙을 검사하고, 캐시 네임스페이스를 격리한다 (SPEC §10-1).

## 2. 작업 범위
- 고정 픽스처(Frontend / Android device SWE / Content Marketer 인턴) 로드 + 파이프라인(T-011) 실행(격리 캐시 네임스페이스).
- 불변식 10종 검사(SPEC §10-1): Frontend #1·fit≥4, Android<Frontend·fit≤3·<Frontend fit, Marketing 최하위·fit≤2, mismatch 가드, 추출형 인용 재검(`_is_extractive`), pairwise 불일치 보고 but top 불변.

## 3. 구현 항목
- `ai/eval/regression.py` — `check_invariants(ranking, tables, pairwise, resume)` 10종 + 픽스처 로더 + 캐시 네임스페이스 격리(`fixture` — 일반 재계산이 골든을 흔들지 않게).
- `ai/eval/fixtures/original_3_jds.json` — 고정 픽스처(합성/공개 데이터, 합성 표기).
- 추출형 재검은 `ai/worker/verify_matches._is_extractive`/`_build_haystack` 재사용.

## 4. 제외 항목
- 멀티-페르소나(T-015) · 골든 페어(T-016) · 스코어링 변경.

## 4-1. 변경 예정 파일/경로
- `ai/eval/regression.py`, `ai/eval/fixtures/original_3_jds.json`, `ai/eval/tests/test_regression.py`

## 5. 완료 조건
고정 픽스처에서 10종 불변식이 통과하고, 픽스처 캐시가 일반 캐시와 격리된다.

## 6. Acceptance Criteria
- AC-1 [Given] 고정 픽스처 산출물(또는 합성 fixture ranking/tables/pairwise) [When] `check_invariants` [Then] 10종 불변식(Frontend #1·fit≥4, Android<Frontend·fit≤3·<FE, Marketing 최하·fit≤2, mismatch 가드, 추출형, pairwise 불일치 top 불변)이 모두 통과한다.
- AC-2 [Given] 회귀 실행 [When] 캐시 사용 [Then] `fixture` 네임스페이스를 사용해 일반 재계산(`--refresh-cache`)이 회귀 골든 캐시를 변경하지 않는다.
- AC-3 [Given] mismatch 역할이 non-mismatch 위로 온 (오염된) 산출물 [When] `check_invariants` [Then] 가드 불변식이 실패로 검출된다(false negative 방지).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/eval/tests/test_regression.py::test_AC_1_ten_invariants_pass
- AC-2 → pytest::ai/eval/tests/test_regression.py::test_AC_2_fixture_cache_isolation
- AC-3 → pytest::ai/eval/tests/test_regression.py::test_AC_3_guard_violation_detected

## 6-2. TDD opt-out
<!-- TDD 적용 — 합성 산출물 fixture로 결정적 검사. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-004-eval-harness](../features/F-004-eval-harness.md)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §10-1](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
회귀 철학(SPEC §10-1): 절대 fit 수치가 아닌 *관계* 불변식 — 프롬프트/스키마 개선으로 fit이 정당히 변동돼도 관계가 유지되면 통과.

## 9. 의존성
- depends_on: [T-011]
- read_set: ["ai/worker/**", "ai/core/models.py"]
- write_set: ["ai/eval/regression.py", "ai/eval/fixtures/original_3_jds.json", "ai/eval/tests/test_regression.py"]
- verifier: "uv run pytest ai/eval/tests/test_regression.py"
