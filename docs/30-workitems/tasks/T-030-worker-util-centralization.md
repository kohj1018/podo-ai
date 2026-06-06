# T-030-worker-util-centralization

## 0. Status
done

## 0-1. Type
refactor

## 1. 작업 목적
ADR-104 집행 — worker의 중복 util `_extract_json`(3곳)·`_load_prompt`/`_render`(4곳)을 leaf 모듈 `worker/_json_util.py`·`worker/_prompts.py`로 중앙화한다. 외부 행동 불변(behavior-preserving), GS-1 무음 parsing drift 표면 제거.

## 2. 작업 범위
- `worker/_json_util.py` 신설: 단일 `extract_json()` (현 `compare_pairwise._extract_json`·`llm._extract_json`·`rerank_listwise._extract_json_raw` 통합).
- `worker/_prompts.py` 신설: `load_prompt()`·`render()` (현 `parse_resume`·`parse_job`·`verify_matches`·`matching`의 `_load_prompt`/`_render` 통합).
- 사용처 import 교체 + 로컬 정의 삭제. `DOM_RANK` 단일 출처(`rank_aggregate.DOM_RANK`) 확인(이미 정합 — 재복제 없음 검증).

## 3. 구현 항목
1. `ai/worker/src/worker/_json_util.py` — 현재: 없음 → 변경: `compare_pairwise.py:35 _extract_json`(code-fence 제거 → greedy shrink 본문)을 `def extract_json(text: str) -> Any:`로 이전. `rerank_listwise.py:153 _extract_json_raw` 변형을 동일 함수로 흡수(동작 합집합 검증). → 확인: 신규 `test_json_util.py`가 code-fence/greedy 케이스 통과. (AC-1)
2. `ai/worker/src/worker/compare_pairwise.py:35` · `llm.py:33` — 현재: 각자 `_extract_json` 정의 → 변경: 정의 삭제 + `from worker._json_util import extract_json`, 호출부 `_extract_json(` → `extract_json(`. → 확인: `uv run pytest ai/worker/tests/test_pairwise.py` green. (AC-1)
3. `ai/worker/src/worker/rerank_listwise.py:153` — 현재: `_extract_json_raw` 정의 → 변경: 삭제 + `extract_json` import·교체. → 확인: `test_listwise.py` green. (AC-1)
4. `ai/worker/src/worker/_prompts.py` — 현재: 없음 → 변경: `parse_resume.py:37 _load_prompt` + 동반 `_render`를 `def load_prompt(name)`·`def render(...)`로 이전. → 확인: 신규 `test_prompts.py`가 프롬프트 로딩/렌더 통과. (AC-2)
5. `parse_resume.py:37` · `parse_job.py:22` · `verify_matches.py:43` · `matching.py:39` — 현재: 각자 `_load_prompt`/`_render` 정의 → 변경: 삭제 + `from worker._prompts import load_prompt, render`, 호출부 교체. → 확인: `uv run pytest ai/worker/tests/` 전체 green(행동 동일). (AC-2)
6. `rank_aggregate.py:368` `DOM_RANK` — 현재: 단일 정의(SSOT) → 변경: 없음 — 다른 모듈 재선언 0 확인(grep). 주석에 `# SSOT per ADR-104` 1줄. → 확인: `grep -rn "DOM_RANK *=" ai/` 결과 1건. (AC-3)
7. 변경 파일에 `# per ADR-104` 역참조 주석 부착. → 확인: `uv run pytest && uv run ruff check . && uv run mypy ...` exit 0(순환 import 없음). (AC-3)

## 4. 제외 항목
- 동작 변경·새 기능. · `DOM_RANK` 값 변경. · grounding 모듈(T-031). · 알고리즘 로직.

## 4-1. 변경 예정 파일/경로
- 신규: `ai/worker/src/worker/_json_util.py`, `ai/worker/src/worker/_prompts.py`, `ai/worker/tests/test_json_util.py`, `ai/worker/tests/test_prompts.py`
- 편집: `ai/worker/src/worker/compare_pairwise.py`, `llm.py`, `rerank_listwise.py`, `parse_resume.py`, `parse_job.py`, `verify_matches.py`, `matching.py`, `rank_aggregate.py`

## 5. 완료 조건
중복 util이 단일 leaf 모듈로 모이고 모든 사용처가 import로 전환됐으며, 전체 validate가 행동 변화 없이 green이다.

## 6. Acceptance Criteria
- AC-1 [Given] 기존 JSON 파싱 케이스(code-fence·greedy) [When] `extract_json` 단일 함수로 교체 후 pytest [Then] `compare_pairwise`·`llm`·`rerank_listwise` 관련 테스트가 행동 동일하게 green이고, `_extract_json`/`_extract_json_raw` 정의가 0개다.
- AC-2 [Given] 기존 프롬프트 로딩/렌더 [When] `load_prompt`/`render` 단일 모듈로 교체 [Then] `parse_resume`·`parse_job`·`verify_matches`·`matching` 테스트가 green이고 `_load_prompt` 정의가 0개다.
- AC-3 [Given] 중앙화 완료 [When] `uv run pytest && ruff check && mypy --strict` [Then] exit 0이고(순환 import 없음), `DOM_RANK` 선언이 정확히 1곳(`rank_aggregate`)이다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_json_util.py::test_AC_1_extract_json_single_source_behavior
- AC-2 → pytest::ai/worker/tests/test_prompts.py::test_AC_2_load_prompt_single_source
- AC-3 → pytest::ai/worker/tests/test_pipeline.py::test_AC_3_full_suite_green_no_cycle (기존 스위트 회귀 가드)

## 6-2. TDD opt-out
<!-- TDD 적용 — refactor라 기존 테스트가 행동 불변 oracle. 신규 util은 특성 테스트 추가. -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-011-worker-boundary-hardening](../features/F-011-worker-boundary-hardening.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-1 결정론 경계)
- ADR: [ADR-104](../../90-decisions/project/ADR-104-worker-shared-util-boundary.md) · [ADR-006](../../90-decisions/boilerplate/ADR-006-simplicity-and-architecture.md)

## 8. 메모
- 변경 파일이 12개(테스트 포함)로 5-파일 sizing 휴리스틱 초과 — *단일 ADR-104의 기계적 통합*이라 분할보다 한 task 유지가 정합. **§3 단계는 json util(1-3)→검증 → prompt util(4-5)→검증 → DOM_RANK(6)→검증 → 전체 validate(7)로 게이트**된 순서(각 단계 독립 green). 사용자가 json/prompt 2-task 분할을 원하면 분할 가능.
- repair-plan 2026-06-06 [default] P1 Plan-sizing: Adopt-modified — 단일 task 유지 + 단계별 검증 순서 명시(분할 대신; 기계적 import 교체라 cohesive).
- 해석 확정: AC-1 = `_extract_json_raw`(rerank) 변형은 단일 `extract_json`이 *동작 합집합*을 커버(별 함수 유지 X).

## 9. 의존성
- (선행 없음 — scaffold 의존 0, M2 wave 1 병렬 가능)
- read_set: ["ai/worker/src/worker/**"]
- write_set: ["ai/worker/src/worker/_json_util.py", "ai/worker/src/worker/_prompts.py", "ai/worker/src/worker/compare_pairwise.py", "ai/worker/src/worker/llm.py", "ai/worker/src/worker/rerank_listwise.py", "ai/worker/src/worker/parse_resume.py", "ai/worker/src/worker/parse_job.py", "ai/worker/src/worker/verify_matches.py", "ai/worker/src/worker/matching.py", "ai/worker/src/worker/rank_aggregate.py", "ai/worker/tests/test_json_util.py", "ai/worker/tests/test_prompts.py"]
- verifier: "uv run pytest ai/worker/tests/"
