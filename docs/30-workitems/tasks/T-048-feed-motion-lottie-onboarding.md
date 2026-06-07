# T-048-feed-motion-lottie-onboarding

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
피드의 '도착(arrival)' 모션 + 마스코트 lottie + 첫 진입 온보딩을 구현하되, **모든 모션에 `prefers-reduced-motion` 분기를 강제**한다(DESIGN §8·§8-1). lottie는 의미 전달(arrival·로딩·온보딩 환영) 전용 — 미반영/로드 실패 시 CSS arrival로 graceful fallback. F-018 FAC-6(reduced-motion)·온보딩 시나리오 커버.

## 2. 작업 범위
- `podo/apps/web/components/ArrivalList.tsx` — 신규 공고 카드 진입 = fade + `translateY(8px→0)`, stagger 40ms, ≤200ms(DESIGN §8). `prefers-reduced-motion: reduce`면 transform/stagger 제거 → opacity fade(≤120ms)만.
- `podo/apps/web/components/PodoLottie.tsx` — `@lottiefiles/dotlottie-react`를 **`dynamic(() => …, { ssr: false })`**로 로드(DESIGN §8-1). `.lottie` 에셋. reduced-motion이면 **autoplay 금지 → 정적 프레임/poster 렌더**. 장식 애니메이션은 `aria-hidden`.
- `podo/apps/web/components/Onboarding.tsx` — 첫 진입(세션 있으나 이력서 없음) 시 포도가 업로드를 안내(F-015 경로 링크). 1회성(localStorage 플래그 or 서버 상태).
- 모션 토큰은 DESIGN §8(ease/duration)만 참조 — 임의 모션 금지.

## 3. 구현 항목
1. `ArrivalList.tsx` — IntersectionObserver/CSS로 arrival 모션 + reduced-motion 분기. → 확인: vitest(reduced-motion matchMedia mock 시 transform 미적용) (AC-1)
2. `PodoLottie.tsx` — dotLottie dynamic ssr:false + reduced-motion 정적 프레임 분기 + aria-hidden(장식). → 확인: vitest(reduced-motion 시 autoplay=false·정적) (AC-2)
3. `Onboarding.tsx` — 이력서 미보유 첫 진입 안내 + 업로드 링크 + 1회성 dismiss. → 확인: vitest (AC-3)
4. lottie 미로드/실패 시 CSS arrival fallback 경로. → AC-2 포함.

## 4. 제외 항목
- lottie 에셋 *제작*(포도 .lottie 디자인) — 디자인 산출물, 본 task는 통합·플레이스홀더 에셋.
- 점수·밴드·근거에 lottie 장식 — DESIGN §9 금지(원칙 1).
- 무한 앰비언트 루프·전면 배경 lottie — 금지.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/components/ArrivalList.tsx` (신설)
- `podo/apps/web/components/PodoLottie.tsx` (신설)
- `podo/apps/web/components/Onboarding.tsx` (신설)
- `podo/apps/web/test/feed_motion.spec.tsx` (신설)

## 5. 완료 조건
신규 공고가 arrival 모션으로 렌더되고, `prefers-reduced-motion: reduce`에서 모든 모션(arrival·lottie·stagger)이 정적으로 대체되며, 첫 진입 온보딩이 동작한다.

## 6. Acceptance Criteria
- AC-1 [Given] 신규 공고 3건 + `prefers-reduced-motion` 미설정 [When] 피드 렌더 [Then] 각 카드가 fade+translateY arrival 모션(stagger)으로 진입하고, `matchMedia('(prefers-reduced-motion: reduce)')=true`로 모킹 시 transform/stagger 없이 opacity fade만 적용된다.
- AC-2 [Given] PodoLottie 컴포넌트 [When] reduced-motion=reduce [Then] dotLottie autoplay가 비활성되고 **정적 첫 프레임(poster)이 렌더**되며(무렌더 아님 — 마스코트는 보임), 장식 인스턴스에 `aria-hidden`이 있고, lottie 로드 실패 시 CSS arrival로 fallback한다.
- AC-3 [Given] 세션 보유·이력서 미보유 사용자 [When] 첫 피드 진입 [Then] 온보딩 안내(포도 + 업로드 링크)가 표시되고 dismiss 후 재진입 시 표시되지 않는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/feed_motion.spec.tsx::test_AC_1_arrival_motion_and_reduced_motion_branch
- AC-2 → vitest::podo/apps/web/test/feed_motion.spec.tsx::test_AC_2_lottie_reduced_motion_static_and_fallback
- AC-3 → vitest::podo/apps/web/test/feed_motion.spec.tsx::test_AC_3_onboarding_first_entry_once

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Feature: [F-018-companion-feed-experience](../features/F-018-companion-feed-experience.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN §8 Motion](../../20-system/DESIGN.md#design-8-motion), §8-1 Lottie, [§9 Don'ts](../../20-system/DESIGN.md#design-9-donts)
- ADR: [ADR-049](../../90-decisions/boilerplate/ADR-049-concept-mockup-first-design.md)

## 8. 메모
- lottie 라이브러리 = `@lottiefiles/dotlottie-react`(DESIGN §8-1 확정), `.lottie` 포맷, 에셋 ≤~50KB·동시 ≤2.
- 온보딩 1회성 저장: localStorage(단순) — 멀티디바이스 동기는 비범위.

## 9. 의존성
- depends_on: [T-046]
- read_set: ["podo/apps/web/components/", "docs/20-system/DESIGN.md"]
- write_set: ["podo/apps/web/components/ArrivalList.tsx", "podo/apps/web/components/PodoLottie.tsx", "podo/apps/web/components/Onboarding.tsx", "podo/apps/web/test/feed_motion.spec.tsx", "podo/apps/web/package.json", "pnpm-lock.yaml"]
- assumptions: ["T-046 피드 셸 존재", "dotLottie-react 설치 가능"]
- verifier: "pnpm --filter @podo/web test feed_motion"
