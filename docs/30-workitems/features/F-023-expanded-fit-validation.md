# F-023-expanded-fit-validation: 확대 입력 fit 품질·게이트 재측정 + A-3 τ 실데이터

## 0. Status
draft

> **잠정 (M5 — 사용자 논의 후 task화).** 측정·검증 feature(코드 변경 최소 + 정답셋/라벨 의존).

## 0-1. Type
feature

## 2. 기술적 근거 (Technical rationale)
**무엇을:** F-020(커버리지)·F-021(벡터/비용)·F-022(도메인)로 *확대된 입력*(다종 회사 JD × 다종 이력서) 위에서 fit 품질과 신뢰 게이트(GS-1/GS-2)가 보존되는지, 그리고 비용 최적화가 정확도를 깎지 않는지 측정한다. 더불어 M1에서 하니스만 두고 *실데이터로 미실행*한 **A-3 τ(상대 랭킹 타당도)를 1회 실측**한다.
**서비스하는 가정:** A-3(최고 위험)·A-9(GS-2)·A-12(GS-1)·A-7(직군 분류). 측정 경로는 이미 `ai/eval`(τ 프록시 `a3_tau.py`·게이트 `gates.py`)에 존재 — 확대 입력으로 확장.

## 1. 요약
다종 이력서 × 다종 JD 표본에서 **fit 품질을 측정**하고, **GS-1(캐시 hit 변동 0)·GS-2(hallucinated requirement ≤2%)를 확대 입력에서 재실측**한다. JD 종류 폭증은 hallucination 표면을 키우고, F-021 비용 최적화(모델 티어링)는 결정성을 흔들 수 있으므로 *회귀 가드*로 잡는다. **A-3 τ**는 창업자(+가능 시 현업) 수기 랭킹 vs 모델 랭킹 Kendall τ로 1회 판정(Charter §6 / DISCOVERY §12 A-3 No-go: τ<0.6).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 확대 표본(다종 이력서·다종 JD) 구성 → 채점 → fit 품질·게이트 지표 산출.
2. GS-1: 동일 입력 2회 채점 변동 0. GS-2: 표본 ≥30 근거 hallucination ≤2%.
3. A-3: 수기 랭킹 vs 모델 τ ≥ 0.6(또는 자명 페어 위반율 ≤5%) → 진행 신호.
### Alternate path
1. 비용 최적화 전/후 품질 비교 → 정확도 미하락 확인.
2. 도메인 분류(F-022) 정확도 측정 → 오정렬 회귀.
### Fail path
1. 🔴 GS-1/GS-2 확대 입력에서 미달 → 회귀로 잡고 F-021/F-022 보강 차단 게이트.
2. 🔴 A-3 τ<0.6 → DISCOVERY §11 No-go 경로(F5 상대 랭킹 범위 재검토) — 사용자 결정.

## 4. 범위
- 확대 평가 표본/정답셋 구성(다종 이력서·다종 회사 JD).
- GS-1/GS-2 재측정 하니스 확장(`ai/eval` 기존 경로 위에).
- 비용 최적화 전/후 품질·비용 회귀.
- 도메인 분류(F-022) 정확도 측정.
- A-3 τ 실데이터 1회(수기 랭킹 입력 — 사용자/현업 라벨) + 판정 기록(DISCOVERY §12·§14 회수).

## 5. 비범위
- 출시 후 GS-3 실데이터(실 서류통과 결과) — M6 배포 후 트랙(본 feature는 출시 전 프록시까지).
- 자동 라벨링(수기/소규모 정답셋 — Charter §5).
- 알고리즘 구현 자체 — F-021/F-022(본 feature는 *측정*).

## 6. 요구사항
- GS-1: 캐시 hit 변동 0 / miss top-k 순서 변동 0(확대 입력).
- GS-2: hallucinated requirement ≤2%(표본 ≥30, 사람 라벨).
- A-3: τ 측정 + Charter §9 구간 판정(τ<0.6 No-go / 0.6~0.7 조건부 / ≥0.7 진행).
- 비용 최적화가 게이트를 깨지 않음(전/후 회귀).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** 확대 표본에서 GS-1(동일 입력 변동 0)·GS-2(hallucination ≤2%)가 재측정되어 보존이 확인된다.
- **FAC-2:** 비용 최적화(F-021) 전/후 fit 품질이 비교되어 정확도 미하락이 입증된다.
- **FAC-3:** 도메인 분류(F-022) 정확도가 다종 직군 이력서에서 측정된다.
- **FAC-4 (선택/후속 게이트 — M5 졸업 비차단):** A-3 τ는 *내부 golden/persona eval 확장*을 우선(사용자 결정 #11, 2026-06-08). 창업자 수기 랭킹 라벨 준비 시 M5에서 1회 측정·판정해 DISCOVERY §12 A-3 / §14에 회수(미준비 시 후속 게이트). M5 §5 "(선택)"과 정합.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-068:AC-1, T-068:AC-2
- FAC-2 → T-069:AC-1, T-069:AC-2
- FAC-3 → T-068:AC-3
- FAC-4 → T-069:AC-3

## 8. Non-functional Requirements
- 측정 재현성: 평가 하니스 결정적(fixture/시드).
- 표본 한계 정직 고지(소표본 통계적 일반화 제한 — A-6 연동).

## 8-1. UX 흐름 품질
(해당 없음 — 오프라인 평가.)

## 9. 엣지 케이스
- 영어 JD × 한국어 이력서 교차 fit 품질.
- 직군 혼재 이력서의 cross-scoring(A-7).
- A-3 평가자 1인 한계(현업 확보 어려우면 신뢰도 하향 명시).

## 10. 의존성
- 측정 대상: F-020(커버리지)·F-021(비용/벡터)·F-022(도메인).
- 기존 경로: `ai/eval`(a3_tau·gates·golden_pairs·regression).
- 사용자 입력: A-3 수기 랭킹 라벨(+가능 시 현업).

## 11. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§6 GS-1/2/3, §9 A-3)
- Discovery: [DISCOVERY](../../10-charter/DISCOVERY.md) (§9 GS-3 프록시, §12 A-3·A-9·A-12, §14 Evidence)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) (게이트 우선)

## 12. 열린 질문 (논의 전제)
- A-3 평가자 확보(창업자 1인 + 현업 1~2인) + No-go(τ<0.6) 시 대응(F5 범위 재검토).
- 확대 표본 크기·구성(직군·언어·회사 다양성).
- GS-2 라벨링 인력·기준.
- **(M5 핵심 변경 — 사용자 논의 후 task화.)**
