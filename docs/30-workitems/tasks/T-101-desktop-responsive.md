# T-101-desktop-responsive

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
데스크톱 폭에서 레이아웃이 깨지지 않도록 반응형을 마감한다 — **단일 중앙 컬럼 유지**(DESIGN §4, 멀티컬럼 미사용).

## 2. 작업 범위
컨테이너 폭/여백 정돈(globals.css/layout). 멀티컬럼·새 레이아웃 제외.

## 3. 구현 항목
1. `podo/apps/web/app/globals.css` — 현재: 각 컴포넌트가 `maxWidth:430px` 인라인 분산 → 변경: 컨테이너 폭/패딩을 토큰/유틸로 통일(단일 중앙 컬럼, 데스크톱에서 폭 소폭 증가만 — DESIGN §4 "가로 확장은 컬럼 폭 소폭 증가"). → 확인: 데스크톱 중앙 정렬·여백 (AC-1).
2. `podo/apps/web/app/layout.tsx` — 현재: 루트 레이아웃 → 변경: 중앙 컬럼 컨테이너 래핑(필요 시). brand 그라데이션 3곳 fence 유지(DESIGN §2-4). → 확인: 레이아웃 깨짐 0 (AC-1).

## 4. 제외 항목
- 멀티컬럼/데스크톱 전용 레이아웃. 모바일 동작 변경.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/app/globals.css` (--app-max-width 토큰 + 1024px 미디어쿼리 480px + .app-shell 중앙 컬럼)
- `podo/apps/web/app/layout.tsx` (app-shell로 AppHeader+children 래핑)
- `podo/apps/web/test/responsive.spec.tsx` (신규 — AC-1 CSS·layout 계약 감사)

## 5. 완료 조건
데스크톱 폭에서 단일 중앙 컬럼이 유지되고 폭/여백이 정돈돼 레이아웃이 깨지지 않는다.

## 6. Acceptance Criteria
- AC-1 [Given] 데스크톱 뷰포트(예: ≥1024px) [When] 피드·resume·마이페이지 렌더 [Then] 단일 중앙 컬럼이 유지되고(과도 확장 없이) 콘텐츠가 좌측 정렬·중앙 배치되며 레이아웃이 깨지지 않는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/responsive.spec.tsx > test_AC_1_desktop_single_column

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-032-motion-and-polish](../features/F-032-motion-and-polish.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 4 Layout](../../20-system/DESIGN.md) · [## 2 Colors](../../20-system/DESIGN.md#design-2-colors)
- ADR: —

## 8. 메모

## 9. 의존성
- depends_on: []
- write_set: ["podo/apps/web/app/globals.css", "podo/apps/web/app/layout.tsx"]
