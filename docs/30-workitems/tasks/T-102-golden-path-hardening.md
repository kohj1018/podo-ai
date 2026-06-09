# T-102-golden-path-hardening

## 0. Status
draft

## 0-1. Type
bugfix

## 1. 작업 목적
핵심 골든패스(로그인 → /resume 입력 → 제출 → 피드 분석결과)를 통합 점검해 끊김·버그를 제거하고 회귀 테스트로 고정한다(M7 §2-B). 다른 M7 feature 통합 후 마지막 wave.

## 2. 작업 범위
골든패스 위 동작 점검·수정 + 회귀 테스트. 골든패스 밖 버그는 QA_FINDINGS 이연.

## 3-T. 트러블슈팅
- **증상(Symptom):** 가입~추천 도달 사이 분기에서 끊김/버그(통합 후 표면화).
- **재현 절차(Repro):** implement 시 골든패스 E2E로 결정적 재현 — 세션 만료·교차출처 쿠키 미전송·이력서 교체 후 stale run·`window.location.assign` 강제이동·업로드/채점 실패 복구 경로.
- **기대 / 실제(Expected / Actual):** 기대=무중단 도달. 실제=implement 시 관측 기록.
- **관측(Observed):** 네트워크(401/403/CORS)·콘솔·E2E 스냅샷.
- **가설(Hypotheses):** (1) credentials 누락 잔존([[web-fetch-credentials-include]]) (2) active resume 교체 시 이전 run/coarse 혼입(M5-repair-38) (3) redirect 타이밍 경쟁(T-097).
- **근본 원인(Root cause):** implement 시 가설 검증 후 확정.
- **회귀 테스트 AC:** 아래 AC-1을 재현 실패 테스트(Red→Green)로 박는다.

## 3. 구현 항목
1. 골든패스 E2E(Playwright) — 현재: 부분 e2e → 변경: 로그인→/resume 입력(파일·직접작성)→제출→채점 대기→피드 분석결과 전 구간 1개 시나리오로. → 확인: E2E green (AC-1).
2. 식별 버그 수정 — 변경: 점검에서 나온 P0/P1을 각각 재현 테스트 + 수정. 안 고치는 건 QA_FINDINGS(M7)에 명시 이연. → 확인 (AC-2).

## 4. 제외 항목
- 신규 기능. 골든패스 밖 surface 버그(별 finding).

## 4-1. 변경 예정 파일/경로

## 5. 완료 조건
골든패스가 E2E로 무중단 통과하고, 식별된 P0/P1이 수정되거나 명시 이연된다.

## 6. Acceptance Criteria
- AC-1 [Given] 신규 사용자 [When] 로그인→이력서 입력·제출→피드 [Then] 골든패스 E2E가 끊김 없이 통과한다(401/403/CORS/stale run 0).
- AC-2 [Given] 통합 점검 [When] 골든패스 버그 식별 [Then] 각 P0/P1이 회귀 테스트와 함께 수정되거나 QA_FINDINGS(M7)에 명시 이연된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/e2e/golden_path.spec.ts > test_AC_1_signup_to_feed
- AC-2 → (식별 버그별 회귀 테스트 — implement 시 추가)

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-033-core-flow-hardening](../features/F-033-core-flow-hardening.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-009](../../90-decisions/boilerplate/ADR-009-tdd-default.md)

## 8. 메모
- repair-plan 2026-06-10 [default] P1 Plan-sizing: Adopt — bugfix 스윕이라 write_set은 진단 후 확장(임의 source 파일). 아래 9 write_set은 *시드*이며, implement가 `## 4-1`에 실제 변경 파일을 채우고 QA_FINDINGS(M7)를 갱신한다(미고침은 명시 이연).
- 이미 알려진 버그는 별 task로 분리 처리(중복 회피): **score POST 실패 미이동=T-096:AC-3** · **redirect 루프/경쟁=T-097:AC-1**. T-102는 *통합 후 새로 드러나는* 골든패스 결함 발굴·수정 담당.

## 9. 의존성
- depends_on: [T-090, T-091, T-092, T-093, T-094, T-095, T-096, T-097, T-098, T-099, T-100, T-101]
- write_set: ["podo/apps/web/e2e/golden_path.spec.ts"]  # 시드 — 진단 후 source 파일로 확장 허용(bugfix)
- 비고: 전 task 통합 후 단독 마지막 wave. write_set은 진단 결과에 따라 확장(`## 4-1`이 SSOT).
