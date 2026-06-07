# F-018-companion-feed-experience: 동반자 에이전트 피드 경험 (UX 1순위)

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
M2/M3가 기능 컴포넌트만 깐 피드를, [DESIGN.md](../../20-system/DESIGN.md)가 박은 **"포도 ai · 포지션 도착! 마스코트가 매일 아침 맞는 자리를 골라 배달하는 동반자"** 경험으로 끌어올린다. 진입 → GreetingCard(포도 인사+오늘의 카운트) → 단일 피드(중복제거 + 신규/마감 diff + arrival 모션) → JobCard(적합도 5단계 배지 + FitScoreRing + 근거 펼침: JD 인용 + 이력서↔JD 매핑) → 커버리지 패널. **로딩·에러·empty·보류를 DESIGN.md §7-4 8-상태 매트릭스대로 일급으로**(포도가 안내) + 접근성 + lottie(arrival·로딩 등 *의미 전달*에 한정, 장식 금지) + 온보딩(첫 진입). **이 feature에 M4 task 비중을 가장 크게 둔다.** 뻔한 SaaS가 아니라 *나만의 맞춤형 취업 에이전트*로 느껴지게.

근거 insight: I-2(5단계 밴드)·I-3(누락0 투명성) — DISCOVERY §15.

## 2. 사용자 가치 (User Story)
- As a **유진(신입/졸업예정 개발자 구직자)**, I want a feed that feels like a personal job-hunting companion (포도) delivering today's fitting roles with honest reasons, so that I trust the recommendations and decide apply/skip quickly without feeling like I'm using a cold generic tool.

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 로그인(F-016) 후 피드 진입 → GreetingCard에 포도 + "오늘 신규 N건 / 마감 임박 M건".
2. 신규 공고가 arrival 모션(fade+translateY, stagger)으로 "도착"하며 렌더.
3. 각 JobCard: 출처(토스/당근)·직무·회사 + FitScoreRing + 적합도 5단계 PassBand + 마감 D-day.
4. 카드 펼침 → EvidenceBlock: JD 인용(grounding span 강조) + 이력서↔JD 매핑(✓ ok / △ gap).
5. 마감 임박 섹션에서 D-1 긴급 강조 → 우선순위 판단.
6. (F-019로) 지원/스킵·즐겨찾기.
### Alternate path
1. 추천 점수가 전반적으로 낮은 날 → 정직하게 보통/낮음 밴드 표시 + 근거(부족 요건) 명시(과약속 금지).
2. 신규가 빈약한 날(2~3건) → EmptyState "오늘은 신규가 적어요"(포도) + 최근 7일 미처리 재노출.
3. 첫 진입(이력서 없음) → 온보딩: 포도가 업로드를 안내(F-015 경로로).
### Fail path
1. 🔴 LLM miss/근거 부족 공고 → 가짜 점수 대신 **PendingState(보류)**: 포도 + dashed 카드 + 정직한 메시지 + 원문 링크.
2. 🔴 수집 실패/커버리지 degraded → **ErrorState**를 숨기지 않고 노출(CoveragePanel "수집 실패" danger — Fail #3 차단).
3. 🟡 채점 진행 중 → **LoadingState** skeleton + ring indeterminate(가짜 점수 절대 금지).

## 4. 범위
- Next.js App Router 피드(`/`): GreetingCard · 단일 피드 가상화(커서 페이지네이션) · 섹션(마감 임박 / 오늘의 추천).
- 컴포넌트(DESIGN.md §7): JobCard · FitScoreRing(arc=fenced gradient) · PassBand(5단계) · EvidenceBlock · DeadlineRow · GreetingCard · CoveragePanel · PodoStamp(높음↑ 티어 chrome) · Toast.
- **8-상태 매트릭스(§7-4) 전 컴포넌트 정의** — 특히 loading/error/empty/보류 일급화(M2 REV-M2-UI-001 회수).
- **신규/마감 diff 렌더** — `diff_status`(crawler set) 읽어 신규/마감 표식(cron 실가동은 M6, 데이터는 수동/로컬 크롤 시드).
- **마스코트·모션·lottie**: 포도 PNG + arrival 모션(§8) + lottie(arrival·로딩 등 의미 전달 한정) + `prefers-reduced-motion` 분기.
- **온보딩**: 첫 진입(이력서/세션 기준) 안내 흐름.
- **접근성(DSN-M3-001~003 회수)**: label/aria-busy/role=region + 키보드 + band 텍스트=`band-*-ink`.
- DESIGN.md 토큰만(raw hex 금지) + fenced 그라데이션 3곳 규율.
- 데이터는 NestJS `recommendations`(정렬 projection) + `ranking_runs.result`(JSONB pass-through, web은 표시만).

## 5. 비범위
- 직군 분리 탭 — 도메인 자동분류(M5) 의존 → M4 보류(단일 피드).
- 알림(오전 푸시/이메일) 발송 — M6+ 비범위(피드 내 "신규 도착" 표시까지만).
- 지원/즐겨찾기 *기록·영속* — F-019(본 feature는 액션 트리거 UI까지).
- 이력서 업로드 화면 자체 — F-015(M3) 재사용/연결.
- 새 스코어링·출력계약 변경 — 동결.

## 6. 요구사항
- DESIGN.md §1 5원칙 준수: 따뜻한 chrome/엄격한 data, fenced 그라데이션, 랭킹·근거 한 시선, 정직한 보류/빈 상태 일급, 모션='도착' 의미만.
- 점수·밴드·근거 텍스트에 마스코트/그라데이션/이모지 장식 금지(원칙 1). PodoStamp는 카드 chrome에만.
- 가짜 점수 금지 — miss는 PendingState(원칙 4 / GS-2).
- CoveragePanel 상시 노출(Fail #3 차단).
- 색만으로 의미 전달 금지 — 밴드·매핑 항상 텍스트 라벨(+✓/△).
- 모든 모션 `prefers-reduced-motion` 분기. 단일 컬럼 max-width 430px(§4).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** 로그인 후 피드 진입 시 GreetingCard(포도 + 신규/마감 카운트)와 적합도 5단계 배지·근거 펼침이 있는 JobCard가 렌더된다.
- **FAC-2:** LLM miss/근거 부족 공고는 숫자 대신 PendingState(보류)로 렌더되고 가짜 점수가 표시되지 않는다.
- **FAC-3:** 수집 실패 시 CoveragePanel이 "수집 실패"(danger)를 노출하고 "전부 수집" 거짓 인상을 주지 않는다(Fail #3).
- **FAC-4:** empty(신규 적음)·loading(skeleton)·error 상태가 DESIGN.md §7-4 매트릭스대로 렌더되고 포도 톤으로 안내된다.
- **FAC-5:** 접근성 — 파일/버튼 label·aria-busy·role=region·키보드 포커스·band 텍스트 대비(AA)가 핵심 화면에서 단언된다(DSN-M3-001~003 회수).
- **FAC-6:** 모든 모션(arrival·ring draw·lottie)에 `prefers-reduced-motion: reduce` 분기가 적용된다.
- **FAC-7:** raw hex 0 — 색상은 DESIGN.md §2 토큰(CSS 변수)만 참조하고 fenced 그라데이션이 §2-4 3곳 외에 등장하지 않는다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-046:AC-1, T-047:AC-1, T-047:AC-2
- FAC-2 → T-047:AC-3
- FAC-3 → T-046:AC-2
- FAC-4 → T-046:AC-3, T-046:AC-4, T-048:AC-3
- FAC-5 → T-047:AC-2, T-049:AC-1
- FAC-6 → T-048:AC-1, T-048:AC-2
- FAC-7 → T-047:AC-1, T-049:AC-2

## 8. Non-functional Requirements
- 성능: 피드 진입은 저장된 결과 읽기(LLM 지연 분리). 리스트 가상화로 긴 목록 부드럽게.
- 접근성: Lighthouse Accessibility ≥90(목표). 키보드 전 흐름 도달.
- i18n: 한국어 우선(Pretendard). 다국어 비범위.

## 8-1. UX 흐름 품질
- **primary task:** 진입 → 상위 추천 스캔 → 펼쳐 근거 확인 → 지원/스킵 결정.
- **empty 흐름:** 신규 적음 → "오늘은 신규가 적어요"(포도) + 최근 7일 재노출. 이력서 없음 → 온보딩 업로드 유도.
- **loading 흐름:** 채점 진행 → skeleton 카드 + ring indeterminate. 가짜 점수 금지.
- **error 흐름:** 수집/채점 실패 → ErrorState 노출(포도 "아침 배달이 늦어요" 톤 + 사실 명확) + 재시도.
- **accessibility:** 카드 키보드 포커스·펼침, 보류/빈/에러 상태 스크린리더 안내, band 색+라벨 동반.
- **copy 톤:** 포도 동반자 톤("포도가 오늘의 자리를 골라왔어요!")이되 점수·근거는 정직.
- **success metric (HEART):** Engagement → 주간 활성 복귀율(오전 진입) / Task success → 추천 펼침→지원 결정 전환율(실 배포 후 이벤트 로그, DISCOVERY §14 회수).

## 9. 엣지 케이스
- 전 공고 보류(무키/키 미보유) → 피드가 PendingState로 가득(정직), 가짜 점수 0.
- 긴 이력서·다수 공고 → 가상화로 성능 유지.
- 마감 지난 공고 → 마감 섹션 정리 또는 dim 처리.
- reduced-motion 사용자 → 모션 제거, opacity fade만.
- 동일 공고 중복 노출(중복제거 실패) → 가독성 저하(수용 가능 Fail #6)이나 회귀 단언.

## 10. 의존성
- 선행: F-016(세션/보호 라우트), F-017(채점 상태→LoadingState/피드 갱신).
- 연결: F-015(M3 업로드 화면) → 온보딩/이력서 경로. F-019(지원/즐겨찾기 액션).
- 데이터: NestJS feed/coverage 서빙(M2 F-009/F-010) + diff_status.
- **DESIGN §8-1 Lottie 규칙** — 반영됨. lottie 사용은 §8-1 준수(미반영/실패 시 CSS 모션 대체, 차단 아님).

## 11. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§8 흐름1·2, §3.1 시나리오)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4), [## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components), [## 2 Colors](../../20-system/DESIGN.md#design-2-colors), [## 8 Motion](../../20-system/DESIGN.md#design-8-motion), [## 9 Do's and Don'ts](../../20-system/DESIGN.md#design-9-donts)
- ADR: [ADR-049](../../90-decisions/boilerplate/ADR-049-concept-mockup-first-design.md) · [ADR-042](../../90-decisions/boilerplate/ADR-042-ux-flow-quality.md) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 12. 열린 질문
- **lottie 규칙 = DESIGN §8-1 반영됨**(라이브러리 `@lottiefiles/dotlottie-react`·`.lottie` 포맷·Next.js `dynamic ssr:false`·reduced-motion 정적 프레임 대체·성능 예산 ≤50KB/동시≤2·금지 범위). UI task는 §8-1 준수. lottie 미반영/로드 실패 시 **CSS arrival로 graceful fallback**(차단 아님). 에셋(포도 lottie 제작/변환)은 task에서.
- 온보딩 범위(1회 코치마크 vs 빈 피드 인라인 안내) — 단순성 우선.
- FitScoreRing 0~100 숫자 vs 5단계 라벨 노출 균형(DESIGN §7-2 ink 숫자) — design.
- 첫 진입 "이력서 먼저" 상태와 F-015 업로드 화면의 연결 방식(라우팅).
