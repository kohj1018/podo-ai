# T-051-application-tracking-ui

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
JobCard에 지원/스킵·즐겨찾기 액션 UI를 붙이고, 처리 결과를 피드에 반영(처리완료 정리·즐겨찾기 보존)한다. 지원 = 원본 채널 링크 이동 + 기록. F-019 FAC-3 + UI 흐름 커버.

## 2. 작업 범위
- `podo/apps/web/components/JobCardActions.tsx` — "지원하기"(원본 채널 링크 + 기록 POST) / "스킵" / "즐겨찾기" 버튼. DESIGN §7-1 Button 재사용.
- 처리 후 낙관적 업데이트(피드에서 정리) + 실패 시 롤백 + Toast("지원 기록됐어요" / "기록에 실패했어요. 다시 시도해주세요.").
- 스킵 되돌리기(unskip) → 재노출.
- 즐겨찾기 별도 보기 진입.

## 3. 구현 항목
1. `JobCardActions.tsx` — 액션 버튼 + `POST /api/v1/applications`(T-050) 호출 + 낙관적 갱신/롤백. → 확인: vitest (AC-1)
2. 지원하기 = 원본 채널 링크 새 탭 + 기록(자동지원 아님). → AC-1 포함.
3. 스킵/unskip 토글 + Toast. → 확인: vitest (AC-2)

## 4. 제외 항목
- 자동지원·원클릭 지원 — Charter §5 비목표.
- 지원 일정/마감 캘린더 — 비목표.
- 기록 API·스키마 — T-050.

## 4-1. 변경 예정 파일/경로
- `podo/apps/web/components/JobCardActions.tsx` (신설)
- `podo/apps/web/components/JobCard.tsx` (actions 슬롯 결선)
- `podo/apps/web/test/job_card_actions.spec.tsx` (신설)

## 5. 완료 조건
지원/스킵/즐겨찾기 버튼이 동작해 기록되고 피드에 반영(처리완료 정리·즐겨찾기 보존)되며, 저장 실패가 Toast로 표면화된다.

## 6. Acceptance Criteria
- AC-1 [Given] 피드 JobCard [When] "지원하기" 클릭 [Then] 원본 채널 URL이 새 탭으로 열리고 `applied` 기록 POST가 호출되며 카드가 피드에서 정리되고 "지원 기록됐어요" Toast가 표시된다.
- AC-2 [Given] 공고 "스킵" 후 [When] unskip(되돌리기) [Then] 해당 공고가 피드에 재노출되고, 기록 저장 실패 시 "기록에 실패했어요. 다시 시도해주세요." Toast + 롤백된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/job_card_actions.spec.tsx::test_AC_1_apply_opens_link_records_and_clears
- AC-2 → vitest::podo/apps/web/test/job_card_actions.spec.tsx::test_AC_2_skip_unskip_toggle_and_error_toast

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M4-product-mvp](../milestones/M4-product-mvp.md)
- Feature: [F-019-application-tracking](../features/F-019-application-tracking.md)
- Architecture-Iface: [ARCH §7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN §7 Components](../../20-system/DESIGN.md#design-7-components) (Button·Toast)

## 8. 메모
- 지원 = 원본 채널 링크 이동(자동지원 아님 — Charter §5). Fail #8(기록 실패) 표면화.

## 9. 의존성
- depends_on: [T-047, T-050]
- read_set: ["podo/apps/web/components/JobCard.tsx", "podo/apps/api/src/applications/"]
- write_set: ["podo/apps/web/components/JobCardActions.tsx", "podo/apps/web/components/JobCard.tsx", "podo/apps/web/test/job_card_actions.spec.tsx"]
- assumptions: ["T-050 applications API 존재", "T-047 JobCard 존재"]
- verifier: "pnpm --filter @podo/web test job_card_actions"
