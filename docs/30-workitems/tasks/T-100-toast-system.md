# T-100-toast-system

## 0. Status
done

## 0-1. Type
refactor

## 1. 작업 목적
`JobCardActions`의 인라인 toast를 재사용 가능한 `Toast` 컴포넌트로 통일한다(DESIGN §7-2). **외부 행동 불변** — 기존 피드백 동작 보존, 구조만 개선.

## 2. 작업 범위
신규 Toast 컴포넌트 + JobCardActions 치환. 라이브러리 도입 제외(자체 최소).

## 3. 구현 항목
1. 신규 `podo/apps/web/components/Toast.tsx` — 현재: 없음 → 변경: `role="status"` `aria-live="polite"` 라벨 토스트(메시지 prop, 자동 dismiss). 색만 의존 금지(텍스트 라벨). DESIGN 토큰. → 확인: 렌더·a11y (AC-1).
2. `podo/apps/web/components/JobCardActions.tsx:75-116` — 현재: `setToast` 인라인 state + 인라인 markup → 변경: `<Toast message={toast}/>`로 치환. 지원/스킵/즐겨찾기 메시지·타이밍 동작 보존(행동 불변). → 확인: 기존 동작 동일 (AC-1).

## 4. 제외 항목
- Toast 큐/스택 라이브러리. 신규 알림 채널.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/components/Toast.tsx` (신규 — output role=status + aria-live=polite + 자동 dismiss)
- `podo/apps/web/components/JobCardActions.tsx` (인라인 toast → <Toast/> 치환, 행동 불변)
- `podo/apps/web/test/toast.spec.tsx` (신규 — AC-1)

## 5. 완료 조건
지원/스킵/즐겨찾기 피드백이 공용 Toast(role=status)로 표시되며 기존 동작이 동일하다.

## 6. Acceptance Criteria
- AC-1 [Given] 지원/스킵/즐겨찾기 액션 [When] 결과 수신 [Then] 공용 Toast 컴포넌트(role=status, aria-live)가 동일한 메시지·동작으로 피드백을 표시한다(행동 불변, 기존 spec 통과).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/toast.spec.tsx > test_AC_1_toast_feedback_behavior_preserved

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-032-motion-and-polish](../features/F-032-motion-and-polish.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-006](../../90-decisions/boilerplate/ADR-006-simplicity-and-architecture.md)(surgical change)

## 8. 메모
- refactor: 외부 행동 불변(JobCardActions 기존 spec 그대로 통과) + 인라인→컴포넌트 구조 개선만. 범위 밖 변경 금지(ADR-006).

## 9. 의존성
- depends_on: []
- write_set: ["podo/apps/web/components/Toast.tsx", "podo/apps/web/components/JobCardActions.tsx"]
