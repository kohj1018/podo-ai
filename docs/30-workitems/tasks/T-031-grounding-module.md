# T-031-grounding-module

## 0. Status
done

## 0-1. Type
refactor

## 1. 작업 목적
ADR-103 집행 — worker grounding 원시 연산(`_build_haystack`·`_is_extractive`)을 공개 `worker/grounding.py` 모듈로 승격하고, eval이 worker private 대신 이 공개 모듈만 의존하게 한다. 외부 행동 불변, eval 무음 브레이킹 차단(GS-2 1급 계약 명시화).

## 2. 작업 범위
- `worker/grounding.py` 신설: `build_haystack`·`is_extractive` 공개(현 `verify_matches._build_haystack`·`_is_extractive` 이전).
- `verify_matches.py`가 `worker.grounding`을 내부 사용.
- `ai/eval`(`regression.py`·`eval_resumes.py`) import을 `worker.verify_matches._*` → `worker.grounding.*`로 교체.

## 3. 구현 항목
1. `ai/worker/src/worker/grounding.py` — 현재: 없음 → 변경: `verify_matches.py`의 `_build_haystack`·`_is_extractive` 본문을 `def build_haystack(...)`·`def is_extractive(...)` 공개로 이전. → 확인: 신규 `test_grounding.py`가 haystack 구성·추출성 판정 통과. (AC-1)
2. `ai/worker/src/worker/verify_matches.py:_build_haystack/_is_extractive` — 현재: 로컬 private 정의 → 변경: 삭제 + `from worker.grounding import build_haystack, is_extractive`, 내부 호출 교체. → 확인: `uv run pytest ai/worker/tests/test_verify_matches.py` green(행동 동일). (AC-1)
3. `ai/eval/src/eval/regression.py:21` — 현재: `from worker.verify_matches import _build_haystack, _is_extractive`(private) → 변경: `from worker.grounding import build_haystack, is_extractive`, 호출부 교체. → 확인: `grep -rn "verify_matches import _" ai/eval/` 결과 0. (AC-2)
4. `ai/eval/src/eval/eval_resumes.py:23` — 현재: 동일 private import → 변경: `worker.grounding` 공개 import로 교체. → 확인: `uv run pytest ai/eval/tests/` green. (AC-2)
5. 변경 파일에 `# per ADR-103` 역참조 주석 부착. → 확인: `uv run pytest && ruff check && mypy --strict` exit 0(순환 없음 — grounding은 leaf). (AC-2)

## 4. 제외 항목
- 동작 변경·새 기능. · grounding *로직* 수정(GS-2 판정 규칙 불변). · util 중앙화(T-030). · ARCH §3-2 문서 1줄 명문화(별도/후속 — 본 task는 코드만).

## 4-1. 변경 예정 파일/경로
- 신규: `ai/worker/src/worker/grounding.py`, `ai/worker/tests/test_grounding.py`
- 편집: `ai/worker/src/worker/verify_matches.py`, `ai/eval/src/eval/regression.py`, `ai/eval/src/eval/eval_resumes.py`, `ai/worker/tests/test_verify.py`, `ai/eval/tests/test_regression.py`

## 5. 완료 조건
grounding 원시 연산이 공개 모듈로 모이고, eval이 worker private을 전혀 import하지 않으며, 전체 validate가 행동 변화 없이 green이다.

## 6. Acceptance Criteria
- AC-1 [Given] 기존 grounding 동작(haystack 구성·추출성 판정) [When] `worker.grounding` 공개 모듈로 이전 후 pytest [Then] `verify_matches` 관련 테스트가 행동 동일하게 green이고 `_build_haystack`/`_is_extractive` private 정의가 0개다.
- AC-2 [Given] eval이 worker grounding을 사용 [When] import을 `worker.grounding`으로 교체 후 `pytest && mypy --strict` [Then] exit 0이고, `ai/eval`에서 `worker.*._`(private) import가 0건이다(grep 검증).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_grounding.py::test_AC_1_public_grounding_behavior_preserved
- AC-2 → pytest::ai/eval/tests/test_regression.py::test_AC_2_eval_uses_public_grounding

## 6-2. TDD opt-out
<!-- TDD 적용 — refactor라 기존 verify_matches/eval 테스트가 행동 불변 oracle. -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-011-worker-boundary-hardening](../features/F-011-worker-boundary-hardening.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-1 grounding 경계, §3-2 eval→worker 의존)
- ADR: [ADR-103](../../90-decisions/project/ADR-103-eval-worker-boundary.md) · [ADR-006](../../90-decisions/boilerplate/ADR-006-simplicity-and-architecture.md)

## 8. 메모
- 해석 확정: AC-1 = `build_haystack`/`is_extractive`를 grounding으로 *이전*(re-export 아님) — verify_matches가 grounding을 import해 사용(ADR-103 D2).
- repair-workitem 2026-06-06 P0 [F821-eval-callsite]: Adopt — eval_resumes.py:120/125 호출부가 private `_build_haystack`/`_is_extractive` 잔존(import만 교체됨) → public 호출로 교체.
- repair-workitem 2026-06-06 P0 [F821-EvidenceItem]: Adopt — verify_matches.py가 헬퍼 삭제 시 `EvidenceItem` import까지 제거했으나 L203 signature에서 사용 → import 복원.
- repair-workitem 2026-06-06 P1 [verify-test-missing]: Adopt — §6-1 지정 test_AC_2_eval_uses_public_grounding를 test_regression.py에 추가(eval src AST 스캔=worker private import 0 + 공개 API 호출가능).

## 9. 의존성
- depends_on: [T-030]   # verify_matches.py를 T-030(prompts)·본 task(grounding) 둘 다 편집 → write_set 교집합, 같은 wave 금지(순차)
- read_set: ["ai/worker/src/worker/verify_matches.py", "ai/eval/src/eval/**"]
- write_set: ["ai/worker/src/worker/grounding.py", "ai/worker/src/worker/verify_matches.py", "ai/eval/src/eval/regression.py", "ai/eval/src/eval/eval_resumes.py", "ai/worker/tests/test_grounding.py"]
- verifier: "uv run pytest ai/worker/tests/ ai/eval/tests/"
