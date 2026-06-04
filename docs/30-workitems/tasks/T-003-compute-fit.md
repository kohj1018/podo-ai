# T-003-compute-fit

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
1~5 fit 산출의 결정적 코어(`compute_fit` + cap 사다리 + dedup 실험 플래그)를 `ai/worker`에 이식한다. LLM 없이 단계 4·5 산출만으로 계산되는 알고리즘 본체 (SPEC §4). `domain_alignment`은 ai/core(T-002)에서 import — compute_fit은 그 *결과 문자열*(alignment)만 인자로 받는다.

## 2. 작업 범위
- 가중치 상수(TYPE_WEIGHT/LEVEL_CREDIT/STATUS_WEIGHT/DOMAIN_CAP/MINOR_CATEGORIES) + `compute_fit(table, alignment, dedup_required_preferred=False)` 전문(SPEC §4-2) — 실제 return dict(coverage 전체 필드: critical_met_count/critical_total_count/role_evidence_matches/weighted_earned/total 등)까지 그대로.
- `detect_required_preferred_dups`(보수적 dedup, 기본 OFF — baseline 바이트 동일, SPEC §4-4).
- (비범위) `domain_alignment`은 ai/core 소유(T-002) — 본 task는 그 결과를 입력으로 받음.

## 3. 구현 항목
- `ai/worker/rank_aggregate.py`(또는 `scoring.py`) — compute_fit + cap 사다리 + 도메인 cap(mismatch 동적) + coverage dict + dedup_audit.
- 가중치·임계값(ratio≥0.80→5 …)·cap 규칙(role-defining critical/required ≥2→cap2, =1→cap3; minor crit crit_ratio≥0.8→cap4; domain cap)을 **SPEC §4 상수 그대로** (검증된 캘리브레이션 — 임의 변경 금지).
- dedup: 교차타입·containment/Jaccard≥0.6/(same_cat&Jaccard≥0.4)·필수표현 유지·cap에서만 제외.

## 4. 제외 항목
- BT/aggregate/정렬(T-008) · 매칭/검증(T-006·T-007) · dedup 기본값 승격(실험 유지, SPEC §10-4).

## 4-1. 변경 예정 파일/경로
- `ai/worker/rank_aggregate.py`(compute_fit 부분), `ai/worker/tests/test_compute_fit.py`

## 5. 완료 조건
명세 상수대로 fit 1~5와 cap 사유가 산출되고, dedup OFF가 baseline과 동일하며, 도메인 cap이 적용된다.

## 6. Acceptance Criteria
- AC-1 [Given] role-defining critical prerequisite 미충족 2건인 매칭표 [When] `compute_fit(table, "strong")` [Then] `level <= 2`이고 coverage.cap_reason에 "role-defining critical gaps x2"가 포함된다.
- AC-2 [Given] alignment="mismatch"이고 core prerequisite direct 매칭 0인 표 [When] compute_fit [Then] `level == 1`(role_evidence 없으면 domain cap 1); core direct가 1건 있으면 cap 2다.
- AC-3 [Given] required 행과 그 preferred 트윈이 동일 역량으로 중복된 표 [When] `dedup_required_preferred=False` vs `True` [Then] False는 baseline level과 동일, True는 해당 required를 cap에서 제외해 level이 ≥ baseline이고 `dedup_audit`에 기록된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_compute_fit.py::test_AC_1_role_defining_critical_cap
- AC-2 → pytest::ai/worker/tests/test_compute_fit.py::test_AC_2_mismatch_dynamic_cap
- AC-3 → pytest::ai/worker/tests/test_compute_fit.py::test_AC_3_dedup_flag_vs_baseline

## 6-2. TDD opt-out
<!-- TDD 적용 — 순수 결정적 함수라 테스트 친화적. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-001-core-value](../features/F-001-core-value.md)
- Architecture-Iface: [ARCH ## 7-3](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §4](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
해석 확정: dedup은 *실험 플래그*로만 이식(기본 OFF) — SPEC §10-4 승격 4조건 미충족.

## 9. 의존성
- depends_on: [T-002]
- read_set: ["ai/core/models.py", "docs/20-system/SCORING_PIPELINE_SPEC.md"]
- write_set: ["ai/worker/rank_aggregate.py", "ai/worker/tests/test_compute_fit.py"]
- verifier: "uv run pytest ai/worker/tests/test_compute_fit.py"
