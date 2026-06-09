# F-031-onboarding-and-loading-ux

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
신규 사용자가 **회원가입/최초 로그인 직후 이력서가 없으면 바로 /resume로 진입**하도록 온보딩 동선을 강화하고(현재는 피드 인라인 `<Onboarding/>`), **모든 로딩 지점에 일관된 로딩 UI/UX**를 정비한다(가짜 점수 절대 미표시). 근거: M7 §2-B(신규 진입)·§2-F(로딩 정비) / DESIGN §7-4·§8-1.

## 2. 사용자 가치 (User Story)
- As 유진(Charter §2.1), I want 처음 들어오면 곧장 이력서를 쓰게 안내받고 싶다, so that 헤매지 않고 시작한다.
- As 유진, I want 분석·로딩 중에 무엇이 일어나는지 보이길 바란다, so that 멈춘 줄 알고 이탈하지 않는다.

## 3. 핵심 시나리오 (Feature-level)
- **happy**: 최초 로그인 → 이력서 없음 → /resume 자동 진입 → 작성 → 피드.
- **alternate**: 이력서 있는 사용자 로그인 → 피드 정상(리다이렉트 없음).
- **fail**: 세션 체크/피드/업로드 로딩 → skeleton·indeterminate 노출(가짜 점수 0), 실패 시 에러 상태.

## 4. 범위
- 인증됐으나 이력서 없는 사용자의 진입 리다이렉트(/→/resume).
- 온보딩 카피/동선 강화(이력서 없는 사용자 안내).
- 전 로딩 지점 로딩 UI 정비: 피드 meta/리스트/커서, 업로드·마스킹·채점 대기, 세션 체크(AuthGate), 활동 뷰, 마이페이지.
- reduced-motion 분기 일관화.

## 5. 비범위
- 알림(인앱/푸시) — M7 §4.
- 다단계 온보딩 튜토리얼/코치마크 — 단순성(M7 §2-E는 동선 보강만).

## 6. 요구사항
- **가짜 점수/preview 절대 금지**(GS-2) — 로딩 중 숫자 대신 skeleton/indeterminate.
- 리다이렉트는 깜빡임 최소(loading 상태 동안 placeholder).
- 모든 모션 `prefers-reduced-motion` 분기(DESIGN §8).

## 7. Feature-level Acceptance Criteria
- FAC-1 신규(이력서 없는) 사용자가 진입 즉시 이력서 작성(/resume)으로 안내된다.
- FAC-2 모든 주요 로딩 지점이 가짜 점수 없이 로딩 UI를 제공하고 reduced-motion을 분기한다.

## 7-1. FAC ↔ AC 매핑표
- FAC-1 → T-097:AC-1, T-097:AC-2
- FAC-2 → T-098:AC-1, T-098:AC-2

## 8. Non-functional Requirements
- 접근성: 로딩 상태 `aria-busy`/`role=status`, reduced-motion.
- 성능: 리다이렉트 판정 fetch 1회(불필요 중복 호출 금지).

## 8-1. UX 흐름 품질
- primary task: 신규는 "이력서 작성 시작", 기존은 "오늘의 추천 보기".
- empty/loading/error: 로딩=skeleton/indeterminate, 빈=온보딩 안내, 실패=에러+재시도.
- accessibility: aria-live 로딩 안내, 포커스 이동.
- copy 톤: "이력서를 올리면 포도가 시작해요".
- success metric(HEART-Task success): 신규 진입→이력서 작성 시작률 ≥ 목표(실데이터).

## 9. 엣지 케이스
- 리다이렉트 루프 방지(/resume에서 또 판정하지 않게).
- 이력서 막 제출 후 채점 대기 중 진입 → scoring 상태 skeleton(redirect 아님).
- 세션 만료 중 로딩 → /login 가드(AuthGate)와 충돌 없게.

## 10. 의존성
- SessionProvider/AuthGate(세션) · feed/meta(has_resume) · globals.css(.shimmer).

## 11. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-107](../../90-decisions/project/ADR-107-oauth-multiuser.md)(세션/리다이렉트)

## 12. 열린 질문
- 리다이렉트 위치: 로그인 콜백 vs 피드 페이지 client 가드(권장: feed/meta has_resume 기반 client 가드).
- 로딩 정비를 공용 Skeleton/Spinner primitive로 추출할지(3회 반복 시, AGENTS YAGNI).
