# F-003-relative-ranking: listwise + pairwise + Bradley-Terry + 도메인 우선순위 가드

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
쌍 단위 fit(F-001) 위에서 수집된 공고들의 *상대 적합도 순서*를 산출한다: listwise 재랭킹 → 상위 후보 A/B·B/A 교차 pairwise → Bradley-Terry 상대 강도 집계 → 랭킹 모드(기본 `domain_fit_bt`) + 도메인 우선순위 가드. = DISCOVERY F5. BT는 *상대 강도*일 뿐 합격확률이 아니다. 알고리즘 SSOT: [SCORING_PIPELINE_SPEC §5·§7-3·§7-4](../../20-system/SCORING_PIPELINE_SPEC.md).

> **A-3 게이팅 (M1 §2 재해석):** 본 feature의 *코드 이식*은 A-3 검증 전 진행한다(τ 측정에 랭커가 선재해야 하므로). A-3 τ 측정은 F-004(골든 페어)가 수행. `τ<0.6`이면 F5 *제품화/노출* 범위를 재검토(코드는 이식되어 있되 제품 디폴트 노출 여부 재결정).

## 2. 사용자 가치 (User Story) — Type=feature 일 때
- As "유진"(Charter §2.1), I want to 공고들이 내 적합도 순으로 정렬되되 *주력 도메인 역할이 위에 오고 마케팅/디자인 같은 무관 직군이 위로 새치기하지 않길* 원한다, so that 상위부터 펼쳐 보며 지원 우선순위를 빠르게 정한다. (Charter §8 흐름 2)
- As "유진", I want to 비슷한 공고 간 우열이 순서 편향 없이 일관되길 원한다, so that 순위를 신뢰할 수 있다. (GS-1 / pain #3)

## 3. 핵심 시나리오 (Feature-level)

### Happy path
1. 검증된 매칭표 + 공유 fit(F-001 단계 6)을 입력받는다.
2. 압축 매칭표로 listwise 재랭킹(누락/중복 보정).
3. 상위 후보 집합(top-K + fit≥4 + strong 도메인 구제)을 A/B·B/A 교차 pairwise 비교.
4. Bradley-Terry로 상대 강도 집계.
5. `domain_fit_bt` 정렬(도메인 tier → fit → BT → listwise → 결정적) + 도메인 우선순위 가드.
6. 최종 순위 + guard_moves를 산출.

### Alternate path
1. pairwise 양방향 불일치 → tie/low로 처리(순서 편향 차단), 최상위 순위는 흔들지 않음.
2. 랭킹 모드 전환(`fit_primary`/`bt_primary`) — 업스트림 신호 동일, 최종 순서만 변경.

### Fail path
1. 🔴 mismatch(마케팅/디자인/PM) 역할이 엔지니어링 역할 위로 올라감 → 하드 가드 위반. 절대 불가.
2. 🔴 같은 입력에 top-k 순서가 흔들림(비결정) → GS-1 위반.

## 4. 범위
- listwise 재랭킹(`listwise_rerank` 프롬프트 + 압축표 + 누락/중복 보정, SPEC §7-3).
- pairwise 후보 집합 구성(결정적) + A/B·B/A 교차 비교(`pairwise_compare`, SPEC §7-4).
- Bradley-Terry MM 반복(순수 파이썬) + elo fallback(SPEC §5-1).
- aggregate 3 모드 정렬 키 + 도메인 우선순위 가드(SPEC §5-2·5-3).

## 5. 비범위
- 쌍 단위 fit·cap·근거 산출 — F-001.
- 직군 분기 랭킹 모델 — A-7 의존, 단일 모델로 시작.
- 절대 합격확률 % — 비목표. BT는 상대 강도만.

## 6. 요구사항
- 정렬 키·DOM_RANK·도메인 가드는 SPEC §5-2·5-3을 그대로 이식(검증된 캘리브레이션 — 임의 변경 금지).
- BT는 scipy 없이 순수 파이썬 MM(`iters=300, prior=0.5`), 평균 강도 1 정규화(SPEC §5-1).
- 모든 랭킹 모드에서 도메인 우선순위 가드 적용(mismatch는 non-mismatch 위로 못 옴) — 하드 규칙.
- pairwise는 A/B·B/A 양방향, agreed일 때만 outcome 확정(순서 편향 차단).
- 업스트림 신호(매칭/검증/fit/listwise/pairwise)는 모드 무관 동일, 최종 순서만 모드별.

## 7. Feature-level Acceptance Criteria
- **FAC-1:** listwise가 모든 job_id를 정확히 한 번씩 포함하도록 누락/중복을 보정한다(누락 시 fit/domain 기준 안전 배치).
- **FAC-2:** pairwise가 A/B·B/A 양방향을 비교하고 불일치 쌍은 tie/low로 처리하되 최상위 순위를 바꾸지 않는다.
- **FAC-3:** Bradley-Terry가 pairwise 결과로 상대 강도를 산출하고 동일 입력에 동일 점수로 수렴한다(결정적).
- **FAC-4:** `domain_fit_bt` 정렬이 (도메인 tier → fit → BT → listwise → 결정적) 키를 따르고, 같은 tier 안에서 fit이 단조다.
- **FAC-5:** 어떤 모드에서도 mismatch 도메인 역할이 non-mismatch 역할 위로 오지 않는다(도메인 우선순위 가드).

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-009:AC-1, T-009:AC-2 (listwise 누락/중복 보정)
- FAC-2 → T-010:AC-1, T-010:AC-2 (A/B·B/A + 불일치 처리)
- FAC-3 → T-008:AC-1 (BT 수렴·결정성)
- FAC-4 → T-008:AC-2 (aggregate domain_fit_bt 정렬 키)
- FAC-5 → T-008:AC-3 (도메인 우선순위 가드 — 모든 모드)

## 8. Non-functional Requirements
- **재현성(지배):** GS-1 — 결정적 정렬. BT/aggregate는 순수 파이썬(LLM 없음). listwise/pairwise는 캐시로 재현.
- **타당도:** GS-3 — 상대 랭킹이 사람 판단과 일치(F-004 골든 페어 τ로 측정).
- **성능:** pairwise는 후보 집합으로 제한(top-K + 상한)해 LLM 호출 폭증 방지.

## 8-1. UX 흐름 품질
(해당 없음 — 정렬 *산출* 백엔드. 순위 노출 UX는 Feed feature.)

## 9. 엣지 케이스
- 비교 쌍 부족/불일치 다수 — BT prior로 그래프 연결 유지, 수렴 보장.
- listwise가 일부 job_id 누락 후 재질의도 실패 — fit/domain 기준 안전 배치(blind append 금지).
- 같은 tier·같은 fit 동점 — BT가 타이브레이크, BT도 동점이면 listwise→job_id 결정적.
- 모든 후보가 mismatch — 가드는 no-op(분할 후 동일 순서).

## 10. 의존성
- **선행:** F-001(데이터 계약·compute_fit·매칭·검증·프롬프트·LLM 게이트웨이·캐시). 구체: T-002, T-003, T-004(게이트웨이), T-005·T-006·T-007·T-008(F-001 매칭/검증/프롬프트).
- **A-3:** τ 측정은 F-004(T-016/T-017)가 수행. 본 feature는 측정 *대상* 랭커를 제공.

## 11. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§4 G2, §6 GS-1·GS-3, §9 A-3)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3 Scorer, §3-1 결정론 경계)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §5·§7-3·§7-4](../../20-system/SCORING_PIPELINE_SPEC.md)
- Feature: [F-001-core-value](F-001-core-value.md) (선행 — 쌍 단위 스코어링)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) (D1 게이트 우선)

## 12. 열린 질문
- A-3 τ<0.6 시 F5 제품 노출 범위를 어디까지 좁힐 것인가? (Charter §9 No-go)
- 직군 미확정(백엔드/데이터) 페르소나에 단일 도메인 프로파일 vs 분기 — 언제? (A-7)
- pairwise 후보 상한(`MAX_PAIRWISE_CANDIDATES`)을 공고 수 증가 시 어떻게 조정?
