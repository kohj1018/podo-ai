# T-009-listwise

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
listwise 재랭킹(단계 7)을 `ai/worker`에 이식한다: 압축 매칭표만 LLM에 전달 + 누락/중복 보정(재질의 1회 + fit/domain 기준 안전 배치) (SPEC §7-3).

## 2. 작업 범위
- `compress_table(table, ctx)`: type별 매칭 카운트 + strong + core_prerequisite_gaps + preferred_technical_gaps + behavioral_gaps + product_duty_gaps_not_blocking + invalid + risks(원문 미포함).
- `listwise_rank(tables, domain_ctx, fits)`: 프롬프트 `listwise_rerank` 호출 → 중복 제거 + 누락 시 재질의 1회 → 여전히 누락이면 `key=(fit_level, DOM_RANK)`로 안전 위치 삽입(맨끝 append 금지).

## 3. 구현 항목
- `ai/worker/src/worker/rerank_listwise.py` — `compress_table`, `listwise_rank`, `_ask_listwise`(validate: ranking 리스트·중복/누락 검출), warnings 수집.

## 4. 제외 항목
- pairwise(T-010) · aggregate(T-008) · 프롬프트 작성(T-005).

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/rerank_listwise.py`, `ai/worker/tests/test_listwise.py`

## 5. 완료 조건
listwise가 모든 job_id를 정확히 한 번씩 포함하도록 보정하고, 누락분을 fit/domain 기준으로 안전 배치한다.

## 6. Acceptance Criteria
- AC-1 [Given] LLM이 일부 job_id를 중복·일부를 누락한 응답, 재질의도 누락 잔존 [When] `listwise_rank` [Then] 결과 ranking은 모든 입력 job_id를 정확히 한 번씩 포함하고 warnings에 누락/중복이 기록된다.
- AC-2 [Given] 재질의 후에도 누락된 job_id [When] 안전 배치 [Then] `(fit_level, DOM_RANK)` 기준으로 적절 위치에 삽입된다(맨끝 blind append 아님).
- AC-3 [Given] 매칭표 [When] `compress_table` [Then] JD/이력서 원문 없이 카운트·strong·core/preferred/behavioral gaps·product_duty·invalid·risks 요약만 포함한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_listwise.py::test_AC_1_no_omission_no_duplicate
- AC-2 → pytest::ai/worker/tests/test_listwise.py::test_AC_2_fit_aware_placement
- AC-3 → pytest::ai/worker/tests/test_listwise.py::test_AC_3_compress_no_raw_text

## 6-2. TDD opt-out
<!-- TDD 적용 — LLM fake 주입. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-003-relative-ranking](../features/F-003-relative-ranking.md)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §7-3](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
- repair-workitem 2026-06-05 P0 ruff-format: Adopt — format hook가 2파일 자동 정렬, pnpm validate green
- repair-workitem 2026-06-05 P0 E501x4: Adopt — impl 79/85/159/250 ruff format 자동 줄바꿈으로 해소
- repair-workitem 2026-06-05 P0 F401: Adopt — test_listwise.py `import pytest` 미사용 제거
- repair-workitem 2026-06-05 P0 F841: Adopt — test `warnings_str` dead 변수 제거(assert는 warnings 직접 사용)
- repair-workitem 2026-06-05 P1 dom-rank-dup: Adopt — _DOM_RANK 중복 상수 제거, rank_aggregate.DOM_RANK를 SSOT로 import(무음 drift→GS-1 회귀 차단) (REV-M1-002, /stabilize-milestone)
- repair-workitem 2026-06-05 P1 extract-json-dup: Reject-context(defer) — _extract_json 3중복 추출은 worker shared-util 경계 ADR 후보→architect 결정(IMPROVEMENT_GUIDE §4) (REV-M1-001)

## 9. 의존성
- depends_on: [T-005]
- read_set: ["ai/core/src/core/models.py", "ai/worker/src/worker/prompts/listwise_rerank.md", "ai/worker/src/worker/llm.py"]
- write_set: ["ai/worker/src/worker/rerank_listwise.py", "ai/worker/tests/test_listwise.py"]
- verifier: "uv run pytest ai/worker/tests/test_listwise.py"
