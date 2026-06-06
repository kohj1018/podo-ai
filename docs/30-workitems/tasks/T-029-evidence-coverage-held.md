# T-029-evidence-coverage-held

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
피드 공고의 **근거 펼침**(JD 인용 + 이력서↔JD 매핑) · **커버리지 투명성 패널** · **LLM 보류 상태**를 구현한다. 근거는 `ranking_runs.result`(opaque)에서 *표시 전용*으로 해석하고, 보류는 가짜 점수 대신 보류 표시("틀린 것보다 없는 게 낫다").

## 2. 작업 범위
- 근거 펼침: `EvidenceBlock`(DESIGN §7-2 재사용) — 피드 항목 `evidence`(=`result` opaque)에서 JD 인용 + 매핑 표시(비즈니스 분기 X, §7-4).
- 커버리지 패널: `GET /api/v1/coverage` 소비 — 수집/미수집 채널 + 마지막 성공 시각(`coverage.*` 토큰).
- 보류 상태: `status='held'` 항목 → 보류 표시(가짜 점수 X).

## 3. 구현 항목
1. `podo/apps/web/components/EvidenceBlock.tsx` — 현재: 없음 → 변경: **DESIGN §7-2 EvidenceBlock 재사용** — 펼침 시 항목 `evidence`(result opaque)에서 JD 인용 + 이력서↔JD 매핑 렌더(표시 전용 — 내부 구조로 분기 금지, §7-4). → 확인: `test_AC_1` 펼침 시 인용+매핑 표시. (AC-1)
2. `podo/apps/web/components/CoveragePanel.tsx` — 현재: 없음 → 변경: `GET /api/v1/coverage` fetch → "수집: 토스·당근 / 마지막 성공 hh:mm" + 미수집 명시. `coverage.on` 등 토큰(raw hex 금지). → 확인: `test_AC_2` 채널+시각 렌더. (AC-2)
3. `JobCard`(T-028) 보류 분기 — `status==='held'` → 점수/배지 대신 **보류 상태**(예: "점수 보류 — 재시도 예정"), 가짜 점수 렌더 0. → 확인: `test_AC_3` held 항목에 점수/band 미표시. (AC-3)
4. 접근성 — 밴드·보류는 색+텍스트 라벨(+아이콘) 동반(DESIGN §2-5), 키보드 펼침/포커스(§7-4 focus). → 확인: 라벨 존재 단언. (AC-1)

## 4. 제외 항목
- 피드 목록/정렬/커서(T-028) · API(T-026/027) · 인증 · 즐겨찾기/지원기록.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/components/EvidenceBlock.tsx`, `podo/apps/web/components/CoveragePanel.tsx`, `podo/apps/web/components/JobCard.tsx`, `podo/apps/web/app/page.tsx`, `podo/apps/web/test/evidence_coverage.spec.tsx`

## 5. 완료 조건
공고 펼침이 JD 인용+매핑을 표시하고, 커버리지 패널이 수집/미수집+마지막 시각을 표시하며, 보류 공고는 가짜 점수 없이 보류로 표시된다.

## 6. Acceptance Criteria
- AC-1 [Given] `result` evidence가 있는 공고 [When] 펼침 [Then] `EvidenceBlock`이 JD 원문 인용 + 이력서↔JD 매핑을 표시 전용으로 렌더한다(내부 구조로 비즈니스 분기 0).
- AC-2 [Given] `GET /api/v1/coverage` 응답 [When] 패널 렌더 [Then] 수집 채널(토스·당근)·미수집 채널·채널별 마지막 성공 시각이 표시된다.
- AC-3 [Given] `status='held'` 공고 [When] 피드 렌더 [Then] 가짜 점수/배지 대신 보류 상태가 표시된다(점수·band 미표시).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/evidence_coverage.spec.tsx::test_AC_1_evidence_expand_shows_citation_mapping
- AC-2 → vitest::podo/apps/web/test/evidence_coverage.spec.tsx::test_AC_2_coverage_panel_renders
- AC-3 → vitest::podo/apps/web/test/evidence_coverage.spec.tsx::test_AC_3_held_shows_pending_not_fake

## 6-2. TDD opt-out
<!-- TDD 적용 — API mock + Testing Library. -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-010-feed-coverage-ui](../features/F-010-feed-coverage-ui.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4) (근거 펼침·커버리지 패널·보류 표현)
- Design: [DESIGN ## 2 Colors](../../20-system/DESIGN.md#design-2-colors) (coverage 토큰·§2-5 대비) · [## 7 Components](../../20-system/DESIGN.md#design-7-components) (EvidenceBlock·CoveragePanel 재사용)
- ADR: [ADR-042](../../90-decisions/boilerplate/ADR-042-ux-flow-quality.md)

## 8. 메모
- DESIGN cross-check: EvidenceBlock·CoveragePanel 재사용(신규 primitive X). coverage 토큰 사용, raw hex 0.
- 해석 확정: 근거는 `result` opaque에서 *표시 전용* 해석(§7-4 — web은 비즈니스 분기에 안 씀). 보류 = Charter thesis("없는 게 틀린 것보다 낫다").
- repair-plan 2026-06-06 [default] P0 Plan-FAC-coverage: Adopt — held 행(status='held', fit_level null)을 보류 배지로 렌더(T-022 projection·T-026 feed 정합).

## 9. 의존성
- depends_on: [T-026, T-027, T-028]   # T-028과 JobCard.tsx/page.tsx write_set 교집합 → 같은 wave 금지(순차)
- read_set: ["docs/20-system/DESIGN.md"]
- write_set: ["podo/apps/web/components/EvidenceBlock.tsx", "podo/apps/web/components/CoveragePanel.tsx", "podo/apps/web/components/JobCard.tsx", "podo/apps/web/app/page.tsx", "podo/apps/web/test/evidence_coverage.spec.tsx"]
- verifier: "pnpm --filter web test"
