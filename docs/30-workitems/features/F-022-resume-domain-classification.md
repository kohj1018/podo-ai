# F-022-resume-domain-classification: 업로드 이력서 도메인 자동분류 + 직군 분리 탭 활성

## 0. Status
draft

> **잠정 (M5 — 알고리즘 핵심 변경 → 사용자 논의 후 task화).** 출력 계약은 M4 동결 — 직군 분기 *출력*이 필요하면 동결 범위 합의 선행.

## 0-1. Type
feature

## 1. 요약
현재 `worker/persistence.load_resume`는 **모든 업로드 이력서를 `primary=frontend / secondary=backend`로 하드코딩**(T-037 §8, 자동 분류 비범위였음)한다 → 백엔드·데이터 이력서가 오정렬돼 도메인 정렬·fit이 틀어진다. 본 feature가 **업로드 이력서의 도메인을 자동 분류**해 하드코딩을 교체하고, 이를 토대로 M4에서 보류했던 **직군 분리 탭(Charter §8 흐름3)**을 활성화한다.

## 2. 사용자 가치 (User Story)
- As a **유진(직무 정체성 미확정 신입 — 백엔드/데이터 사이)**, I want my resume's domain to be detected correctly and to compare backend vs data recommendations in separate tabs, so that fit scores aren't biased by a wrong default and I can position myself across role families.

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 이력서 업로드 → evidence 추출 시 도메인 자동 분류(primary/secondary).
2. 분류 결과로 도메인 정렬(`domain_alignment`)·fit이 실제 직군 기준으로 산출.
3. 피드 상단 직군 분리 탭(백엔드 | 데이터 …) → 탭 전환 시 해당 직군 공고만.
### Alternate path
1. 직군 미확정(양쪽 신호 혼재) → 다중 도메인으로 분류, 양 탭 모두 추천 제시.
2. 사용자가 관심 직군 필터 임시 조정 → 피드 재구성.
### Fail path
1. 🔴 분류 오류로 엉뚱한 직군 → 사용자 가시·교정 가능(분류 신뢰 표시) + 회귀 측정(F-023).
2. 🔴 분류가 출력 계약(evidence/fit_level shape)을 바꾸려 함 → 동결 위반 → 계약 내 표현으로 제한.

## 4. 범위
- **도메인 자동 분류 = evidence(`EvidenceItem.domain`) 집계 + 결정적 스킬→직군 규칙 사전 보강** (사용자 확정 2026-06-07). 새 LLM 호출 0(이미 추출된 evidence 재사용), 결정적. sparse 시 규칙 사전(예: React/Next→frontend, Spring/Django/Node→backend, pandas/Spark/SQL/ML→data)으로 보완. → `load_resume` 하드코딩(frontend/backend) 교체.
- 분류 결과로 `Resume.primary_domains`/`secondary_domains`(이미 list — 다중/미확정 표현 가능) 채움 + 도메인 정렬(`domain_alignment`) 파이프라인 연결.
- 직군 분리 탭 UI(F-018 피드에 탭 추가) — 분류 신뢰 위에서.
- 다중/미확정 도메인 처리(양 탭 제시).
- 회귀: 다종 직군 이력서 분류 정확도 측정(F-023 연동).

## 5. 비범위
- **LLM 기반 도메인 분류기 신설 — 비범위(아직 안 넣음, 사용자 확정).** evidence 집계+규칙으로 시작, 정확도 부족(F-023 측정) 시 후속 검토.
- 출력 계약(fit_level·evidence·result shape) 변경 — M4 동결(직군 분기 *출력* 필요 시 별도 합의).
- 비개발 직군 분류 — Charter §5 비목표(개발 내부 백엔드/데이터 등).
- 직군별 *분기 스코어링 모델* — 단일 모델 유지(A-7, 별도 결정).

## 6. 요구사항
- `load_resume` 하드코딩(frontend/backend) 제거 → 자동 분류.
- 분류는 결정적/버전 핀(GS-1 정합 — 같은 이력서 같은 분류).
- 직군 탭은 *정확한 분류 위에서만* 활성(M4 보류 사유 해소).
- 다중 도메인·미확정 정직 처리.

## 7. Feature-level Acceptance Criteria
- **FAC-1:** 백엔드/데이터/프론트 이력서를 업로드하면 각각 올바른 primary/secondary 도메인으로 분류되고 `load_resume` 하드코딩이 제거된다.
- **FAC-2:** 분류 결과로 도메인 정렬·fit이 산출되어 직군에 맞는 상대 랭킹이 나온다(오정렬 회귀 측정).
- **FAC-3:** 피드 직군 분리 탭에서 탭 전환 시 해당 직군 공고만 필터링되어 노출된다.
- **FAC-4:** 동일 이력서는 동일 도메인으로 분류된다(결정성, GS-1 정합).

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-066:AC-1
- FAC-2 → T-066:AC-1, T-068:AC-4
- FAC-3 → T-067:AC-1
- FAC-4 → T-066:AC-4

## 8. Non-functional Requirements
- 결정성: 분류 버전 핀(같은 이력서 같은 결과).
- 정확도: 다종 직군 이력서 분류 정확도 측정(F-023).

## 8-1. UX 흐름 품질
- **primary task:** 직군 탭 전환으로 백엔드/데이터 추천 비교.
- **empty 흐름:** 한 직군에 공고 없음 → "이 직군은 오늘 공고가 없어요"(포도).
- **error 흐름:** 분류 불확실 → 양 탭 제시 + "직군이 섞여 있어요" 안내.
- **accessibility:** 탭 키보드·ARIA(DESIGN §7-1 Tab).
- **copy 톤:** 포도 톤, 분류 불확실성 정직 표시.
- **success metric (HEART):** Task success → 직군 탭 사용률·포지셔닝 의사결정 도움(실 배포 후).

## 9. 엣지 케이스
- 풀스택/다직군 이력서 → 다중 도메인.
- 신호 빈약 이력서 → 저신뢰 분류 + 정직 표시.
- 영어 이력서 → 분류 다국어 처리.
- 분류와 JD role_family 불일치 조합 → 도메인 정렬 tier 계산.

## 10. 의존성
- 교체 대상: `worker/persistence.load_resume`(하드코딩) — 코드 감사 확인.
- 연계: F-018(직군 탭 UI, M4 보류분), F-021(도메인×벡터 prefilter), F-023(분류 정확도 회귀).

## 11. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§8 흐름3 직군 분기, §2.1 미확정 페르소나)
- Discovery: [DISCOVERY](../../10-charter/DISCOVERY.md) (§12 A-7 직군 분기)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-4 직군 분리 탭)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (도메인 정렬)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components) (Tab)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 12. 열린 질문 (확정값 — plan에서 미세조정)
- **분류 방식 = evidence domain 집계 + 결정적 스킬→직군 규칙 보강 (확정).** LLM 분류기 미도입(§5).
- 규칙 사전(스킬→직군 매핑) 내용 + 버전 핀 — plan(도메인이 `compute_fit` tier→fit_level에 영향, GS-1 정합).
- 직군 카테고리 집합(백엔드/데이터/프론트/풀스택 …) — plan에서 확정.
- 직군 *분기 출력*이 필요해지면 M4 출력 계약 동결과 별도 합의(현재는 불필요 — `domain_alignment`는 이미 출력에 존재).
