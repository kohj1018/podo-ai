# T-015-multi-persona-diagnostic

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
4개 합성 페르소나로 방향성 일반화 진단을 `ai/eval`에 이식한다(정확도 아님): 페르소나별 도메인 프로파일을 주입해 6 방향성 불변식 + (선택) 3 모드 ablation을 검사 (SPEC §10-2).

## 2. 작업 범위
- 4 합성 페르소나(backend_platform/junior_frontend/ai_ml_application/devops_infra_security) + 도메인 프로파일(SPEC §10-2 표) 주입(`USER_PRIMARY/SECONDARY_DOMAINS` override).
- 6 방향성 불변식: extractive(fail)·fit_scale(1~5 정수·% 금지, fail)·mismatch_priority(fail)·expected_top_in_top3(warn/na)·domain_order(warn/na)·primary_domain_available(warn/na).
- `--compare-ranking-modes`: 3 모드 실행 → `ranking_mode_comparison`(fit_rank/tier inversions, mismatch_violation).

## 3. 구현 항목
- `ai/eval/src/eval/eval_resumes.py` — 페르소나 로더(`expected_behavior` 동등) + 도메인 주입 + `diagnose`(6 불변식) + 모드 비교.
- `ai/eval/src/eval/fixtures/personas/*` — 합성 이력서 + expected_behavior(합성 표기, 실제 데이터 비덮어쓰기).

## 4. 제외 항목
- 불변식 회귀(T-014) · 골든 페어(T-016) · 스코어링 변경.

## 4-1. 변경 예정 파일/경로
- `ai/eval/src/eval/eval_resumes.py`, `ai/eval/src/eval/fixtures/personas/`, `ai/eval/tests/test_eval_resumes.py`

## 5. 완료 조건
4 페르소나에 도메인 프로파일이 주입되어 방향성 불변식이 검사되고, 모드 비교가 산출된다.

## 6. Acceptance Criteria
- AC-1 [Given] backend_platform 페르소나(primary=backend) [When] 도메인 주입 후 진단 [Then] `domain_alignment`가 backend 역할에 strong으로 산출되고 mismatch_priority·fit_scale·extractive 불변식이 통과한다.
- AC-2 [Given] 4 페르소나 산출물 [When] `diagnose` [Then] 각 페르소나에 6 불변식 결과(severity: fail/warning/na)가 리포트되고 fail이 0이면 pass다.
- AC-3 [Given] `--compare-ranking-modes` [When] 3 모드 실행 [Then] `ranking_mode_comparison`에 모드별 fit_rank_inversions·tier_inversions·mismatch_violation(=0이어야 함)이 기록된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/eval/tests/test_eval_resumes.py::test_AC_1_persona_domain_injection
- AC-2 → pytest::ai/eval/tests/test_eval_resumes.py::test_AC_2_six_directional_invariants
- AC-3 → pytest::ai/eval/tests/test_eval_resumes.py::test_AC_3_mode_comparison

## 6-2. TDD opt-out
<!-- TDD 적용 — 합성 페르소나 + LLM fake/캐시. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-004-eval-harness](../features/F-004-eval-harness.md)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §10-2](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
방향성(일관성) 검사 — *정확도*는 골든 페어(T-016)가 본다.

- repair-workitem 2026-06-05 P0 missing-module: Adopt — eval_resumes.py 신규 작성(PERSONAS/diagnose 6불변식/compare_ranking_modes), aggregate 3모드 재사용
- repair-workitem 2026-06-05 P0 integration-fail: Adopt — 모듈+lint 수정 후 verify.mjs exit 0 (83 passed/1 skipped)
- repair-workitem 2026-06-05 P0 ac-untested: Adopt — AC-1/2/3 verifier 3/3 PASS
- repair-workitem 2026-06-05 P1 test-lint: Adopt — 미사용 import(DiagnosticResult/InvariantEntry) 제거 + I001 정렬(ruff)
- repair-workitem 2026-06-05 P1 builder-partial-noop: Adopt-modified — 메인 세션 직접 구현으로 해소(read_set 미축소, 메인 세션은 대형 읽기에 안 죽음)
- 설계 결정: domain_alignment=rank1 역할의 alignment / 도메인 주입=persona 프로파일이 진단 파라미터(전역 config USER_DOMAINS 부재 — worker 미보유). 모드 비교는 fixture로 aggregate 입력 재구성 후 3모드 실행(LLM 미호출).

## 9. 의존성
- depends_on: [T-011]
- read_set: ["ai/worker/**", "ai/core/src/core/models.py"]
- write_set: ["ai/eval/src/eval/eval_resumes.py", "ai/eval/src/eval/fixtures/personas/**", "ai/eval/tests/test_eval_resumes.py"]
- verifier: "uv run pytest ai/eval/tests/test_eval_resumes.py"
