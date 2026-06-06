# T-038-resume-upload-ui

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
Next.js `/resume` 업로드 화면을 만든다 — 사용자가 `.txt`/`.md` 파일 또는 paste로 이력서를 입력하면 **마스킹본 preview**(직접 식별자 플레이스홀더 강조) + evidence 요약을 보여주고, "이 이력서로 분석 시작" 버튼으로 스코어링/feed 흐름에 연결한다(연결 자체는 T-039). preview는 *안전 통제*도 겸함 — 사용자가 PII 제거를 눈으로 확인 후 분석 시작. DESIGN §7-4 상태 매트릭스·§2 토큰(raw hex 금지) 준수.

## 2. 작업 범위
- App Router `/resume` 페이지 + 업로드 컴포넌트(파일 drag/drop accept=".txt,.md" + textarea paste).
- 마스킹 preview 패널(플레이스홀더 강조 + "스킬 N개, 경력 M건" 요약).
- "이 이력서로 분석 시작" Button.primary(preview 전 disabled).
- 신규 컴포넌트(ResumeUpload·MaskingPreview)를 DESIGN §7 Components 인벤토리에 등록(P1-design).
- (상태 매트릭스 loading/error/empty·포맷 안내는 **T-041**로 분리 — repair-plan P1 sizing.)

## 3. 구현 항목
1. `podo/apps/web/app/resume/page.tsx` — 현재: 없음 → 변경: `/resume` 라우트 + `ResumeUpload` 렌더(서버 컴포넌트 셸 + client 업로드). → 확인: `/resume` 진입 시 업로드 영역 렌더. (AC-1)
2. `podo/apps/web/components/ResumeUpload.tsx`(`'use client'`) — 현재: 없음 → 변경: FeedList 패턴(API_BASE=`NEXT_PUBLIC_API_BASE_URL`) 차용. 파일 `<input accept=".txt,.md">` + textarea(paste). 제출 시 `POST /api/v1/resumes`(파일=multipart, paste=json). 응답의 `masked_preview`·`placeholders`·`evidence`(스킬/경력 수) 수신해 상태 저장. → 확인: 업로드→응답→preview 표시. (AC-1)
3. `podo/apps/web/components/MaskingPreview.tsx` — 현재: 없음 → 변경: 마스킹본 텍스트 렌더 + `[MASKED_EMAIL]`·`[MASKED_PHONE]`·`[MASKED_NAME]` 등 플레이스홀더를 토큰 색(`var(--band-*-ink)` 등, raw hex 금지)으로 강조 + "스킬 N개, 경력 M건 인식" 1줄. → 확인: `test_AC_2`가 플레이스홀더 강조 노드 존재. (AC-2)
4. "이 이력서로 분석 시작" 버튼 — 현재: 없음 → 변경: Button.primary, API 응답 전(`!preview`) `disabled`. 클릭 핸들러는 T-039(feed 연결). → 확인: 응답 전 disabled, 후 enabled. (AC-3)
5. `docs/20-system/DESIGN.md` §7 Components — 현재: ResumeUpload·MaskingPreview 미등록 → 변경: 두 신규 컴포넌트를 §7 인벤토리에 1줄씩 등록(8-state 적용 범위 명시: ResumeUpload 업로드 영역 loading/error/empty는 T-041, MaskingPreview loading skeleton). Button.primary는 기존 §7 재사용(primitive 신설 X). → 확인: §7에 두 항목 존재. (AC-1, P1-design)
> (비허용 포맷 안내·로딩 skeleton·error/empty 상태 매트릭스는 **T-041**로 분리 — repair-plan P1 sizing.)

## 4. 제외 항목
- feed 페이지로 이동·스코어링 기동(T-039). · 상태 매트릭스(포맷 안내·loading/error/empty — T-041). · 행단위 evidence 편집 UI(F-015 §5). · PDF/docx. · 인증·멀티유저·배포(M4). · 새 디자인 primitive 신설(필요 시 architect/bootstrap-design).

## 4-1. 변경 예정 파일/경로
<!-- 구현 시점에 채운다. -->

## 5. 완료 조건
`/resume`에서 파일/paste 업로드 시 마스킹 preview(플레이스홀더 강조 + evidence 요약)가 뜨고, "분석 시작" 버튼이 응답 전 disabled이며, 신규 컴포넌트가 DESIGN §7에 등록된다. (상태 매트릭스는 T-041.)

## 6. Acceptance Criteria
- AC-1 [Given] `/resume` 진입 [When] `.txt` 선택/paste 후 업로드 [Then] 마스킹 preview 패널이 렌더되고 "스킬 N개, 경력 M건" 요약이 표시된다.
- AC-2 [Given] 마스킹 preview [When] 렌더 [Then] `[MASKED_EMAIL]`·`[MASKED_PHONE]` 등 플레이스홀더가 DESIGN §2 토큰 색으로 강조 표시된다(raw hex 0).
- AC-3 [Given] 업로드 응답 대기 중 [When] preview 미수신 [Then] "이 이력서로 분석 시작" 버튼이 disabled를 유지하고, 응답 후 enabled가 된다.
> 포맷 안내(구 AC-4)·로딩 skeleton(구 AC-5)은 **T-041**로 이관(repair-plan P1 sizing).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/resume_upload.spec.tsx::test_AC_1_upload_renders_masking_preview_with_evidence_summary
- AC-2 → vitest::podo/apps/web/test/resume_upload.spec.tsx::test_AC_2_placeholders_highlighted_token_color_no_hex
- AC-3 → vitest::podo/apps/web/test/resume_upload.spec.tsx::test_AC_3_start_button_disabled_until_response

## 6-2. TDD opt-out
<!-- TDD 적용 — API mock(fetch) + Testing Library(T-028 인프라: jsdom+@vitejs/plugin-react). 순수 컴포넌트 렌더 단언. -->

## 7. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md)
- Feature: [F-015-resume-upload-ui](../features/F-015-resume-upload-ui.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4) (App Router·API 경유·DB 직접접근 없음)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components) (Button·상태 매트릭스), [## 2 Colors](../../20-system/DESIGN.md#design-2-colors) (토큰·raw hex 금지)
- ADR: [ADR-042](../../90-decisions/boilerplate/ADR-042-ux-flow-quality.md), [ADR-027](../../90-decisions/boilerplate/ADR-027-interface-decision-allocation.md)

## 8. 메모
- 인터페이스 계약(해소 — repair-plan P0): T-034 응답이 `masked_preview` + `evidence_summary`(스킬·경력 수)를 포함하도록 확정됨(T-034 §3 step4·AC-1). 본 task는 그 응답을 소비.
- 해석 확정(evidence 요약 출처): T-034가 결정적 skills 추출(extract_skills_evidence 비-LLM 부분 TS 이식)로 업로드 즉시 계산. LLM 기반 전체 evidence는 분석-후 feed.
- DESIGN cross-check: ResumeUpload/MaskingPreview = 신규 컴포넌트 → DESIGN §7 등록(step5, P1-design). Button.primary는 §7 재사용(primitive 신설 X). 플레이스홀더 강조는 토큰 색.
- 합성 seed → dev fixture 격하(F-015 §4): UI는 업로드 경로가 1급 — seed는 keyless E2E fixture로만(코드 변경은 T-037/stabilize).
- repair-plan 2026-06-07 [default] P1 Plan-sizing: Adopt — 상태 매트릭스(포맷 안내·loading)를 신규 T-041로 분리 → 본 task=업로드+preview(5→3 AC). F-015 §7-1: FAC-4→T-041:AC-1, FAC-5→T-041:AC-2.
- repair-plan 2026-06-07 [default] P1 Plan-design: Adopt — ResumeUpload·MaskingPreview를 DESIGN §7에 등록 line item 추가(write_set에 DESIGN.md); primitive 신설 X(Button 재사용).

## 9. 의존성
- depends_on: [T-034, T-036]   # 업로드 API + 마스킹(masked_preview 응답). mock API로 UI 선행 가능
- read_set: ["docs/20-system/DESIGN.md", "podo/apps/web/components/FeedList.tsx", "podo/apps/web/app/globals.css"]
- write_set: ["podo/apps/web/app/resume/page.tsx", "podo/apps/web/components/ResumeUpload.tsx", "podo/apps/web/components/MaskingPreview.tsx", "podo/apps/web/test/resume_upload.spec.tsx", "docs/20-system/DESIGN.md"]
- assumptions: ["T-034 응답이 masked_preview+evidence_summary 포함(repair-plan P0 확정)", "T-028 RTL 인프라(jsdom+plugin-react) 존재"]
- verifier: "pnpm --filter web test"
