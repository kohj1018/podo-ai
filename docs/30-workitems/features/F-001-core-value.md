# F-001-core-value: 결정론 스코어링 + JD grounding 근거

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
수집된 공고와 사용자 이력서에 대해, *동일 입력이면 항상 동일한* fit 점수·합격가능성 밴드를 산출하고, 각 점수의 근거를 JD 원문 인용으로 표시한다. 제품의 단일 thesis("틀린 점수 > 근거 없는 점수")를 직접 구현하는 핵심 feature이며, GS-1·GS-2 게이트가 이 feature 위에서 측정된다. (ADR-100 D1·D3)

## 2. 사용자 가치 (User Story) — Type=feature 일 때
- As "유진"(신입/졸업예정 개발자 구직자, Charter §2.1), I want to 각 공고가 내 스펙으로 붙을 가능성을 *흔들리지 않는* 점수와 *JD에 실재하는* 근거로 보고 싶다, so that 헛지원·과소지원을 줄이고 지원/스킵 의사결정 비용을 낮출 수 있다. (DISCOVERY pain #2·#3 / JTBD 보조)
- As "유진", I want to 점수가 왜 그렇게 나왔는지(이력서 항목 ↔ JD 요구 매핑)를 직접 확인하고 싶다, so that "신입/경력무관"에 숨은 경력요구 gap을 스스로 인지할 수 있다. (pain #2)

## 3. 핵심 시나리오 (Feature-level)

### Happy path
1. (이력서, 공고집합)이 주어지면 각 쌍에 대해 캐시 키를 계산한다.
2. 캐시 hit → 저장된 점수·밴드·근거를 즉시 반환(LLM 호출 없음).
3. 캐시 miss → LLM을 temperature=0/seed 고정/버전 핀으로 호출, JD 원문 span에 grounding된 근거를 추출.
4. fit 점수·5단계 합격가능성 밴드·근거(JD 인용 + 이력서↔JD 매핑)를 저장하고 반환.
5. 사용자는 점수 배지와 펼침 근거를 확인한다.

### Alternate path
1. 점수가 낮은 공고도 근거(부족 요건)를 명시하되 결과 자체는 숨기지 않는다.
2. 이력서가 갱신되면 정규화본이 바뀌어 캐시 키가 갱신 → 재계산(이전 캐시는 버전으로 구분 보존).

### Fail path
1. 🔴 동일 입력에 점수가 흔들림(캐시 우회·키 결함) → GS-1 위반, 게이트 실패. 절대 불가.
2. 🔴 JD에 없는 요구를 근거로 생성(hallucination) → GS-2 위반. 절대 불가.
3. 🟡 LLM 호출 실패(miss 경로) → 점수 보류 상태 표시(가짜 점수 노출 금지), 재시도.

## 4. 범위
- (이력서, JD) 쌍에 대한 결정론 캐시 스코어링 경로(키 계산 → hit/miss → 저장).
- cache miss 시 LLM 호출의 결정론 설정(temperature=0/seed/모델·프롬프트 버전 핀).
- JD 원문 span grounding 근거 추출 + 이력서↔JD 1:1 매핑 노출(F6·F7).
- fit 점수 + 5단계 합격가능성 밴드 산출(F4).
- 게이트 측정 훅: test-retest 반복 실행 경로 + 근거 사실성 라벨링 대상 출력.

## 5. 비범위
- 상대 랭킹(F5) 정렬 자체 — 별 feature로 분해(A-3 τ 결과 의존). 본 feature는 *쌍 단위 점수·근거*까지.
- 수집(F1·F3)·커버리지 패널(F2)·피드 UI — 별 feature.
- 직군 분기 모델 — A-7 의존, 단일 모델로 시작.
- 절대 합격확률 % — 비목표(밴드로 대체).

## 6. 요구사항
- 캐시 키는 (이력서 정규화본·JD 정규화본·모델 ID·프롬프트 버전·파라미터)로 구성하고 직렬화 가능해야 한다. 시간·랜덤·환경 값 혼입 금지 (ADR-100 D3 / ARCH §3-1).
- cache miss LLM 호출은 temperature=0(또는 동등 결정 설정) + seed 고정 + 모델/프롬프트 버전 핀.
- 모든 근거 문장은 JD 원문 span에 매핑되어야 하며, JD에 없는 요구는 근거로 생성하지 않는다 (ARCH §3-1 grounding 규칙).
- 합격가능성은 정확한 %가 아닌 5단계 색깔 밴드로 표현 (cut-off는 열린 질문).
- LLM 호출 실패 시 가짜 점수를 노출하지 않고 보류 상태로 표시.

## 7. Feature-level Acceptance Criteria
- **FAC-1 (GS-1):** 동일 (이력서, JD) 입력을 N=10회 재채점하면 캐시 hit 경로의 점수·밴드 변동이 0이다.
- **FAC-2 (GS-1):** cache miss 재계산 경로에서도 상위 fit 순서(top-k)가 N회 반복에 변동 0이다.
- **FAC-3 (GS-2):** 표본 공고 ≥30에서 표시된 근거 중 JD 원문에 실재하지 않는 요구(hallucinated requirement) 비율이 ≤2%다.
- **FAC-4 (F7):** 각 점수에 대해 이력서 항목 ↔ JD 요구의 1:1 매핑이 사용자에게 노출된다.
- **FAC-5:** LLM 호출 실패 시 가짜 점수가 노출되지 않고 보류 상태가 표시된다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
<!-- /plan-workitem이 task 분해 시 본 subsection을 채운다 (영속 SSOT — plan 출력은 echo).
     형식: FAC-N → T-NNN:AC-N, T-MMM:AC-M (다대다 허용). 현재 task 미분해 → 미매핑. -->
- FAC-1 → (task 미분해 — /plan-workitem M1에서 매핑)
- FAC-2 → (task 미분해)
- FAC-3 → (task 미분해)
- FAC-4 → (task 미분해)
- FAC-5 → (task 미분해)

## 8. Non-functional Requirements
- **재현성(지배):** GS-1 — 동일 입력 동일 출력. 결정론 캐시 경계(ARCH §3-1)가 구조적 보증.
- **정확성(지배):** GS-2 — 근거 사실성 ≤2% hallucination.
- **보안:** 이력서 = 민감 PII. 외부 LLM 전송 시 최소 필요 정보 원칙(구체 정책은 스택·제공자 확정 후 ADR).
- **성능:** 캐시 hit은 LLM 지연과 분리(즉시 반환). miss 배치 지연 목표는 스택 확정 후.

## 8-1. UX 흐름 품질
<!-- UI feature 한정. 본 feature는 점수·근거 *산출*이 핵심이고 노출 surface는 피드 feature와 공유 —
     스택 확정(ADR-101)·UI 디자인 확정(DESIGN.md). 흐름의 시각 구현 세부는 피드 feature에서 확정. 현재 방향만 명시. -->
- primary task: 공고의 점수·근거를 신뢰하고 지원/스킵을 결정.
- error 흐름: LLM 실패 시 *가짜 점수 대신* 보류 상태 — "틀린 것보다 없는 게 낫다" 원칙을 UX에서도 관철.
- copy 톤: 근거는 단정 대신 JD 인용 기반("JD에 X 요구됨"). 과약속 표현 금지.
- success metric (HEART): 추천 상위군의 실제 서류 통과율 > 하위군(GS-3, 출시 후 실데이터로 DISCOVERY §14 회수).

## 9. 엣지 케이스
- 이력서 정량 신호가 빈약(인턴 1·팀플 2~3)해 매핑할 근거가 적은 경우 — gap을 *없는 것처럼* 채우지 않는다(A-2).
- JD가 "신입/경력무관"인데 우대사항에 경력요구가 숨은 경우 — 합리적 inference는 허용하되 fabrication 금지, 경계 명문화 필요(A-10 / 열린 질문).
- 모델/프롬프트 버전 변경 시 기존 캐시 — 버전으로 구분, 무효화·마이그레이션 정책 필요(열린 질문).
- 동일 공고가 여러 채널에서 수집된 중복 — 스코어링 전 dedup 책임은 Collector(F1) 경계.

## 10. 의존성
- **선행:** 스택 확정(`/bootstrap-stack`) — LLM 제공자·캐시 저장소·언어가 결정론 키 설계에 직접 영향.
- **선행(검증):** A-3(τ≥0.6 또는 자명 페어 위반율 ≤5%, Charter §6 Discovery exit check) — 미달 시 상대 랭킹 범위 재검토가 본 feature 후속(F5)에 영향.
- **입력:** Collector(F1)가 저장한 JobPosting, 사용자 Resume.
- **A-12:** 결정론 캐시가 실제로 변동 0을 보장하는지 100회 반복 결정성 테스트로 확인(FAC-1·FAC-2의 근거).

## 11. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§4 G2·G4, §6 GS-1·GS-2)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-1 결정론·grounding 경계, §4 Score·Evidence)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) (D1 게이트 우선, D3 결정론 캐시)

## 12. 열린 질문
- 5단계 밴드 cut-off 경계는? 초기엔 보수적으로 넓게 잡을 것인가? (Charter §10)
- "숨은 경력요구 추론"의 합리적 inference vs fabrication 경계를 프롬프트 가드레일로 어떻게 명문화? (A-10)
- 이력서 정규화 수준 — 과도하면 캐시 폭증, 과소하면 변동. 어디서 균형? (A-12 / ARCH §10)
- 모델/프롬프트 버전 변경 시 기존 점수·캐시 마이그레이션 정책? (GS-1)
- 단일 스코어링 모델 vs 직군(백엔드/데이터) 분기 — 언제 분기? (A-7)
