# T-095-resume-two-mode-redesign

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
"너무 구린" `ResumeUpload`를 두 입력 모드로 재설계한다: 파일 업로드(UI 개선) + 직접 작성 폼(항목 scaffold → 표준 헤딩 마크다운). **구조화 영속·알고리즘 무변경**(M7 §2-C·§2-H).

## 2. 작업 범위
프론트만 — ResumeUpload/신규 ResumeForm + /resume 셸. 백엔드(POST 흐름)·마스킹 무변경.

## 3. 구현 항목
1. `podo/apps/web/components/ResumeUpload.tsx` — 현재: 단일 textarea + 날 `<input type=file>` + plain 버튼(132-225행) → 변경: **모드 토글**(파일/직접작성). 파일 모드=기존 handleFileChange/handleUpload 유지 + 드롭존·안내 UI 개선(DESIGN 토큰, raw hex 0). → 확인: 파일 모드 기존 흐름 동작 (AC-1).
2. 신규 `podo/apps/web/components/ResumeForm.tsx` — 현재: 없음 → 변경: 항목 입력란(소개·경력·학력·자격증/수상·기술스택) state. 제출 시 **표준 헤딩 마크다운 조립**: 채워진 항목만 `## 소개\n{값}\n\n## 경력\n{값}…`로 join → 부모에 string 전달. 빈 항목 헤딩 생략. → 확인: 조립 문자열 정확 (AC-2).
3. `ResumeUpload` 직접작성 제출 — 변경: 조립 마크다운을 **기존 `{text}` JSON POST 경로**(현 90-96행)에 그대로 태움(`source:paste`, 라벨 `format:md`). → 확인: 동일 응답·preview (AC-2, AC-3).
4. 공통 후처리 — 변경: 두 모드 모두 응답 `masked_preview`→`MaskingPreview`→"분석 시작"(기존 handleStartAnalysis 재사용). 8-상태(빈/로딩 skeleton/에러), primary CTA 1개. → 확인 (AC-3).

## 4. 제외 항목
- 구조화 데이터 모델(섹션 별도 영속)·section-aware 추출·파일 자동 섹션분배 — M7 §4.
- 채점 트리거 lifecycle(T-096) · 편집 prefill(T-096).

## 4-1. 변경 예정 파일/경로

## 5. 완료 조건
사용자가 파일 업로드 또는 항목 폼 직접작성으로 이력서를 입력하고, 두 모드 모두 마스킹 preview 후 분석을 시작한다.

## 6. Acceptance Criteria
- AC-1 [Given] 파일 모드 [When] `.txt/.md` 업로드 [Then] 기존 흐름(마스킹·preview·분석시작)이 개선된 UI로 동작한다(비허용 포맷/100KB 초과 안내 유지).
- AC-2 [Given] 직접작성 폼에 소개·경력 등 입력 [When] 제출 [Then] 채워진 항목만 표준 헤딩 마크다운(`## 소개`/`## 경력`/…)으로 조립돼 기존 `{text}` POST로 전송된다.
- AC-3 [Given] 두 모드 중 하나로 업로드 성공 [When] 응답 수신 [Then] MaskingPreview가 표시되고 "분석 시작"이 활성화된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/resume_upload.spec.tsx > test_AC_1_file_mode_flow
- AC-2 → podo/apps/web/test/resume_form.spec.tsx > test_AC_2_sections_to_markdown
- AC-3 → podo/apps/web/test/resume_upload.spec.tsx > test_AC_3_preview_and_start

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-030-resume-input-redesign](../features/F-030-resume-input-redesign.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) · [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components) · [## 2 Colors](../../20-system/DESIGN.md#design-2-colors)
- ADR: [ADR-105](../../90-decisions/project/ADR-105-pii-masking-policy.md)

## 8. 메모
- 해석 확정: AC-2 직접작성 출력 = 표준 헤딩 마크다운 blob을 기존 `{text}` 경로로 전송(별도 섹션 영속 없음 — 알고리즘 무변경, §2-H). 헤딩은 워커 파싱(`## Skills/기술스택`·`## 경력`)과 정합하도록 한글 표준 헤딩 사용.

## 9. 의존성
- depends_on: []
- write_set: ["podo/apps/web/components/ResumeUpload.tsx", "podo/apps/web/components/ResumeForm.tsx", "podo/apps/web/app/resume/page.tsx"]
