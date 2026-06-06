# F-012-doc-reconcile: M1→M2 누적 doc reconcile 부채 회수

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 요약
M1→M2 누적 문서 부채를 M3 첫 작업으로 회수한다. (1) 용어 divergence("적합도 5단계" ↔ "합격가능성 밴드") 통일, (2) DISCOVERY §15 Insight I-1/2/3 `open→planned/done` promote, (3) DISCOVERY/Charter/DESIGN `status` 정리, (4) globals.css 색상 토큰 SSOT 동기, (5) ADR-104 backref 6건 부착. **정합만 — 제품 전략 재작성·새 기능 범위 재정의는 비범위.**

> 근거: IMPROVEMENT_GUIDE M2 P1 #5 doc reconcile / cross-stabilize 회귀 신호 / M3 §2 "M3 첫 feature(F-012)로 흡수" 사용자 판단.

## 2. 기술적 근거 (Type=technical-enabler)
- **무엇/왜:** 용어 divergence가 validate·stabilize·plan 라운드에서 false-positive를 생성하고, Insight promote 누락은 `/discover-product --update` SSOT 경로를 막는다. doc reconcile 없이 M3 feature 문서를 쌓으면 drift가 더 깊어진다.
- **서비스하는 결정/가정:** [ADR-035](../../90-decisions/boilerplate/ADR-035-continuous-discovery.md) DISCOVERY=SSOT reconcile 경로 / M3 §2 "첫 feature로 흡수" / IMPROVEMENT_GUIDE M2 P1 #5.

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. `/discover-product --update`로 DISCOVERY.md 용어 통일·Insight promote 적용.
2. `/bootstrap-project --apply`로 Charter snapshot sync.
3. DESIGN.md globals.css 토큰 SSOT 정합 확인.
4. ADR-104 backref 6건 부착 완료.
5. 전체 validate green — 문서 내 term/link 일관성 확인.
### Fail path
1. 🔴 용어 통일 과정에서 제품 전략·기능 범위가 변경됨 → 비범위 위반(차단).

## 4. 범위
- **용어 통일** — DISCOVERY/Charter/DESIGN/workitem 전체에서 "합격가능성 밴드" → "적합도 5단계"로 치환. (`/discover-product --update` → `/bootstrap-project --apply` 경유)
- **Insight promote** — DISCOVERY §15 Insight I-1 `open→done`, I-2/I-3 `open→planned` + `linked feature` 채움.
- **status 정리** — DISCOVERY/Charter `## 0. Status` 현행화.
- **globals.css 토큰 동기** — `podo/apps/web/src/app/globals.css` CSS 변수가 DESIGN.md §2 토큰과 일치하는지 확인·동기.
- **ADR-104 backref** — ADR-104에서 요구한 역참조 주석(`per ADR-104`) 6건을 해당 워커 파일에 부착(T-030/T-031이 이미 구조를 만들었으면 backref만 추가).

## 5. 비범위
- 제품 전략 재작성·새 기능 범위 재정의.
- 새 ADR 신설(ADR-105는 F-014 범위).
- UI 컴포넌트 코드 변경.
- 스코어링 알고리즘 변경.

## 6. 요구사항
- 변경 후 DISCOVERY/Charter/DESIGN에서 "합격가능성 밴드" 잔존 0건.
- Insight I-1 status=done, I-2/I-3 status=planned + linked feature 채워짐.
- globals.css CSS 변수가 DESIGN.md §2 semantic 토큰 이름과 1:1 일치.
- 통합 validate exit 0 유지(문서 링크 깨짐 0).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** DISCOVERY/Charter/DESIGN/workitem 전체 grep에서 "합격가능성 밴드" 잔존 0건.
- **FAC-2:** DISCOVERY §15 Insight I-1 status=done, I-2/I-3 status=planned, linked feature 채워짐.
- **FAC-3:** `podo/apps/web/src/app/globals.css` CSS 변수 이름이 DESIGN.md §2 semantic 토큰 이름과 diff 0.
- **FAC-4:** ADR-104 대상 파일 6건에 `per ADR-104` backref 주석 존재.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-032:AC-1
- FAC-2 → T-032:AC-2
- FAC-3 → T-033:AC-1
- FAC-4 → T-033:AC-2

## 8. Non-functional Requirements
(해당 없음) — 문서·설정 파일 변경만, 런타임 영향 없음.

## 8-1. UX 흐름 품질
(해당 없음) — technical-enabler, UI 변경 없음.

## 9. 엣지 케이스
- "합격가능성 밴드" 치환 시 의미 맥락이 달라 단순 치환이 부적절한 문장 → 개별 검토 후 재표현.
- globals.css에 DESIGN.md 미등록 토큰이 있으면 → DESIGN.md §2에 추가 등록(또는 제거 판단 후 결정).

## 10. 의존성
없음 — M3 첫 작업, scaffold 의존 0, 즉시 착수 가능.

## 11. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- ADR: [ADR-035](../../90-decisions/boilerplate/ADR-035-continuous-discovery.md), [ADR-104](../../90-decisions/project/ADR-104-worker-shared-util-boundary.md)

## 12. 열린 질문
- "합격가능성 밴드" 치환 시 Charter §6 GS-1 설명 문맥에서 "밴드"가 기술 용어로 쓰인 경우 어떻게 처리할지 → T-032에서 케이스별 확인.
