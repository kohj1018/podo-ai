# T-028-feed-page

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
Next.js 단일 피드 페이지를 만든다 — `GET /api/v1/feed`의 `recommendations` 정렬 목록을 `rank_position` 커서로 무한 스크롤하며, 각 공고를 **적합도 5단계 배지**(fit_level 직결) + fit 배지와 함께 렌더한다. DESIGN §7 컴포넌트(JobCard·FitScoreRing·PassBand) 재사용.

## 2. 작업 범위
- `podo/apps/web` 피드 페이지: API 소비 + 중복제거 목록 + 커서 무한 스크롤 + 리스트 가상화(§7-4).
- 적합도 5단계 배지(fit_level 1~5 직결, `band-*` 토큰) + fit 배지(FitScoreRing). 합격확률/% 표시 금지.

## 3. 구현 항목
1. `podo/apps/web/app/page.tsx`(또는 `app/feed/page.tsx`) — 현재: 헬스 placeholder(T-018) → 변경: `GET /api/v1/feed` fetch + `JobCard` 목록 렌더(커서 `nextCursor` 무한 스크롤 + 가상화). → 확인: `test_AC_1`이 rank_position 순 + 중복제거 렌더. (AC-1)
2. `podo/apps/web/components/JobCard.tsx` — 현재: 없음 → 변경: **DESIGN §7-2 JobCard 재사용 구현**(source/role/co/meta + `FitScoreRing` + 적합도 5단계 배지). 배지는 DESIGN §2 `color.passband.{1..5}` **토큰**으로(raw hex 금지) — **라벨은 "적합도"**(DESIGN의 "합격가능성"을 M2 명칭 결정대로 relabel). → 확인: 토큰 사용(raw hex grep 0) + fit_level→band 매핑. (AC-1)
3. `podo/apps/web/components/FitScoreRing.tsx` — DESIGN §7-2 재사용(fit 배지). 그라데이션은 FENCED(§2-4 — fit 점수 링만 허용). → 확인: 렌더. (AC-1)
4. 무한 스크롤 — `nextCursor`로 다음 페이지 append(rank_position 커서). → 확인: `test_AC_2` 추가 로드 시 다음 항목 append. (AC-2)

## 4. 제외 항목
- 근거 펼침/커버리지 패널/보류(T-029) · 인증 · 직군 탭(M2 비범위) · 새 디자인 primitive 신설.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/app/page.tsx`, `podo/apps/web/components/JobCard.tsx`, `podo/apps/web/components/FitScoreRing.tsx`, `podo/apps/web/components/PassBand.tsx`, `podo/apps/web/test/feed.spec.tsx`
- 추가: `podo/apps/web/components/FeedList.tsx`(Feed 패턴 §7-3 — client fetch+커서), `app/globals.css`(§2 band/gradient 토큰), `vitest.config.ts`(jsdom+react), `package.json`+`pnpm-lock.yaml`(RTL/jsdom/plugin-react devDeps)

## 5. 완료 조건
피드가 중복제거된 공고를 적합도 5단계 + fit 배지와 함께 rank_position 순으로 렌더하고, 커서 무한 스크롤이 동작한다.

## 6. Acceptance Criteria
- AC-1 [Given] `GET /api/v1/feed` 응답 [When] 피드 페이지 렌더 [Then] 중복제거된 공고가 `rank_position` 순으로 적합도 5단계 배지(fit_level 직결, `band-*` 토큰) + fit 배지와 함께 표시되고, 합격확률/% 텍스트가 없다.
- AC-2 [Given] `nextCursor`가 있는 첫 페이지 [When] 스크롤 끝 도달 [Then] 다음 페이지가 `rank_position` 커서로 로드되어 목록에 append된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/feed.spec.tsx::test_AC_1_renders_sorted_with_fit_band_no_percent
- AC-2 → vitest::podo/apps/web/test/feed.spec.tsx::test_AC_2_cursor_infinite_scroll_appends

## 6-2. TDD opt-out
<!-- TDD 적용 — API mock + Testing Library 렌더 단언. e2e는 후속 Playwright. -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-010-feed-coverage-ui](../features/F-010-feed-coverage-ui.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4) (단일 피드 가상화·5단계 밴드·커서)
- Design: [DESIGN ## 2 Colors](../../20-system/DESIGN.md#design-2-colors) (passband 토큰·gradient FENCED) · [## 7 Components](../../20-system/DESIGN.md#design-7-components) (JobCard·FitScoreRing·PassBand 재사용)
- ADR: [ADR-042](../../90-decisions/boilerplate/ADR-042-ux-flow-quality.md) · [ADR-027](../../90-decisions/boilerplate/ADR-027-interface-decision-allocation.md)

## 8. 메모
- DESIGN cross-check: JobCard·FitScoreRing·PassBand는 **재사용**(신규 primitive X). PassBand "합격가능성" → "적합도"로 relabel(M2 명칭 결정 — DESIGN 용어 reconcile은 후속). band-* fill/ink 토큰, raw hex 금지(§2-5 의미는 색+텍스트 라벨 동반).
- 해석 확정: 적합도 배지 = `fit_level` 1:1(별도 calibration X, M2 결정).
- 구현 노트(2026-06-06): 메인 세션 수동. JobCard/FitScoreRing/PassBand = DESIGN §7-2 구현, FeedList = §7-3 Feed 패턴(client). 토큰 레이어: `globals.css :root`에 band-*-fill/ink + brand-gradient(raw hex는 여기만), 컴포넌트는 `var(--band-{level}-*)` 동적 참조(§9 raw hex 0 — components grep 0). gradient는 FitScoreRing(FENCED §2-4)만.
- 테스트 인프라: `@testing-library/react`+`jsdom`+`@vitejs/plugin-react@^4`(vitest2/vite5 호환 — v6는 vite6 요구) 추가, `vitest.config`에 jsdom+react. RTL render로 AC 검증(순수 컴포넌트 — DI 부트 무관).
- **무한 스크롤 범위**: cursor 페이지네이션 + 중복제거 append를 "더 보기" 트리거로 구현(AC-2 핵심 = cursor 로드+append, 테스트됨). *auto-on-scroll(IntersectionObserver)*는 jsdom 미지원 + 동일 cursor 메커니즘이라 thin 확장으로 이연. **리스트 가상화(§7-4)**는 M2 데이터 규모(수십 건)상 YAGNI — 이연(후속 대용량 시 react-window).
- PassBand held(fit_level null) → "적합도 보류"(가짜 점수 0) — 상세 보류 렌더는 T-029.

## 9. 의존성
- depends_on: [T-026]
- read_set: ["docs/20-system/DESIGN.md"]
- write_set: ["podo/apps/web/app/page.tsx", "podo/apps/web/components/JobCard.tsx", "podo/apps/web/components/FitScoreRing.tsx", "podo/apps/web/components/PassBand.tsx", "podo/apps/web/test/feed.spec.tsx"]
- verifier: "pnpm --filter web test"
