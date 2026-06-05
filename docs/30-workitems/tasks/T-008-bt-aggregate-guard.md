# T-008-bt-aggregate-guard

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
Bradley-Terry 집계 + aggregate(3 랭킹 모드) + 도메인 우선순위 가드를 `ai/worker`에 이식한다. 결정적 정렬 — LLM 없음 (SPEC §5).

## 2. 작업 범위
- `bradley_terry(ids, results, iters=300, prior=0.5)`(순수 파이썬 MM, 평균 1 정규화) + `elo` fallback.
- `aggregate(...ranking_mode)`: 3 모드 정렬 키(domain_fit_bt/fit_primary/bt_primary) + 도메인 우선순위 가드(안정 분할) + guard_moves + FitResult 조립.

## 3. 구현 항목
- `ai/worker/src/worker/rank_aggregate.py`(T-003과 같은 모듈) — bradley_terry/elo/aggregate/RANKING_MODES/DOM_RANK.
- 정렬 키 **SPEC §5-2 그대로**: domain_fit_bt `(-domrank,-fit,-bt,lw,jid)`, fit_primary `(-fit,-domrank,-bt,lw,jid)`, bt_primary 비교집합 `(-bt,-fit,-domrank,lw,jid)`+나머지. BT는 `round(.,6)` 동점 안정화.
- 도메인 가드: `non_mismatch + mismatch` (모든 모드 적용). guard_moves 기록.

## 4. 제외 항목
- compute_fit(T-003, 본 task는 사전계산 fits를 입력으로 받음) · pairwise 생성(T-010) · listwise(T-009).

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/rank_aggregate.py`(aggregate/BT 부분), `ai/worker/tests/test_aggregate.py`

## 5. 완료 조건
BT가 동일 입력에 수렴하고, 3 모드 정렬 키가 명세대로이며, mismatch가 절대 non-mismatch 위로 오지 않는다.

## 6. Acceptance Criteria
- AC-1 [Given] 명확한 pairwise 승패 집합 [When] `bradley_terry` 두 번 호출 [Then] 동일 점수로 수렴하고(결정적) 승자 강도 > 패자 강도다.
- AC-2 [Given] 같은 fits·domain_ctx [When] `aggregate(ranking_mode="domain_fit_bt")` [Then] 순서가 (도메인 tier desc → fit desc → BT desc → listwise → jid) 키를 따르고 같은 tier 내 fit이 단조 비증가다.
- AC-3 [Given] mismatch(marketing) 1건이 fit/ BT상 상위로 정렬될 입력 [When] 어떤 ranking_mode로든 aggregate [Then] mismatch는 모든 non-mismatch 아래로 배치되고 guard_moves에 기록된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_aggregate.py::test_AC_1_bt_converges_deterministic
- AC-2 → pytest::ai/worker/tests/test_aggregate.py::test_AC_2_domain_fit_bt_sort_key
- AC-3 → pytest::ai/worker/tests/test_aggregate.py::test_AC_3_mismatch_guard_all_modes

## 6-2. TDD opt-out
<!-- TDD 적용 — 순수 결정적. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-003-relative-ranking](../features/F-003-relative-ranking.md)
- Architecture-Iface: [ARCH ## 7-3](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §5](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
정렬 키는 검증된 캘리브레이션 — 임의 변경 금지(SPEC §5-2). 기본 모드 domain_fit_bt.

## 9. 의존성
- depends_on: [T-003]
- read_set: ["ai/core/src/core/models.py", "docs/20-system/SCORING_PIPELINE_SPEC.md"]
- write_set: ["ai/worker/src/worker/rank_aggregate.py", "ai/worker/tests/test_aggregate.py"]
- verifier: "uv run pytest ai/worker/tests/test_aggregate.py"
- (주의: T-003과 같은 파일 `rank_aggregate.py` write — 같은 wave 동시 implement 금지(file race). T-003 종료 후 진행.)
