# T-007-verify-matches

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
신뢰 레이어(단계 5)를 `ai/worker`에 이식한다: 결정적 추출형 체크(비추출 인용 제거 + invalid 강등) + 보수적 LLM verifier(강등만). GS-2 사실성의 2차 보증 — 절대 생략 금지 (SPEC §6-2).

## 2. 작업 범위
- `_extractive_pass`: 모든 evidence_quote가 이력서 텍스트/evidence 정규화본에 substring 실재 검증. 비추출 제거. 지지 주장했으나 추출 인용 0 → invalid_match + match_level 강등 + confidence=low.
- `_llm_verify`(프롬프트 `match_verifier`) + `_apply_verifier`: severity 낮추기만(min), downgrade/exaggerated면 -1, confidence는 낮은 쪽, missing이면 low.

## 3. 구현 항목
- `ai/worker/src/worker/verify_matches.py` — `verify_table` = `_extractive_pass` → `_llm_verify`. `_norm`/`_build_haystack`/`_is_extractive`(불변식 회귀 T-014도 재사용). `MAX_RESUME_CHARS=9000`.

## 4. 제외 항목
- 매칭/rematch(T-006) · compute_fit(T-003) · listwise/pairwise(T-009·T-010).

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/verify_matches.py`, `ai/worker/tests/test_verify.py`

## 5. 완료 조건
비추출 인용이 제거되고 근거 없는 주장 행이 invalid로 강등되며, verifier가 레벨을 낮추기만 한다.

## 6. Acceptance Criteria
- AC-1 [Given] 이력서에 존재하지 않는 인용을 가진 (지지 주장) 행 [When] `verify_table` [Then] 비추출 인용이 제거되고 행은 `invalid_match=True`·match_level 강등(direct/adjacent→weak, weak→missing)·confidence=low가 된다.
- AC-2 [Given] verifier가 match_level을 올리려는(direct로) 응답 [When] `_apply_verifier` [Then] 레벨은 절대 올라가지 않고(min severity) 유지/강등만 된다.
- AC-3 [Given] 추출 가능한 verbatim 인용을 가진 정상 행 [When] `verify_table` [Then] extractive_ok=True로 유지되고 invalid 처리되지 않는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_verify.py::test_AC_1_non_extractive_invalidated
- AC-2 → pytest::ai/worker/tests/test_verify.py::test_AC_2_verifier_only_lowers
- AC-3 → pytest::ai/worker/tests/test_verify.py::test_AC_3_extractive_kept

## 6-2. TDD opt-out
<!-- TDD 적용 — verifier LLM fake 주입, 추출형 체크는 결정적. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-001-core-value](../features/F-001-core-value.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-1 grounding 규칙)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §6-2](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
`_is_extractive`/`_build_haystack`는 불변식 회귀(T-014)가 import해 재검 — 공개 심볼로 둔다.

## 9. 의존성
- depends_on: [T-006]
- read_set: ["ai/core/src/core/models.py", "ai/worker/src/worker/prompts/match_verifier.md", "ai/worker/src/worker/llm.py"]
- write_set: ["ai/worker/src/worker/verify_matches.py", "ai/worker/tests/test_verify.py"]
- verifier: "uv run pytest ai/worker/tests/test_verify.py"
