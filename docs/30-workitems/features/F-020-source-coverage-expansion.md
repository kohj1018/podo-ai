# F-020-source-coverage-expansion: 채용공고 커버리지 확대 (공식 채용 페이지·ATS 어댑터)

## 0. Status
draft

> **잠정 (M5).** 커버리지 확대는 Charter §5 "다채널 풀커버리지 비목표"의 *숫자 상한*을 건드린다 → **M5 task 생성 *전* Charter §5 scope-note 반영이 필수 선행(blocking gate)**: 상위(Charter) 승인 없이 하위 task 착수 금지(AGENTS.md "상위 문서 없이 하위 먼저 X"). scope-note 내용 = 공식 페이지 한정·티어드·소스별 게이트. **별도 ADR은 불필요**(검증된 A-1 재사용·가역적·"공식만"은 기존 ToS 연장이라 비가역 트레이드오프 없음 — 사용자 판단 2026-06-07). *Charter 편집 자체는 repair-plan 범위 밖 → 메인세션 별도 처리.*

## 0-1. Type
feature

## 1. 요약
수집 커버리지를 토스·당근 2곳 → **다수 IT기업 공식 채용 페이지**(네카라쿠배 자체 페이지 + 외국계 + 스타트업)로 확대한다. **애그리게이터(잡코리아·직행·원티드 등) 크롤링은 하지 않는다.** 회사마다 bespoke 크롤러를 쓰지 않도록 **ATS 어댑터 전략**(Greenhouse·Lever·Workday·Ashby 등 표준 ATS를 *ATS별 어댑터*로 묶어 커버리지를 곱셈 확장)을 우선하고, 티어드(대기업→외국계→스타트업)로 늘린다. 각 신규 소스는 **A-1형 게이트**(차단/구조변경/캡차 미관측)를 통과해야 커버리지 패널에 "수집 중"으로 승격된다.

범위 갱신: Charter §5 scope-note(M5 진입 시, 별도 ADR 불필요). 원 제약: Charter §5 "다채널 풀커버리지" 비목표(숫자 상한).

## 2. 사용자 가치 (User Story)
- As a **유진(신입/졸업예정 개발자 구직자)**, I want postings from many companies' official career pages in one feed, so that I miss fewer real opportunities while trusting that coverage is explicit(not aggregator noise).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 크롤러가 ATS 어댑터(예: Greenhouse)로 등록된 회사들의 공고를 수집 → `job_postings` upsert.
2. 자체 페이지 회사(네카라쿠배 등)는 회사별 어댑터로 수집.
3. 커버리지 패널에 수집 성공 소스 목록 + 마지막 성공 시각 노출(미수집은 명시).
### Alternate path
1. 일부 소스 일시 실패 → 그 소스만 "수집 실패/지연" 표기, 나머지는 정상(부분 커버리지 정직 고지).
### Fail path
1. 🔴 소스 구조 변경/차단 → 게이트가 감지 → 해당 소스 커버리지 강등 + 로그(조용한 실패·거짓 완전성 금지, Fail #3).
2. 🔴 애그리게이터를 실수로 추가 → 정책 위반(금지) — 코드/리뷰에서 차단.

## 4. 범위
- ATS 어댑터(공통 인터페이스 + Greenhouse/Lever/Workday/Ashby 등 N개) + 회사별 어댑터(자체 페이지).
- 소스 레지스트리(회사↔어댑터↔ATS 매핑) + 티어드 추가.
- 소스별 A-1형 게이트(차단/구조변경/캡차 감지) + 커버리지 패널 연동(소스별 상태·마지막 성공 시각).
- 정적 httpx 우선 → 필요 시 Playwright headless(ARCH §6).
- crawler 구조 국소 리팩토링(`crawler/sources/*` 어댑터 분리 — 동인 있는 수술적 리팩토링, ADR-101#amend).
- ToS/robots 준수 상시 원칙(공식 페이지만).

## 5. 비범위
- 애그리게이터(잡코리아·직행·원티드 등) — **영구 비범위**.
- 비개발 직군 공고 — Charter §5 비목표.
- 실 배포 cron 실가동 — M6(M5는 로컬/수동 트리거로 수집 검증).
- 알고리즘 변경 — F-021~023.

## 6. 요구사항
- **공식 채용 페이지에서만** 수집(정책). 소스별 게이트 통과해야 커버리지 승격.
- ATS 어댑터 우선(공수 절감) + 회사별 어댑터 보완.
- 부분 커버리지 정직 고지(커버리지 패널 — Fail #3 차단).
- 결정성: 수집 fixture/오프라인 모드로 무키 E2E 보존(M2 패턴).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** **ATS 어댑터 ≥1종 + 공식 소스 ≥3개**(검증 가능 최소치 — plan에서 상향 가능)에서 공고가 `job_postings`에 수집되고 커버리지 패널에 소스별 마지막 성공 시각이 노출된다.
- **FAC-2:** 신규 소스는 A-1형 게이트(차단/구조변경/캡차 미관측)를 통과해야 "수집 중"으로 승격된다.
- **FAC-3:** 일부 소스 실패 시 해당 소스만 "수집 실패/지연"으로 표기되고 "전부 수집" 거짓 인상이 없다(Fail #3).
- **FAC-4:** 애그리게이터 소스는 추가/수집되지 않는다(정책 가드).

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-062:AC-1, T-063:AC-1
- FAC-2 → T-062:AC-2
- FAC-3 → T-063:AC-2, T-063:AC-3
- FAC-4 → T-062:AC-3

## 8. Non-functional Requirements
- 운영성: 소스별 fetch 실패율·캡차율 로깅(M6 알람 토대).
- 유지보수: ATS 어댑터로 회사 추가 비용 최소화. 어댑터별 구조변경 회귀 테스트.
- 법무: ToS/robots 준수 상시(공식 페이지 한정).

## 8-1. UX 흐름 품질
(해당 없음 — 수집 레이어. 커버리지 표시는 F-018 CoveragePanel.)

## 9. 엣지 케이스
- 같은 회사가 자체 페이지 + ATS 양쪽 게시 → 중복제거(url 기준 + 회사·직무 휴리스틱).
- 외국계 영어 JD → 수집은 가능, fit 교차는 F-023에서 검증.
- ATS 페이지네이션/동적 렌더 → 어댑터별 처리(headless 승격).
- robots 비허용 소스 → 추가하지 않음.

## 10. 의존성
- 범위 갱신: Charter §5 scope-note(M5 진입 시, 별도 ADR 불필요).
- 연계: F-021(많아진 JD를 임베딩·prefilter로 받아내야 비용 폭증 방지) — 함께 가야 의미.
- F-018 CoveragePanel(소스 상태 표시).

## 11. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§5 다채널 비목표 — 반전, G3 커버리지)
- Discovery: [DISCOVERY](../../10-charter/DISCOVERY.md) (§12 A-1·A-11, F1·F2)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §3 Collector)
- 범위 갱신: Charter §5 scope-note(M5 진입 시, 별도 ADR 불필요) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)(크롤링 방식)

## 12. 열린 질문 (논의 전제)
- 1차 티어 목표 회사·ATS 우선순위 + 소스별 유지보수 부채 상한.
- 회사별 어댑터(자체 페이지)와 ATS 어댑터 비중.
- 중복제거 강화(회사·직무 정규화) 범위.
- (M5 핵심 변경 — 사용자 논의 후 task화.)
