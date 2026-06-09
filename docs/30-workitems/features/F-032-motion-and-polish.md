# F-032-motion-and-polish

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
DESIGN이 명세했으나 미완인 폴리시를 마감한다: **Lottie '도착' 에셋 적용**(현 정적 PNG fallback), **Toast 시스템화**(현 인라인), **데스크톱 반응형 마감**(단일 중앙 컬럼 유지). 근거: M7 §2-G / DESIGN §7-2(Toast)·§8-1(Lottie)·§4(레이아웃).

## 2. 사용자 가치 (User Story)
- As 유진(Charter §2.1), I want 새 공고가 '도착'하는 느낌과 액션 피드백이 분명하길 바란다, so that 제품이 살아있고 신뢰된다.
- As 유진(데스크톱 사용 시), I want 화면이 깨지지 않길 바란다, so that 어디서든 편하게 본다.

## 3. 핵심 시나리오 (Feature-level)
- **happy**: 피드 진입 → 포도 '도착' 모션(1회) → 지원/스킵 → Toast 피드백.
- **alternate**: reduced-motion/에셋 미가용 → 정적 poster·CSS fallback(차단 아님).
- **fail**: Lottie 로드 실패 → 정적 마스코트 PNG로 graceful.

## 4. 범위
- PodoLottie에 `.lottie` 에셋 연결 + 성능 예산(≤50KB·동시≤2)·reduced-motion 정적 대체.
- 재사용 Toast 컴포넌트(role=status) — JobCardActions 인라인 toast 교체, 기존 동작 보존.
- 데스크톱 폭 반응형(단일 중앙 컬럼 유지, 폭/여백 정돈).

## 5. 비범위
- 새 장식 모션/앰비언트 루프(DESIGN §9 금지).
- 멀티컬럼 데스크톱 레이아웃(단일 피드 §7-4 유지).
- Toast 라이브러리 도입(자체 최소 구현 — YAGNI).

## 6. 요구사항
- Lottie는 '도착'·로딩·온보딩 의미 전달 전용(판단 데이터 장식 금지, DESIGN §8-1).
- Toast는 라벨 텍스트 동반(색만 의존 금지), aria-live.
- 데스크톱도 brand 그라데이션 3곳 fence 유지(DESIGN §2-4).

## 7. Feature-level Acceptance Criteria
- FAC-1 '도착' 시그니처 모션이 의미를 전달하고 reduced-motion/실패 시 정적 fallback한다.
- FAC-2 피드백 Toast가 일관 컴포넌트(role=status)로 통일되고 기존 동작을 보존한다.
- FAC-3 데스크톱 폭에서 단일 중앙 컬럼을 유지하며 레이아웃이 깨지지 않는다.

## 7-1. FAC ↔ AC 매핑표
- FAC-1 → T-099:AC-1
- FAC-2 → T-100:AC-1
- FAC-3 → T-101:AC-1

## 8. Non-functional Requirements
- 성능: Lottie ≤50KB·lazy·동시≤2(DESIGN §8-1).
- 접근성: 장식 모션 aria-hidden, 의미 모션 텍스트 대안, Toast aria-live.

## 8-1. UX 흐름 품질
- primary task: 액션 후 피드백 인지(Toast).
- empty/loading/error: Lottie 미가용=정적 poster, Toast 실패문구.
- accessibility: reduced-motion 정적, aria-live.
- copy 톤: "지원 기록됐어요"·"즐겨찾기에 담았어요".
- success metric(HEART-Happiness): 액션 후 피드백 인지(정성).

## 9. 엣지 케이스
- 동시 다중 Toast → 큐/대체 정책.
- `.lottie` 미제공 상태로 배포 → 정적 fallback(차단 아님).
- 매우 좁은/넓은 뷰포트 경계 폭.

## 10. 의존성
- PodoLottie(T-048) · JobCardActions(T-050) · globals.css/layout.

## 11. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 8 Motion](../../20-system/DESIGN.md#design-8-motion) · [## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: —

## 12. 열린 질문
- `.lottie` 에셋 조달(직접 제작 vs LottieFiles) — 미조달 시 정적 fallback 유지.
- Toast 위치/스택 정책(상단 vs 하단, 동시 개수).
