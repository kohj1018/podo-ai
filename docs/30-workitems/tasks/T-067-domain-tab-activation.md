# T-067-domain-tab-activation

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
M4에서 직군 분리 탭을 "자동 분류가 없어서 보류"로 미뤘다(Charter §8 흐름3). T-066이 자동 분류를 완성했으므로 본 task가 **직군 분리 탭 UI를 활성화**하고, 탭 전환 시 해당 직군 공고만 필터링해 노출한다. F-022 FAC-3·FAC-4의 UI 표현 구현.

## 2. 작업 범위
- 피드 상단 직군 탭 컴포넌트(`DomainTabBar`) 활성화 또는 신설: `[백엔드 | 데이터 | 프론트엔드 | 전체]` (탭 집합은 `Resume.primary_domains` 기준 동적).
- 탭 전환 → `GET /api/v1/feed?domain=backend` 식의 필터 쿼리 or client-side 필터.
- 피드 API(`GET /api/v1/feed`, ARCH §7-1 버전 경로 고정 — 무버전 `/api/feed` 금지) `domain` 필터 파라미터 추가: `recommendations`의 공고를 `job_postings.role_family` 기준 필터.
- 분류 저신뢰(confidence=low) 시 "직군이 섞여 있어요" 안내 + 양 탭 모두 추천. **confidence·domains는 T-066이 영속한 `resume_domains`를 api가 서빙한 값을 소비**(본 task는 계약 생산 X — T-066 P0 계약 read-only 소비).
- 한 직군에 공고 없음 → "이 직군은 오늘 공고가 없어요" empty 상태.
- 탭 키보드 접근성·ARIA(DESIGN §7-1 Tab — role="tablist"·role="tab"·aria-selected).

## 3. 구현 항목
1. `podo/apps/api/src/feed/feed.controller.ts` — `domain` 쿼리 파라미터 추가. `recommendations JOIN job_postings ON role_family = $domain`(값 없으면 전체). → 확인: jest (AC-1)
2. `podo/apps/web/components/DomainTabBar.tsx` — 신설(또는 M4 보류분 활성화). props: `domains: string[]` (이력서 primary_domains 기반), `active: string`, `onChange`. ARIA: `role="tablist"`, 각 탭 `role="tab" aria-selected`. 키보드: 좌우 화살표 탭 이동. → 확인: 접근성 단위 테스트 (AC-1, AC-3)
3. `podo/apps/web/app/page.tsx` 또는 피드 페이지 — `DomainTabBar` 마운트. 탭 전환 시 `domain` 파라미터로 피드 재요청(또는 client-side filter). → 확인: Playwright 탭 전환 시나리오 (AC-1)
4. 분류 저신뢰 상태 처리 — `Resume.primary_domains=["unknown"]` or confidence=low 시 피드 상단 "직군이 섞여 있어요" 배너 + 전체 탭 기본 활성. → 확인: fixture 렌더 테스트 (AC-2)
5. empty 상태 — 탭 전환 후 공고 0건 → "이 직군은 오늘 공고가 없어요" 표시. → 확인: API 빈 응답 → UI empty state (AC-1)

## 4. 제외 항목
- 직군별 분기 스코어링 모델 — 단일 모델 유지(A-7 별도 결정).
- 출력 계약(fit_level·evidence·result shape) 변경 — M4 동결.
- 비개발 직군 탭(디자인·마케팅 등) — Charter §5 비목표.
- 실 배포 후 탭 사용률 측정 — M6(실 배포 후 HEART 지표).

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/src/feed/feed.controller.ts` (domain 필터 파라미터 추가)
- `podo/apps/api/src/feed/feed.service.ts` (getFeed domain→role_family 필터 — §3#1 NestJS 서비스 계층 필연, AC-1 추적)
- `podo/apps/web/components/DomainTabBar.tsx` (신설 또는 활성화)
- `podo/apps/web/app/page.tsx` (DomainTabBar 마운트)
- `podo/apps/web/test/domain_tab.spec.tsx` (신설)

## 5. 완료 조건
이력서의 자동 분류 결과에 따라 직군 분리 탭이 피드 상단에 표시되고, 탭 전환 시 해당 직군 공고만 필터링 노출된다. 저신뢰 분류 시 정직한 안내가 표시된다.

## 6. Acceptance Criteria
- AC-1 [Given] 백엔드 이력서(T-066 분류 결과: primary=["backend"]) [When] 피드 접근 → "백엔드" 탭 선택 [Then] `job_postings.role_family=backend` 공고만 필터링되어 노출되고 다른 직군 공고는 표시되지 않는다.
- AC-2 [Given] 저신뢰 이력서(confidence=low) [When] 피드 접근 [Then] "직군이 섞여 있어요" 안내가 표시되고 전체 탭이 기본 활성화된다.
- AC-3 [Given] DomainTabBar 렌더 [When] 키보드 좌우 화살표 입력 [Then] 포커스가 탭 간 이동하고 aria-selected가 정확하게 업데이트된다(DESIGN §7-1 Tab).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → jest::podo/apps/web/test/domain_tab.spec.ts::test_AC_1_tab_filter_by_domain
- AC-2 → jest::podo/apps/web/test/domain_tab.spec.ts::test_AC_2_low_confidence_banner
- AC-3 → jest::podo/apps/web/test/domain_tab.spec.ts::test_AC_3_keyboard_navigation_aria

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-022-resume-domain-classification](../features/F-022-resume-domain-classification.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-4 직군 분리 탭)
- Architecture-Iface: [ARCH ##7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ##7 Components](../../20-system/DESIGN.md#design-7-components) (Tab — §7-1 ARIA)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§8 흐름3 직군 분기)

## 8. 메모
- M4 보류분(직군 분리 탭 컴포넌트 코드가 이미 부분 존재 가능) — builder가 `DomainTabBar` or 유사 컴포넌트 존재 여부 확인 후 활성화 또는 신설 선택.
- 열린 질문: `domain` 필터를 server-side(API 파라미터)로 처리할지 client-side로 할지 — API 응답 크기·UX 응답성 고려해 builder 판단(단, API 레이어에 도메인 필터 경로는 필수).
- repair-plan 2026-06-08 [self-review] P1 Plan-scope: Adopt(기록) — **AC-1의 end-to-end "탭→피드 필터링 노출"은 `FeedView.tsx`/`FeedList.tsx`가 active domain을 소비해야 성립하나 write_set에 미포함**(plan under-scope). DomainTabBar/API `?domain=`/page.tsx만 완성돼 탭 클릭이 피드에 무반영(dead-end)이었음.
- repair 2026-06-08 [stabilize 수렴] **배선 완료(M5 graduation 차단 해소, M6 아님)**: `FeedList`에 `domain` prop+`&domain=` fetch+변경 시 재요청, `FeedView`→`page.tsx active` 전달 추가. 무키 멀티유저 E2E(`pnpm e2e`) green으로 실증. [QA-M5-009 수렴]

## 9. 의존성
- depends_on: [T-066, T-065]   # T-066=분류·resume_domains 계약 / T-065=feed.controller 선수정(둘 다 feed.controller 편집 → 순차)
- read_set: ["podo/apps/api/src/feed/feed.controller.ts", "podo/apps/web/app/page.tsx", "podo/apps/web/components/**"]
- write_set: ["podo/apps/api/src/feed/feed.controller.ts", "podo/apps/web/components/DomainTabBar.tsx", "podo/apps/web/app/page.tsx"]
- assumptions: ["T-066 완료(load_resume가 자동 분류 결과로 primary/secondary_domains 채움)", "job_postings.role_family 컬럼 존재(M4 스키마 기확인)"]
- verifier: "pnpm --filter @podo/web test domain_tab && pnpm --filter @podo/api test"
