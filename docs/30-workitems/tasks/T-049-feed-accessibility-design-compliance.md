# T-049-feed-accessibility-design-compliance

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
피드 핵심 화면의 **접근성 일급화**(키보드·스크린리더·대비)와 **DESIGN 토큰 계약 준수**(raw hex 0 + fenced 그라데이션 3곳 한정)를 감사·보강한다. M2/M3 deferred a11y 부채(DSN-M3-001~003) 회수. F-018 FAC-5(접근성)·FAC-7(토큰/그라데이션) 커버.

## 2. 작업 범위
- 키보드: 피드 카드·탭·버튼·EvidenceBlock 펼침이 전부 키보드 도달·조작 가능(focus ring = DESIGN §7-4 2px grape outline).
- ARIA: 파일 input `<label>` 연결, 업로드/채점 중 `aria-busy`, MaskingPreview·CoveragePanel `role=region`/`role=alert`(degraded), 밴드는 색+텍스트 라벨(+✓/△) 동반.
- 대비: band 색을 텍스트로 쓸 때 `band-*-ink`(AA), 본문 `ink`/`muted`만, `faint`는 장식 전용(DESIGN §2-5).
- **토큰 준수 감사**: 컴포넌트 .tsx에 raw hex 0(`grep`), fenced 그라데이션이 §2-4 3곳(로고 ai·fit 링 arc·인사 strip)에만.

## 3. 구현 항목
1. 핵심 컴포넌트(JobCard·GreetingCard·CoveragePanel·Tab·Button·EvidenceBlock)에 label/aria-busy/role/aria-expanded 보강 + 키보드 핸들러. → 확인: vitest(aria 단언) (AC-1)
2. 대비: band 텍스트는 `band-*-ink` 토큰 사용 확인. → AC-1 포함.
3. raw hex/그라데이션 감사 스크립트 또는 테스트: 컴포넌트 디렉터리 raw hex 매칭 0 + brand.gradient 사용처 3곳 화이트리스트. → 확인: grep 기반 test (AC-2)

## 4. 제외 항목
- Lighthouse Accessibility 자동 점수 게이트(선택, 측정 기준 후속).
- 다국어/i18n a11y — 한국어 우선.
- 모션 reduced-motion — T-048 소관.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/components/ResumeUpload.tsx` — 파일 input `<label>`+aria-label(DSN-M3-001) + loading skeleton aria-busy(DSN-M3-002)
- `podo/apps/web/components/MaskingPreview.tsx` — section+aria-label(암묵 region, DSN-M3-003)
- `podo/apps/web/components/CoveragePanel.tsx` — ready section aria-label(암묵 region)
- `podo/apps/web/test/a11y.spec.tsx` (신설 — ARIA/role/band-ink 단언)
- `podo/apps/web/test/design_tokens.spec.ts` (신설 — components/ raw hex 0 + brand-gradient ≤3 감사)

## 5. 완료 조건
핵심 화면이 키보드 전 흐름 도달·ARIA 정합하고, 컴포넌트에 raw hex 0이며 fenced 그라데이션이 3곳에만 등장한다.

## 6. Acceptance Criteria
- AC-1 [Given] 피드 핵심 컴포넌트 [When] 렌더 + 키보드 탐색 [Then] 파일 input에 `<label>`, 업로드/채점 중 `aria-busy`, CoveragePanel `role=region`(degraded 시 `role=alert`), 탭 키보드 이동 + `aria-selected`가 모두 단언되고 band 텍스트가 `band-*-ink`(AA) 토큰을 쓴다.
- AC-2 [Given] `podo/apps/web/components/` 전체 [When] raw hex grep + brand.gradient 사용처 검사 [Then] 컴포넌트 .tsx의 raw hex 매칭이 0이고 `brand.gradient`(fenced) 사용처가 §2-4 화이트리스트(로고·fit 링·인사 strip) 3곳 이내다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/a11y.spec.tsx::test_AC_1_keyboard_and_aria_roles_and_band_ink_contrast
- AC-2 → vitest::podo/apps/web/test/design_tokens.spec.ts::test_AC_2_no_raw_hex_and_fenced_gradient_whitelist

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Feature: [F-018-companion-feed-experience](../features/F-018-companion-feed-experience.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN §2 Colors](../../20-system/DESIGN.md#design-2-colors), [§7 Components](../../20-system/DESIGN.md#design-7-components), [§9 Don'ts](../../20-system/DESIGN.md#design-9-donts)
- 부채: [IMPROVEMENT_GUIDE](../../40-validation/IMPROVEMENT_GUIDE.md) (DSN-M3-001~003 a11y · [Design-token-drift])

## 8. 메모
- DSN-M3-001(파일 input label)·002(aria-busy)·003(preview role=region) 회수 — M3 deferred.
- 구현 결정(implement): T-043/T-046/T-047에서 ARIA(aria-label·role=alert·aria-busy·aria-expanded)가 대부분 선반영됨 → 본 task는 잔여 DSN-M3 부채 3건(파일 label·skeleton aria-busy·preview region) 보강 + **감사 테스트 2종**(a11y.spec·design_tokens.spec)으로 계약 고정. region은 biome 정합 위해 section+aria-label(암묵 role) — getByRole로 단언.
- 구현 결정(implement): Tab·Button 컴포넌트는 현 코드에 미존재(단일 피드·inline 토큰 버튼) → a11y 감사는 실존 컴포넌트(JobCard·GreetingCard·CoveragePanel·EvidenceBlock·ResumeUpload·MaskingPreview) 대상. raw hex는 이미 0(globals.css 토큰 정의에만), brand-gradient는 FitScoreRing 1곳(≤3) — design_tokens.spec가 전수 고정.
- 검증(implement): web vitest a11y 3 + design_tokens 1 pass + 기존 web 회귀 0(34 pass) · `pnpm validate` green.

## 9. 의존성
- depends_on: [T-046, T-047]
- read_set: ["podo/apps/web/components/", "docs/20-system/DESIGN.md"]
- write_set: ["podo/apps/web/components/", "podo/apps/web/test/a11y.spec.tsx", "podo/apps/web/test/design_tokens.spec.ts"]
- assumptions: ["T-046/T-047 컴포넌트 존재"]
- verifier: "pnpm --filter @podo/web test a11y design_tokens"
