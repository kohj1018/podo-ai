# T-006-matching

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
요구↔근거 매칭표 생성(단계 4)을 `ai/worker`에 이식한다: LLM은 evidence_id만 선택하고 **코드가 인용을 verbatim 채움**(구성상 추출형 — GS-2 1차 보증) + 1회 rematch 재시도 (SPEC §6-1).

## 2. 작업 범위
- `build_matching_table(job, evidence)`: 프롬프트 `requirement_evidence_match` 호출 → 요구당 1행 보장(누락 backfill + 권위 메타데이터 덮어쓰기) → `_resolve_evidence`(존재 id만, exact_quote verbatim 복사).
- rematch 1회: `_needs_rematch`(over-claim 또는 missing/weak same-category 그룹) → `rematch_evidence` → 실패 시 invalid_match/genuine miss 표기. `GROUP_CATEGORIES` 보존.

## 3. 구현 항목
- `ai/worker/src/worker/matching.py` — `build_matching_table`, `_resolve_evidence`(id 검증 + quote/source verbatim), `_needs_rematch`, `_rematch`.
- evidence_quotes는 **항상 evidence의 exact_quote에서 복사**(LLM 작성 인용 금지 — 프롬프트가 id-only를 강제, 코드가 채움).

## 4. 제외 항목
- 추출형 재검·verifier(T-007) · compute_fit(T-003) · 프롬프트 작성(T-005).

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/matching.py`, `ai/worker/tests/test_matching.py`

## 5. 완료 조건
각 요구당 1행이 생성되고, 인용은 evidence에서 verbatim 복사되며, 유효 근거 없는 over-claim 행은 rematch 후 invalid 처리된다.

## 6. Acceptance Criteria
- AC-1 [Given] LLM이 일부 요구를 누락하고 일부에 evidence_id를 준 응답 [When] `build_matching_table` [Then] 모든 요구당 정확히 1행이 존재하고, 각 행의 evidence_quotes는 선택된 evidence의 `exact_quote`와 글자 단위로 일치한다(LLM 작성 텍스트 아님).
- AC-2 [Given] match_level=direct인데 존재하지 않는 evidence_id만 준 행 [When] resolve + rematch도 실패 [Then] 해당 행은 `match_level=missing`·`invalid_match=True`로 표기되고 risk_note가 남는다.
- AC-3 [Given] missing으로 온 critical same-category 그룹 행 [When] `_needs_rematch` [Then] rematch 대상으로 판정된다(false-negative 재확인).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_matching.py::test_AC_1_one_row_per_req_extractive_quotes
- AC-2 → pytest::ai/worker/tests/test_matching.py::test_AC_2_overclaim_becomes_invalid
- AC-3 → pytest::ai/worker/tests/test_matching.py::test_AC_3_needs_rematch_group

## 6-2. TDD opt-out
<!-- TDD 적용 — LLM fake 주입. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-001-core-value](../features/F-001-core-value.md)
- Architecture-Iface: [ARCH ## 7-3](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3) (grounding 경계)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §6-1](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
FAC-3(GS-2)·FAC-4(F7 매핑)의 핵심 — 인용 추출형 구성이 hallucination 차단 1차 레이어.

## 9. 의존성
- depends_on: [T-005]
- read_set: ["ai/core/src/core/models.py", "ai/worker/src/worker/prompts/**", "ai/worker/src/worker/llm.py"]
- write_set: ["ai/worker/src/worker/matching.py", "ai/worker/tests/test_matching.py"]
- verifier: "uv run pytest ai/worker/tests/test_matching.py"
