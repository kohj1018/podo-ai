# T-098-loading-ux-pass

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
모든 주요 로딩 지점에 일관된 로딩 UI(skeleton/indeterminate)를 정비한다 — **가짜 점수 절대 미표시**(GS-2), reduced-motion 분기(§2-F).

## 2. 작업 범위
프론트 로딩 상태 보강(피드·세션·활동 뷰·마이페이지·커버리지). 신규 기능 제외.

## 3. 구현 항목
1. `podo/apps/web/components/AuthGate.tsx:22-36` — 현재: "불러오는 중…" 텍스트 placeholder → 변경: skeleton/spinner(`role=status`, `aria-busy`) 유지·정돈. → 확인 (AC-1).
2. `podo/apps/web/components/CoveragePanel.tsx` — 현재: "수집 현황 불러오는 중…" 텍스트 → 변경: compact strip(T-090) 로딩 skeleton. → 확인 (AC-1).
3. 활동 뷰(T-094 ActivityList)·마이페이지(T-093)·resume 업로드(기존 shimmer 유지) 로딩 상태 일관화 — 변경: 공통 패턴(skeleton + `.shimmer` globals.css 재사용). 가짜 점수/preview 0. → 확인 (AC-1).
4. reduced-motion — 변경: 모든 로딩 모션이 `@media (prefers-reduced-motion: reduce)`에서 정적(globals.css `.shimmer` 이미 분기). 신규 spinner도 분기. → 확인 (AC-2).
5. (선택) 3회 이상 반복 시 공용 `Skeleton`/`Spinner` 추출(AGENTS YAGNI — 3회 전 추출 금지).

## 4. 제외 항목
- 신규 surface 기능. 데이터 로딩 성능 최적화.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/components/AuthGate.tsx` (로딩 텍스트 → shimmer skeleton + aria-busy)
- `podo/apps/web/components/CoveragePanel.tsx` (로딩 텍스트 → compact strip shimmer skeleton + aria-busy)
- `podo/apps/web/components/ActivityList.tsx` (기존 shimmer 로딩에 aria-label 일관화)
- `podo/apps/web/test/loading_ux.spec.tsx` (신규 — AC-1/AC-2)
- (무변경) `globals.css` — .shimmer reduced-motion 분기 기존재, 신규 skeleton도 .shimmer 재사용이라 불필요

## 5. 완료 조건
주요 로딩 지점이 가짜 점수 없이 일관된 로딩 UI를 보여주고 reduced-motion을 분기한다.

## 6. Acceptance Criteria
- AC-1 [Given] 피드/세션/활동 뷰/마이페이지 로딩 중 [When] 렌더 [Then] skeleton/indeterminate 로딩 UI가 표시되고 가짜 점수·preview는 표시되지 않는다.
- AC-2 [Given] `prefers-reduced-motion: reduce` [When] 로딩 [Then] 모든 로딩 모션이 정적으로 분기된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/loading_ux.spec.tsx > test_AC_1_loading_indicators_no_fake_score
- AC-2 → podo/apps/web/test/loading_ux.spec.tsx > test_AC_2_reduced_motion

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-031-onboarding-and-loading-ux](../features/F-031-onboarding-and-loading-ux.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components) · [## 8 Motion](../../20-system/DESIGN.md#design-8-motion)
- ADR: —

## 8. 메모
- repair-plan 2026-06-10 [default] P1 Plan-dep: Adopt — T-097 신규 리다이렉트 placeholder/깜빡임 상태도 로딩 정비 대상 → depends_on에 T-097 추가.

## 9. 의존성
- depends_on: [T-090, T-093, T-094, T-095, T-097]
- write_set: ["podo/apps/web/components/AuthGate.tsx", "podo/apps/web/components/CoveragePanel.tsx", "podo/apps/web/components/ActivityList.tsx", "podo/apps/web/app/globals.css"]
- 비고: surface(T-090/093/094/095) + 리다이렉트 placeholder(T-097) 존재 후 정비.
