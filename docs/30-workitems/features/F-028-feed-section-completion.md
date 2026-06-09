# F-028-feed-section-completion

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
피드를 **피로 최소 정보구조(IA, M7 §2-A-1)**로 재구성한다: 마감 임박 전용 섹션 신설, deep 분석 전 공고(CoarseSection)를 접힌 보조로 하단 마운트, 신규 적은 날 최근 7일 미처리 재노출, 커버리지를 compact strip으로. "무엇을 보여주고 무엇을 숨길지"를 페르소나(공고 과부하 신입)의 *오늘의 결정*에 맞춰 위계화한다. 근거: Charter §3.1 Happy#5·Alt#4 / DESIGN §7-3.

## 2. 사용자 가치 (User Story)
- As 유진(Charter §2.1), I want 마감 임박 공고를 추천과 분리해 먼저 보고 싶다, so that 마감을 놓치지 않는다(Fail#4 회피).
- As 유진, I want 피드가 한눈에 정리돼 압도되지 않기를 바란다, so that 매일 부담 없이 복귀한다.

## 3. 핵심 시나리오 (Feature-level)
- **happy**: 진입 → GreetingCard로 오늘 요약 → 마감 임박 N건 먼저 처리 → 오늘의 추천 상위 N 펼쳐 결정 → 더 보고 싶으면 "더 보기" / 하단 coarse 펼침.
- **alternate**: 신규 적은 날 → "오늘은 적어요" + "최근 7일 미처리 다시 보기" 클릭 → 미처리 재노출.
- **fail**: closing_at 미수집이라 마감 데이터 없음 → 마감 섹션 *숨김*(가짜 채움 금지). 커버리지 일부 실패 → compact strip이 degraded 경고로 펼침.

## 4. 범위
- 마감 임박 전용 섹션(추천 위, 상위 3~5 캡) — `?section=expiring`(또는 closing_at 정렬) 소비.
- 피드 IA 세로 순서(greeting→coverage strip→tabs→마감→추천→coarse) + 점진적 노출.
- CoarseSection을 피드 하단에 *접힌* 상태로 마운트(현재 import 0).
- 최근 7일 미처리 재노출 액션(현재 카피만).
- CoveragePanel을 compact strip(1줄, 펼침 가능)로.

## 5. 비범위
- closing_at **크롤러 수집**(데이터 생산) — 크롤러 작업, M7 §7 결정(권장 이연). 본 feature는 *소비/표시*만.
- 공고 검색·정렬 UI(M7 비범위).
- 피드 알고리즘/랭킹 변경(M5 동결).

## 6. 요구사항
- 마감 섹션은 closing_at 데이터 없으면 숨김(정직). 데이터 생기면 자동 노출.
- coarse·근거·커버리지 상세는 기본 접힘(점진적 노출). 한 화면 primary CTA 1개(DESIGN §9).
- fit 점수/밴드는 deep 추천에만 — coarse·마감 섹션 mini 표기 시에도 가짜 점수 금지(ADR-108).

## 7. Feature-level Acceptance Criteria
- FAC-1 마감 임박 공고가 추천과 분리된 전용 섹션으로 긴급 우선 노출(데이터 있을 때), 없으면 숨김.
- FAC-2 피드가 피로 최소 IA(순서·캡·점진노출·커버리지 compact)를 준수한다.
- FAC-3 deep 분석 전(coarse) 공고가 배지 없이 접힌 보조로만 노출된다.
- FAC-4 신규 적은 날 최근 7일 미처리 재노출로 빈 피드를 방지한다.

## 7-1. FAC ↔ AC 매핑표
- FAC-1 → T-090:AC-1
- FAC-2 → T-090:AC-2, T-090:AC-3, T-091:AC-1
- FAC-3 → T-091:AC-1, T-091:AC-2
- FAC-4 → T-092:AC-1, T-092:AC-2

## 8. Non-functional Requirements
- 성능: 피드 진입 = 저장 결과 읽기(LLM 분리, ARCH §8). 추가 섹션도 커서/캡으로 과fetch 금지.
- 보안: 보호 라우트 — 모든 fetch `credentials:'include'`(교차출처 세션).

## 8-1. UX 흐름 품질
- primary task: 오늘의 추천 상위에서 지원/스킵 결정 1행동.
- empty/loading/error: 마감/coarse 빈=숨김, 추천 빈="오늘은 적어요"+재노출, 커버리지 실패=degraded 펼침. 로딩=skeleton(가짜 점수 0).
- accessibility: 섹션 heading 시맨틱, 펼침 토글 aria-expanded, 키보드 도달.
- copy 톤: 포도 동반자("아직 깊이 안 본 공고예요 — 원하면 분석할게요").
- success metric(HEART-Engagement): 피드 스크롤 깊이/이탈 — 과도 스크롤 없이 상위에서 결정(정성). 실데이터로 DISCOVERY §14 회수.

## 9. 엣지 케이스
- closing_at 전부 null → 마감 섹션 미렌더(빈 헤더 노출 금지).
- coarse 0건 → CoarseSection null(현재 동작 유지).
- 추천 0 + 신규 0 → EmptyState + 재노출 액션.

## 10. 의존성
- 기존 feed API(`?section`/`?cursor`/`?domain`), CoarseSection(T-065), CoveragePanel(T-063).
- closing_at 데이터(미충족) — 마감 섹션은 그때까지 빈 상태.

## 11. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) · [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md) · ADR-110(피드 IA, 신설 권장)

## 12. 열린 질문
- closing_at 데이터 수집(크롤러) 포함 vs 이연 — M7 §7.
- 마감 섹션 cut-off(D-day ≤ N) 및 추천 대비 정렬 우선순위.
- 최근7일 재노출 = 별 섹션 vs EmptyState 인라인 액션.
