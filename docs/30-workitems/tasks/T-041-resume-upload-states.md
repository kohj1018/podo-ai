# T-041-resume-upload-states

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
T-038 업로드 화면의 **DESIGN §7-4 상태 매트릭스**를 집행한다 — 비허용 포맷 안내와 로딩 상태(skeleton, 가짜 점수 금지)를 구현한다. (repair-plan: T-038 5 AC sizing 해소 — 업로드+preview(T-038)와 상태 매트릭스(본 task)를 분리.)

## 2. 작업 범위
- `ResumeUpload`(T-038 산출)에 비허용 포맷 안내 + 100KB 초과 client pre-check 안내.
- loading skeleton shimmer + "이력서 분석 중…"(가짜 점수/preview 미표시) + `prefers-reduced-motion` 분기.
- error toast + 재시도 / empty 상태(DESIGN §7-4).

## 3. 구현 항목
1. `podo/apps/web/components/ResumeUpload.tsx`(T-038) — 현재: 업로드+preview만 → 변경: `<input accept=".txt,.md">` 비-txt/md 선택·drop 시 "현재 .txt / .md 파일 또는 텍스트 붙여넣기만 지원합니다." 인라인 안내(업로드 미전송) + 100KB 초과 client pre-check "파일이 너무 큽니다(최대 100KB)." → 확인: `.pdf` 선택 → 안내. (AC-1)
2. `podo/apps/web/components/ResumeUpload.tsx` 로딩 분기 — 현재: 없음 → 변경: 업로드 중 skeleton shimmer + "이력서 분석 중…" 텍스트, 점수/preview 텍스트 미표시. `@media (prefers-reduced-motion: reduce)` 분기(DESIGN §8 모션). error → toast "업로드 실패. 다시 시도해보세요." + 재활성화, empty → "이력서를 업로드하거나 텍스트를 붙여넣으세요." → 확인: `test_AC_2` 로딩 중 skeleton + 점수 텍스트 0. (AC-2)

## 4. 제외 항목
- 업로드 전송·preview 렌더·CTA disabled(T-038). · feed 연결(T-039). · 새 컴포넌트 신설(본 task는 T-038 컴포넌트의 상태 분기만). · PDF 텍스트 추출(M4).

## 4-1. 변경 예정 파일/경로
<!-- 구현 시점에 채운다. -->

## 5. 완료 조건
비허용 포맷·초과 크기 안내와 로딩 skeleton(가짜 점수 없음)·에러·빈 상태가 DESIGN §7-4대로 표현된다.

## 6. Acceptance Criteria
- AC-1 [Given] `.txt`/`.md` 이외 파일 선택(또는 100KB 초과) [When] 선택/drop [Then] "현재 .txt / .md 파일 또는 텍스트 붙여넣기만 지원합니다."(또는 크기 안내)가 표시되고 업로드가 전송되지 않는다.
- AC-2 [Given] 업로드 진행 중 [When] 로딩 상태 [Then] skeleton이 표시되고 가짜 점수/preview 텍스트가 표시되지 않으며, `prefers-reduced-motion: reduce`에서 shimmer가 비활성된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/resume_states.spec.tsx::test_AC_1_non_txt_and_oversize_show_message_no_upload
- AC-2 → vitest::podo/apps/web/test/resume_states.spec.tsx::test_AC_2_loading_skeleton_no_fake_score

## 6-2. TDD opt-out
<!-- TDD 적용 — API mock + Testing Library(T-028 인프라). 상태 분기 렌더 단언. -->

## 7. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md)
- Feature: [F-015-resume-upload-ui](../features/F-015-resume-upload-ui.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components) (상태 매트릭스), [## 2 Colors](../../20-system/DESIGN.md#design-2-colors)
- ADR: [ADR-042](../../90-decisions/boilerplate/ADR-042-ux-flow-quality.md)

## 8. 메모
- 해석 확정: T-038에서 split(repair-plan 2026-06-07 P1 sizing) — 업로드+preview=T-038, 상태 매트릭스=본 task. 동일 컴포넌트(`ResumeUpload.tsx`)를 편집하므로 T-038 후 순차(write_set 교집합).

## 9. 의존성
- depends_on: [T-038]   # ResumeUpload/MaskingPreview 존재 후 상태 분기 추가
- read_set: ["docs/20-system/DESIGN.md", "podo/apps/web/components/ResumeUpload.tsx"]
- write_set: ["podo/apps/web/components/ResumeUpload.tsx", "podo/apps/web/test/resume_states.spec.tsx"]
- verifier: "pnpm --filter web test"
- # T-038과 ResumeUpload.tsx write_set 교집합 → 같은 wave 금지(T-038 후 순차)
