# F-033-core-flow-hardening

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
핵심 골든패스(**로그인 → /resume 입력 → 제출 → 피드 분석결과**)를 끊김·버그 없이 "물 흐르듯" 만드는 통합 하더닝. 다른 M7 feature(F-028~F-032)가 surface를 바꾼 뒤, 골든패스 위 기존/예상 버그를 점검·수정하고 회귀 테스트로 고정한다. 근거: M7 §2-B / Charter §8 흐름1·2.

## 2. 사용자 가치 (User Story)
- As 유진(Charter §2.1), I want 가입부터 추천을 보기까지 한 번도 막히지 않길 바란다, so that 첫 경험에서 신뢰를 잃지 않는다.

## 3. 핵심 시나리오 (Feature-level)
- **happy**: 신규 가입 → 이력서 작성/제출 → 채점 대기 skeleton → 피드 분석결과. 끊김 0.
- **alternate**: 세션 만료·네트워크 실패·이력서 교체 등 분기에서도 명확한 상태·복구 경로.
- **fail**: 식별된 골든패스 버그를 재현 테스트로 박고(Red) 수정(Green).

## 4. 범위
- 골든패스 통합 점검: 세션 만료, 교차출처 쿠키(credentials), `localStorage('podo_active_resume_id')` 엣지(교체/재채점), `window.location.assign` 강제이동 UX, 업로드/채점 실패 복구.
- 식별 버그 수정 + 회귀 테스트(E2E/유닛).
- QA_FINDINGS.md M7 헤더에 finding 누적.

## 5. 비범위
- 새 기능 추가(F-028~F-032 소관).
- 골든패스 밖 surface의 버그(별도 finding 이연).
- 성능 최적화(기능 동작 우선).

## 6. 요구사항
- 버그는 *재현 실패 테스트*(bugfix type)로 박은 뒤 수정(ADR-009 Red→Green).
- 발견했으나 M7에서 안 고치는 건 QA_FINDINGS에 명시 이연(은폐 금지).

## 7. Feature-level Acceptance Criteria
- FAC-1 골든패스(로그인→resume→제출→피드)가 끊김·버그 없이 E2E로 통과한다.
- FAC-2 식별된 P0/P1 버그가 수정되거나 QA_FINDINGS(M7)에 명시 이연된다.

## 7-1. FAC ↔ AC 매핑표
- FAC-1 → T-102:AC-1
- FAC-2 → T-102:AC-2

## 8. Non-functional Requirements
- 신뢰성: 골든패스 회귀 테스트가 CI에서 재현 가능.
- 보안: 세션/격리 불변식 보존(타인 데이터 차단).

## 8-1. UX 흐름 품질
- primary task: 가입→추천 도달 무중단.
- empty/loading/error: 각 분기에서 명확한 상태·복구(삼키기 금지, REV-M2-UI-001).
- accessibility: 상태 전환 시 포커스/aria 유지.
- copy 톤: 실패도 포도 톤이되 사실 명확("아침 배달이 늦어요").
- success metric(HEART-Task success): 골든패스 완주율(실데이터/E2E).

## 9. 엣지 케이스
- 이력서 교체 직후 이전 run/coarse 혼입 방지(M5-repair-38 정합).
- 채점 실패 상태에서 재시도 동선.
- 두 탭/중복 제출.

## 10. 의존성
- F-028~F-032(surface 변경) 통합 후 실행 — 마지막 wave.

## 11. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-009](../../90-decisions/boilerplate/ADR-009-tdd-default.md)(Red→Green)

## 12. 열린 질문
- 골든패스 E2E를 Playwright(기존 e2e) 어디까지 확장할지.
