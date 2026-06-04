# F-004-eval-harness: 게이트 측정 하니스 (불변식 회귀 · 멀티-페르소나 · 골든 페어)

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 요약
스코어링/랭킹을 바꿀 때마다 "정확도 보존/개선 + 회귀 0"을 자동 확인하는 오프라인 평가 게이트. 불변식 회귀(GS-1 결정성·제품 규칙) + 멀티-페르소나 방향성 진단 + 골든 페어 정확도(GS-2 사실성 / GS-3 τ 프록시)를 `ai/eval`에 이식한다. 이 하니스가 M1 done의 "게이트 실증" 경로이자 A-3 검증 수단이다. 알고리즘 SSOT: [SCORING_PIPELINE_SPEC §10](../../20-system/SCORING_PIPELINE_SPEC.md).

## 2. 기술적 근거 (Technical rationale) — Type=technical-enabler
- **무엇을/왜:** 신뢰 게이트(GS-1 재현성·GS-2 근거 사실성·GS-3 상대 랭킹 타당도)는 *측정 경로*가 없으면 합의·차단할 수 없다. 본 enabler는 그 측정 경로를 코드로 박아 M1 done criteria의 "게이트 실증"(N=10 캐시 변동 0 / 표본 ≥30 hallucination ≤2%)과 Charter §6 Discovery exit check(A-3 τ)를 가능하게 한다.
- **서비스하는 가정/결정:** Charter §6 GS-1·GS-2·GS-3, §9 A-3(상대 랭킹 τ)·A-12(결정론 캐시 변동 0). [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) D1(게이트 우선). ARCH §3-2 `ai/eval`(read-only) 매핑.
- **사용자 시나리오 없음** — 오프라인 CI/검증 경로(빌더·창업자 사용).

## 3. 핵심 시나리오 (Feature-level)

### Happy path
1. 고정 3-JD 픽스처로 불변식 회귀 실행(캐시 격리 네임스페이스) → 제품 규칙 10종 통과.
2. 4개 합성 페르소나로 방향성 진단(도메인 tier 주입) → 6 불변식 + (선택) 모드 ablation.
3. 사람이 라벨링한 골든 페어로 정확도 측정(strict/tie-aware), `rescore_persona`로 스코어링 변경을 LLM 없이 ablation.
4. GS-1(캐시 hit 변동 0 / miss top-k 변동 0) · GS-2(hallucination ≤2%) · GS-3 τ 프록시 산출.

### Alternate path
1. 골든 페어가 산출물에 없는 공고를 참조 → 재수집하지 않고 unavailable 처리.
2. 빈 라벨 골든 페어 → "미라벨" 분리(graceful skip), 전부 미라벨이면 friendly fail.

### Fail path
1. 🔴 회귀 불변식 위반(예: mismatch가 엔지니어링 위로) → 게이트 실패, 변경 차단.
2. 🟡 골든셋 표본 편중 → 결과를 *참고*로 두고 승격 보류(과신 금지).

## 4. 범위
- 불변식 회귀(`_check_invariants` 10종) + 고정 픽스처 + 캐시 네임스페이스 격리(SPEC §10-1).
- 멀티-페르소나 진단(4 합성 페르소나 + 6 방향성 불변식 + `--compare-ranking-modes`)(SPEC §10-2).
- 골든 페어 프레임워크: `propose_pairs`/`load_pairs`/`evaluate_pairs`/`aggregate_metrics`/`rescore_persona`(SPEC §10-3).
- GS-1 결정성 테스트(N회 반복 hit 변동 0 / miss top-k 변동 0), GS-2 사실성 라벨링 측정, GS-3 τ 프록시.

## 5. 비범위
- dedup 기본값 승격 — 실험 플래그 유지(SPEC §10-4 승격 4조건 미충족).
- 실서비스 GS-3 실데이터(서류 통과율) — 출시 후 측정(Charter §6 GS-3).
- 스코어링 알고리즘 변경 자체 — F-001/F-003. 본 feature는 *측정*만.

## 6. 요구사항
- 불변식 10종·페르소나 프로파일·골든 페어 지표 정의는 SPEC §10을 그대로 이식.
- 골든 페어·재채점은 **LLM 호출 없이** 저장 산출물만 읽는다(재수집 금지 — unavailable 처리).
- `rescore_persona`는 **실제 `aggregate()` 재사용**(랭킹 로직 100% 동일, fit만 변경)으로 ablation.
- 합성 페르소나/이력서는 합성임을 명시하고 실제 데이터를 덮어쓰지 않는다.
- `ai/eval`은 DB read-only(§3-2). 회귀 픽스처 캐시는 일반 재계산과 격리.

## 7. Feature-level Acceptance Criteria
- **FAC-1 (GS-1):** 고정 픽스처에서 제품 불변식 10종(Frontend #1·fit≥4, Android<Frontend·fit≤3, Marketing 최하위·fit≤2, mismatch 가드, 추출형 인용, pairwise 불일치 보고)을 모두 검사·통과한다.
- **FAC-2 (GS-1):** 동일 (이력서, JD) 입력 N=10회 재실행 시 캐시 hit 점수 변동 0 + miss 재계산 top-k 순서 변동 0을 측정한다.
- **FAC-3 (GS-2):** 표본 공고 ≥30에서 표시된 근거 중 JD 원문에 실재하지 않는 요구 비율(hallucinated requirement)을 측정하고 ≤2% 게이트를 판정한다.
- **FAC-4 (GS-3 τ):** 골든 페어 strict/tie-aware 정확도를 모드별로 산출하고, `rescore_persona`로 스코어링 변경을 LLM 없이 ablation한다.
- **FAC-5:** 멀티-페르소나 진단이 4 페르소나에 도메인 프로파일을 주입해 방향성 불변식(extractive/fit_scale/mismatch_priority 등)을 검사한다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-014:AC-1, T-014:AC-2 (불변식 10종 + 픽스처 캐시 격리)
- FAC-2 → T-016:AC-3 (GS-1 N회 변동 측정)
- FAC-3 → T-016:AC-2 (GS-2 사실성 측정)
- FAC-4 → T-016:AC-1 (golden 지표 + rescore ablation), T-017:AC-1 (A-3 τ 프록시 1회)
- FAC-5 → T-015:AC-1, T-015:AC-2 (페르소나 주입 + 방향성 불변식)

## 8. Non-functional Requirements
- **결정성:** 평가는 저장 산출물 기반이라 재현 가능(LLM 미호출). 픽스처 캐시 격리로 골든 흔들림 방지.
- **정직성:** 표본 편중·N=1 한계를 리포트에 명시(과신 금지 — SPEC §10-4).
- **CI 게이트화:** 프로덕션은 "정확도 보존/개선 + 회귀 0"을 PR 차단 게이트로(후속).

## 8-1. UX 흐름 품질
(해당 없음 — 오프라인 평가.)

## 9. 엣지 케이스
- 골든 페어 공고가 산출물에 부재 → unavailable(재수집 X).
- 전부 미라벨 골든셋 → friendly fail.
- 프롬프트/스키마 개선으로 절대 fit 변동(예: Android 2→3) → 불변식은 *관계*로 검사하므로 통과(버그 아님, SPEC §10-1 회귀 철학).
- τ 측정 표본 부족 → 결과를 참고로, No-go/조건부 판정 신중.

## 10. 의존성
- **선행:** F-001(스코어링) + F-003(상대 랭킹) — 평가 *대상*. 구체: T-011(오케스트레이션 산출물)·T-008(aggregate).
- **A-12:** GS-1 결정성 테스트(100회 반복)가 본 enabler의 FAC-2 근거.
- **A-3:** T-017이 Charter §6 Discovery exit check를 1회 실행.

## 11. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md) (§5 게이트 실증)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§6 GS-1·GS-2·GS-3, §9 A-3·A-12)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 ai/eval, §7-3 grounding 검증)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §10](../../20-system/SCORING_PIPELINE_SPEC.md)
- Features: [F-001](F-001-core-value.md) · [F-003](F-003-relative-ranking.md)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) (D1 게이트 우선)

## 12. 열린 질문
- 이 프로젝트 골든셋을 어떻게 구축·확장? (창업자 라벨링 + 표본 편중 보완 — SPEC §10-4)
- GS-2 사실성 라벨링 평가자 수/절차? (Charter §10)
- dedup 승격 4조건 충족 시점/판단 주체?
