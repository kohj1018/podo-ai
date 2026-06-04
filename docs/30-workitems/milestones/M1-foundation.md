# M1-foundation

## 0. Status
draft

## 1. 목적
신뢰 게이트(GS-1 재현성 · GS-2 근거 사실성)를 *실증할 수 있는* 최소 end-to-end 골격을 세운다. "수집 → 결정론 스코어링 → 근거 표시"가 한 줄로 동작하고, 그 위에서 게이트를 측정할 수 있는 상태가 M1의 done이다. (Charter §6 / ADR-100 D1)

## 2. 범위
토스·당근 2곳 수집 골격 + 결정론 캐시 스코어링 + JD grounding 근거 + 커버리지 투명성 패널 + 최소 피드. 게이트 측정 경로(test-retest·근거 사실성 라벨링)를 함께 세운다.

> **선행 의존 (해소):** 스택 확정(ADR-101)·design 확정(DESIGN.md)·A-1 검증(크롤링 실증, 2026-06-04) 완료 → `/plan-workitem M1` 착수 가능. 남은 pre-impl 게이트는 A-3(상대 랭킹 Kendall τ) 1건 — 분해 시 *A-3 검증을 첫 task로 박고* 스코어러 구현은 그 뒤(Charter §6 Discovery exit check).

## 3. 포함되는 기능
- **F-001 (core-value)** — 결정론 스코어링 + JD grounding 근거 (게이트 핵심 — 본 bootstrap이 생성).
- F2 커버리지 투명성 패널 (Fail #3 차단 — `/plan-workitem`에서 feature 분해).
- F1·F3 수집 골격 + 신규/마감 diff (토스·당근 2곳 — `/plan-workitem`에서 분해).
- 최소 피드(단일 리스트 + 밴드 표시) — 게이트 실증에 필요한 만큼만.

## 4. 제외되는 기능
- 다채널 풀커버리지(7개+) — Charter §5 비목표.
- 자소서/이력서 자동작성·첨삭 — 비목표.
- 무응답 피드백 루프 자동화 / 절대 합격확률 % — 비목표.
- 일정·자동지원·협업 — 비목표.
- 직군 분기 스코어링 모델 — A-7 결과 의존, M1은 단일 모델로 시작(열린 질문).

## 5. 완료 기준 (graduation checklist)
> sprint contract: 본 마일스톤이 "done"이라고 합의되는 외부 검증 가능한 기준 (ADR-014).
- [ ] 모든 task status: done
- [ ] 통합 validate Pass
- [ ] E2E Pass (스택에 정의된 경우)
- [ ] AC 매핑 100% (validation report 기준)
- [ ] P0 severity finding 0건 (QA_FINDINGS의 본 마일스톤 헤더 기준)
- [ ] (선택) **게이트 실증:** 동일 (이력서, JD) 입력 N=10회 재채점 시 캐시 hit 변동 0 (GS-1) + 표본 ≥30 근거의 hallucinated requirement ≤2% (GS-2) 측정 경로가 동작한다.

## 6. 관련 문서
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§4 목표, §6 성공 기준)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3 모듈, §3-1 의존성 규칙)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) (D1 게이트 우선, D3 결정론 캐시)

## 7. 열린 질문
- 스택 확정(ADR-101)·A-1 검증(크롤링 동작 확인, 2026-06-04) 완료 → task 분해 가능. 크롤링 방식(정적 httpx 우선 → 필요 시 headless)은 구현 시 확정.
- **A-1은 검증됨(2026-06-04 — 크롤링 실증).** 남은 A-3(상대 랭킹 τ)이 M1 구현 착수 전 선검증되어야 게이트 실증이 의미를 가짐 (DISCOVERY §12 / Charter §6 Discovery exit check). A-3 τ<0.6이면 F5(상대 랭킹) 범위 재검토.
- M1에 상대 랭킹(F5)을 포함할지 — A-3 τ<0.6이면 범위 재검토(ADR-100 D1 / Charter §9 A-3 No-go).
- 5단계 밴드 cut-off 미정(Charter §10) — 최소 피드의 밴드 표시 폭에 영향.

## 8. 회고 (stabilize 자동 채움)
- 목표 달성도: <정량/정성 1줄>
- scope creep 사례: <있으면 1줄, 없으면 "없음">
- 비목표(charter ## 5) 위반 사례: <있으면 1줄>
- 핵심 학습 3개 이내
