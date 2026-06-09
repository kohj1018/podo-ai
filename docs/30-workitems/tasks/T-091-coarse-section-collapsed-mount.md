# T-091-coarse-section-collapsed-mount

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
구현돼 있으나 어디에도 import되지 않아 죽어 있는 `CoarseSection`(M5 T-065)을 피드 최하단에 **접힌 보조**로 마운트한다(피로 최소 IA §2-A-1 ⑥).

## 2. 작업 범위
프론트만 — CoarseSection 접힘 토글화 + 피드 하단 마운트. 배지 0 불변식(ADR-108) 보존.

## 3. 구현 항목
1. `podo/apps/web/components/CoarseSection.tsx:51-68` — 현재: 데이터 있으면 `<ul>`을 항상 펼쳐 렌더 → 변경: 기본 **접힘** + `<button aria-expanded>` "아직 깊이 안 본 공고 N개 · 펼치기" → 펼치면 기존 목록. `page.items.length`로 N 표기. coarse 0이면 기존대로 `return null`. → 확인: 접힌 진입, 펼치면 목록 (AC-1).
2. `podo/apps/web/app/page.tsx:46-61` — 현재: `<FeedView/>`가 마지막 → 변경: `<FeedView/>` **아래에 `<CoarseSection/>`** 추가(최하단 보조). → 확인: 하단 렌더 (AC-1).
3. `CoarseSection` 항목 행 유지 — 회사·직무만(`fit_level`/PassBand/FitScoreRing 요소 없음). → 확인: 배지 0 (AC-2).

## 4. 제외 항목
- coarse 커서 페이지네이션 확장(현 1페이지 유지).
- 마감 섹션·커버리지(T-090).

## 4-1. 변경 예정 파일/경로

## 5. 완료 조건
CoarseSection이 피드 하단에 접힌 진입으로 뜨고, 펼치면 배지 없는 공고 목록을 보여준다(coarse 0이면 미렌더).

## 6. Acceptance Criteria
- AC-1 [Given] coarse 후보가 있을 때 [When] 피드 하단 [Then] CoarseSection이 "N개 · 펼치기" 접힌 진입으로 마운트되고, 토글 시 목록을 보여준다. coarse 0건이면 섹션이 렌더되지 않는다.
- AC-2 [Given] CoarseSection 펼침 [When] 항목 렌더 [Then] FitScoreRing/PassBand/fit 배지 요소가 0개다(ADR-108 D3).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/coarse_section.spec.tsx > test_AC_1_collapsed_mount_and_expand
- AC-2 → podo/apps/web/test/coarse_section.spec.tsx > test_AC_2_no_fit_badges

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-028-feed-section-completion](../features/F-028-feed-section-completion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md)

## 8. 메모

## 9. 의존성
- depends_on: [T-090]
- write_set: ["podo/apps/web/components/CoarseSection.tsx", "podo/apps/web/app/page.tsx"]
- 비고: `app/page.tsx`를 T-090과 공유 → 같은 worktree 동시 implement 비권장(순차).
