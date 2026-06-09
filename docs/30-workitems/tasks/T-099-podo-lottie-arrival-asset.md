# T-099-podo-lottie-arrival-asset

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
`PodoLottie`에 실제 `.lottie` '도착' 에셋을 **연결**해 DESIGN §8-1 시그니처 모션을 켠다. (컴포넌트·의존성은 이미 구현·설치돼 있고, 빠진 건 에셋 + `src` 전달뿐 — repair-plan 사실 정정.)

## 2. 작업 범위
`.lottie` 에셋 추가 + 호출부 `src` 연결만. dotLottie 구현·의존성 설치 제외(이미 존재).

## 3. 구현 항목
1. `podo/apps/web/public/podo-arrival.lottie`(에셋) — 현재: 없음 → 변경: '도착' 모션 `.lottie`(dotLottie v2, ≤50KB) 추가. 미조달 시 본 단계 생략(아래 fallback이 정적 마스코트로 graceful, 비차단). → 확인: 에셋 로드 (AC-1).
2. `podo/apps/web/components/GreetingCard.tsx:32` — 현재: `<PodoLottie size={52} />`를 **src 없이** 호출 → `PodoLottie`가 항상 정적 poster(마스코트 PNG)로 fallback(`!src` 분기, PodoLottie.tsx:35) → 변경: `<PodoLottie src="/podo-arrival.lottie" size={52} />`로 src 전달. → 확인: 인사 카드에서 '도착' 모션 (AC-1).
3. (회귀 확인) `PodoLottie.tsx`는 이미 `@lottiefiles/dotlottie-react` `dynamic(ssr:false)` + `usePrefersReducedMotion` + `onError→failed` fallback 구현(PodoLottie.tsx:8-54). **수정 불필요** — src 전달 시 reduced-motion/로드실패 fallback 경로가 그대로 동작하는지만 회귀로 고정. → 확인 (AC-1).

## 4. 제외 항목
- `@lottiefiles/dotlottie-react` 의존성 설치 — **이미 설치됨**(package.json:13 `^0.19.4`). lockfile 변경 없음.
- PodoLottie dotLottie/reduced-motion/fallback 구현 — **이미 구현됨**(PodoLottie.tsx).
- 앰비언트 루프·신규 장식 모션(DESIGN §9 금지).

## 4-1. 변경 예정 파일/경로

## 5. 완료 조건
인사 카드(GreetingCard)에서 `.lottie` '도착' 모션이 1회 재생되고, reduced-motion/로드 실패 시 기존 정적 마스코트 fallback이 그대로 동작한다.

## 6. Acceptance Criteria
- AC-1 [Given] `.lottie` 에셋 + `src` 전달 + 모션 허용 환경 [When] GreetingCard 렌더 [Then] '도착' 모션을 1회 재생하고, reduced-motion 또는 로드 실패 시 정적 마스코트 poster로 fallback한다(차단 없음).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/podo_lottie.spec.tsx > test_AC_1_src_plays_and_fallback_preserved

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-032-motion-and-polish](../features/F-032-motion-and-polish.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 8 Motion](../../20-system/DESIGN.md#design-8-motion)
- ADR: —

## 8. 메모
- `.lottie` 에셋 조달은 외부 작업(직접 제작 vs LottieFiles). 미조달 시 정적 fallback 유지(M7 비차단).
- repair-plan 2026-06-10 [default] P1 Plan-ambiguity: Adopt — PodoLottie·의존성 이미 구현/설치(코드 실증) → scope를 `.lottie` 에셋 + src 연결로 축소, 의존성 설치·lockfile 단독 wave 삭제(리뷰 정확).

## 9. 의존성
- depends_on: []
- write_set: ["podo/apps/web/components/GreetingCard.tsx", "podo/apps/web/public/podo-arrival.lottie"]
- 비고: lockfile 변경 없음(의존성 기설치) → 단독 wave 불필요, Wave 1 병렬 가능.
