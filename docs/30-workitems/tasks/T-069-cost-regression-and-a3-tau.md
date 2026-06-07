# T-069-cost-regression-and-a3-tau

## 0. Status
draft

## 0-1. Type
research-spike

## 1. 작업 목적
F-021 비용 구조 전환(N→K) 전/후 LLM 비용(토큰·호출 수)을 실측 비교해 절감을 입증하고, **A-3 τ(상대 랭킹 타당도)를 실데이터로 1회 측정·판정**한다. 하니스(`ai/eval/a3_tau.py`)는 M1(T-017)에서 이미 구현·완료됐으므로 본 task는 *확대된 실데이터*로 실행하는 측정 spike다. 비용 비교는 F-021 출력 계약 불변 보존 확인도 겸한다(F-023 §3 Alternate path).

## 2. 작업 범위
- **비용 전/후 회귀 측정**: F-021 도입 전 기준선(M4 스냅샷 또는 모의 N전체 실행) vs 도입 후(K 후보 only) LLM 토큰·호출 수 비교. `ai/eval/src/eval/cost_regression.py` 신설.
- **비용 측정 하니스**: `run_scoring` 호출 시 LLM 토큰/호출 카운터 훅(기존 LLM client 또는 mock 인터셉터) → N전체 vs K 후보 비용 수치 기록.
- **A-3 τ 실데이터 1회 실행**: `ai/eval/a3_tau.py`(T-017 기구현)를 확대 표본 JD에 대해 실행. 수기 랭킹 라벨(창업자 + 가능 시 현업) 입력 → Kendall τ + 자명 페어 위반율 산출 → (진행/조건부/No-go) 판정.
- 판정 결과를 `ai/eval/reports/m5_cost_and_a3.json` + DISCOVERY §12 A-3 / §14 Evidence Log 회수 대상 명시.
- **No-go(τ<0.6) 시 대응**: 판정 기록 + 사용자에게 F5 범위 재검토 알림(자동 조치 없음 — 사용자 결정).

## 3. 구현 항목
1. `ai/eval/src/eval/cost_regression.py` — 신설. `measure_cost(scoring_fn, resumes, jd_sets_n, jd_sets_k) -> CostReport(n_tokens, k_tokens, n_calls, k_calls, ratio)`:
   - `scoring_fn`에 N전체 vs K 후보 집합을 각각 전달해 LLM 토큰/호출 수 계측(mock LLM client 인터셉터 또는 token_counter 콜백).
   - `ratio = k_tokens / n_tokens` 산출. ratio < 1.0 assert(비용 절감 실증).
   - → 확인: 단위 테스트(mock 기반) (AC-1)
2. `ai/eval/src/eval/m5_cost_runner.py` — 신설. `run_cost_regression(fixture_dir) -> CostReport`: `measure_cost()` 호출 + `ai/eval/reports/m5_cost_and_a3.json` 직렬화. → 확인: fixture 기반 실행 (AC-1, AC-2)
3. **A-3 τ 실행 스크립트** `ai/eval/run_a3_m5.py` — 신설(또는 기존 a3_tau.py CLI 확장). 확대 표본 JD·이력서에 대한 창업자 수기 랭킹 라벨(`a3_labels_m5.json`, 사용자 입력 필요) 로드 → `a3_tau.compute_tau()` 호출 → 판정 리포트 → `m5_cost_and_a3.json`에 병합. → 확인: fixture 합성 라벨로 τ 계산 단위 테스트 (AC-3)
4. 수기 라벨 placeholder `ai/eval/fixtures/m5_expanded/a3_labels_m5.json` — 신설(`{pair_id: "A_better"|"B_better"|"tie"}` 형식, 사용자 입력 대기 주석). builder가 사용자 라벨 입력 안내 README 추가.
5. `ai/eval/tests/test_cost_regression.py` — 신설. AC-1·AC-2 커버(mock LLM 인터셉터로 N>K 호출 수 비교).
6. `ai/eval/tests/test_a3_m5.py` — 신설. AC-3 커버(합성 라벨 τ 계산 + 판정 라벨 assert). → 확인: pytest pass

## 4. 제외 항목
- GS-1/GS-2 재측정 — T-068.
- 도메인 분류 정확도 측정 — T-068.
- 모델 티어링 적용(저가/고가 분리) — F-023 §5 명시 비범위, ADR-108 D7(GS-2 확인 후).
- F5 범위 재검토 자동화 — 사용자 결정 사항.

## 4-1. 변경 예정 파일/경로
- `ai/eval/src/eval/cost_regression.py` (신설)
- `ai/eval/src/eval/m5_cost_runner.py` (신설)
- `ai/eval/run_a3_m5.py` (신설)
- `ai/eval/fixtures/m5_expanded/a3_labels_m5.json` (placeholder 신설)
- `ai/eval/reports/m5_cost_and_a3.json` (산출)
- `ai/eval/tests/test_cost_regression.py` (신설)
- `ai/eval/tests/test_a3_m5.py` (신설)

## 5. 완료 조건
F-021 비용 전/후 LLM 토큰·호출 수 비교가 실측되어 절감이 입증되고, A-3 τ가 확대 표본 실데이터로 1회 측정·판정된다. 결과는 DISCOVERY §14 Evidence Log 회수 대상으로 명시된다.

## 6. Acceptance Criteria
- AC-1 [Given] 동일 이력서 + 동일 JD 집합(N개 전체 vs K 후보) [When] `measure_cost()` 실행 [Then] K 후보 경로의 LLM 토큰·호출 수가 N 전체 경로 대비 낮고(ratio < 1.0) 수치가 `m5_cost_and_a3.json`에 기록된다.
- AC-2 [Given] 비용 측정 전/후 저장 `recommendations` [When] 출력 계약 비교 [Then] fit_level·evidence·result shape이 M4 동결 계약과 동일하다(비용 최적화가 계약을 변경하지 않음).
- AC-3 [Given] 확대 표본 JD + 수기 랭킹 라벨(창업자) [When] `a3_tau.compute_tau()` 실행 [Then] Kendall τ와 자명 페어 위반율이 산출되고 (진행/조건부/No-go) 판정 라벨이 `m5_cost_and_a3.json`에 기록된다(τ<0.6이면 No-go 기록 + 사용자 알림).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/eval/tests/test_cost_regression.py::test_AC_1_k_path_fewer_llm_calls_than_n
- AC-2 → pytest::ai/eval/tests/test_cost_regression.py::test_AC_2_output_contract_unchanged
- AC-3 → pytest::ai/eval/tests/test_a3_m5.py::test_AC_3_tau_verdict_computation

## 6-2. TDD opt-out
- 사유: 탐색적 측정 spike(A-3 τ 실데이터 1회 판정 — 창업자 수기 라벨 필요, 결과 데이터 의존). τ 계산 함수(기구현 T-017)·cost_regression 하니스는 합성 입력으로 TDD 적용. 실데이터 실행은 라벨 입력 후 1회.
- Follow-up task: τ<0.6(No-go) 시 F5 범위 재검토 + 골든셋 확장을 차기 라운드 `/plan-workitem`에서 생성. 모델 티어링 적용은 GS-2 보존 확인 후 별도 task.

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-023-expanded-fit-validation](../features/F-023-expanded-fit-validation.md)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§6 Discovery exit check, §9 A-3 No-go)
- Discovery: [DISCOVERY](../../10-charter/DISCOVERY.md) (§12 A-3·A-12, §14 Evidence Log)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md) (D7 모델 티어링 측정 후)

## 8. 메모
- `a3_tau.py` T-017 기구현 확인: M1 done, `ai/eval/src/eval/a3_tau.py` 존재. 본 task는 M5 확대 표본으로 재실행 + 리포트 병합만.
- 비용 측정 방법(가정): `run_scoring` 내부 LLM client에 token_counter 콜백 주입 or openai usage 로깅 — builder가 기존 LLM client 구조 확인 후 최소 침습 방식 선택(WHY: 계측 코드가 파이프라인 본체를 변경해선 안 됨).
- 열린 질문: A-3 평가자 확보(창업자 1인 + 현업 1~2인) — 현업 미확보 시 창업자 1인 결과로 신뢰도 하향 명시(F-023 §9).

## 9. 의존성
- depends_on: [T-065, T-068]
- read_set: ["ai/eval/src/eval/a3_tau.py", "ai/eval/src/eval/gates.py", "ai/worker/src/worker/scoring_runner.py"]
- write_set: ["ai/eval/src/eval/cost_regression.py", "ai/eval/src/eval/m5_cost_runner.py", "ai/eval/run_a3_m5.py", "ai/eval/fixtures/m5_expanded/a3_labels_m5.json", "ai/eval/tests/test_cost_regression.py", "ai/eval/tests/test_a3_m5.py"]
- assumptions: ["T-065 완료(scoring_runner.py가 K 후보 경로로 실행 가능)", "T-068 완료(확대 fixture·domain_labels 구성됨)", "ai/eval/src/eval/a3_tau.py T-017에서 기구현"]
- verifier: "uv run pytest ai/eval/tests/test_cost_regression.py ai/eval/tests/test_a3_m5.py"
