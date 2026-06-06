# F-015-resume-upload-ui: Next.js 이력서 업로드 화면 + 마스킹 preview + 분석 시작

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
Next.js 이력서 업로드 화면을 만든다. 사용자가 `.txt`/`.md` 파일 선택 또는 텍스트 붙여넣기로 이력서를 입력하면, 마스킹본 preview + 추출된 evidence 개수·핵심 skills/경력 요약을 보여주고 "이 이력서로 분석 시작" 버튼으로 기존 스코어링·feed 흐름에 연결한다. preview는 *안전 통제*도 겸함 — 누락 PII를 사용자가 직접 확인 후 분석 시작. **행단위 evidence 편집 UI는 비범위.** 합성 seed → dev fixture 격하.

근거 insight: I-1 (DISCOVERY §15)

## 2. 사용자 가치 (User Story)
- As a **유진(신입/졸업예정 개발자 구직자)**, I want to upload my resume and see a masked preview before analysis starts, so that I can verify my personal info is removed and my skills are correctly extracted before scoring.

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 사용자가 `/resume` 경로 진입 → 업로드 화면 렌더.
2. 파일 선택 또는 텍스트 영역에 붙여넣기.
3. `POST /api/v1/resumes` 호출(F-013) → 응답으로 마스킹본·evidence 요약 수신.
4. 마스킹본 preview 패널 렌더(직접 식별자 플레이스홀더 강조) + evidence 개수(skills N개, 경력 M건).
5. "이 이력서로 분석 시작" 버튼 클릭 → feed 화면으로 이동, 업로드 이력서 기준 공고 스코어링 시작.
6. feed에서 적합도 5단계 배지 + 근거(JD 인용) 렌더.
### Alternate path
1. 붙여넣기 텍스트가 너무 짧거나 evidence 추출 실패 → "이력서에서 기술/경력 정보를 찾지 못했습니다. 다시 입력해보세요." + 재입력 유도.
2. 업로드 중 네트워크 에러 → Toast "업로드 실패. 다시 시도해보세요." + 재시도 가능.
### Fail path
1. 🔴 분석 시작 전 preview 없이 바로 scoring → 사용자가 PII 잔존 인지 불가 — 금지 흐름.
2. 🟡 PDF 업로드 시도 → "현재 .txt / .md 파일 또는 텍스트 붙여넣기만 지원합니다." 안내.

## 4. 범위
- Next.js App Router `/resume` 페이지.
- 업로드 컴포넌트: 파일 드래그앤드롭 + 텍스트 textarea(paste 겸용).
- 마스킹 preview 패널: 마스킹된 텍스트(플레이스홀더 강조, `[MASKED_EMAIL]` 등) + evidence 개수(skills·경력).
- "이 이력서로 분석 시작" Button.primary → feed 이동.
- 로딩·에러·빈 상태: DESIGN.md §7-4 상태 매트릭스 정합.
- 합성 seed를 dev fixture로 격하(M2 무키 E2E 보존 — `scripts/e2e.mjs` 의존성 확인).
- DESIGN.md 토큰 사용 (raw hex 금지).

## 5. 비범위
- 행단위 evidence 편집 UI(원문 재업로드/paste로 대체).
- PDF/docx 업로드.
- 이력서 버전 관리·히스토리 비교.
- 인증·멀티유저(M4).
- 공개 배포(M4).

## 6. 요구사항
- DESIGN.md §7-4 상태 매트릭스: Button.primary(8-상태), 업로드 영역(loading/error/empty), 마스킹 preview(loading skeleton).
- 파일 선택 accept=".txt,.md"만 — PDF 선택 불가(input accept 제한).
- 마스킹 preview에서 플레이스홀더(`[MASKED_EMAIL]`, `[MASKED_PHONE]` 등) 강조 표시.
- evidence 개수: "스킬 N개, 경력 M건 인식" 요약 1줄.
- "분석 시작" 버튼은 preview 확인 전(API 응답 전) disabled.
- ARCH §7-4: App Router 기반, API 경유(`NEXT_PUBLIC_API_BASE_URL`), DB 직접 접근 없음.
- raw hex 색상 사용 금지 — DESIGN.md §2 토큰만 참조(CSS 변수).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** `/resume` 경로에서 파일 선택 또는 paste 후 업로드하면 마스킹 preview 패널이 렌더되고 `[MASKED_EMAIL]`·`[MASKED_PHONE]` 플레이스홀더가 강조 표시된다.
- **FAC-2:** preview 렌더 전(API 응답 대기 중) "이 이력서로 분석 시작" 버튼이 disabled 상태를 유지한다.
- **FAC-3:** "이 이력서로 분석 시작" 클릭 후 feed 페이지(`/`)로 이동하고 업로드 이력서 기준 적합도 5단계 배지가 렌더된다(E2E 검증).
- **FAC-4:** `.txt` 이외 파일 선택 시 "현재 .txt / .md 파일 또는 텍스트 붙여넣기만 지원합니다." 메시지가 표시된다.
- **FAC-5:** 업로드 중 로딩 상태에서 skeleton 카드가 표시되고 가짜 점수가 표시되지 않는다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-038:AC-1, T-038:AC-2
- FAC-2 → T-038:AC-3
- FAC-3 → T-039:AC-1
- FAC-4 → T-041:AC-1
- FAC-5 → T-041:AC-2
> repair-plan 2026-06-07: 상태 매트릭스(FAC-4/5)를 T-038에서 신규 T-041로 분리(P1 sizing).

## 8. Non-functional Requirements
- `prefers-reduced-motion: reduce` 분기 적용 (DESIGN.md §8 모션 정책).
- 접근성: 파일 업로드 input에 label 연결, 키보드 접근 가능.
- Lighthouse Accessibility ≥90 (선택, 측정 기준은 추후).

## 8-1. UX 흐름 품질
- **primary task:** 이력서 업로드 → preview 확인 → 분석 시작 (3단계).
- **empty 흐름:** 파일 미선택·텍스트 비어 있음 → "이력서를 업로드하거나 텍스트를 붙여넣으세요." podo 마스코트 안내.
- **loading 흐름:** 업로드 중 → 업로드 영역 skeleton shimmer + "이력서 분석 중..." 텍스트. "분석 시작" disabled.
- **error 흐름:** API 오류 → Toast "업로드 실패. 다시 시도해보세요." + 업로드 영역 재활성화.
- **accessibility:** 파일 input에 `<label>` 연결 / aria-busy 업로드 중 / 마스킹 preview 영역 role=region.
- **copy 톤:** "포도가 이력서를 살펴볼게요!" (podo 캐릭터 안내 톤). 에러는 "업로드에 실패했어요. 다시 시도해주세요." (친근하되 사실 명확).
- **success metric (HEART):** Task success → 업로드 → 분석 시작 완료율 목표 ≥80% (측정: 실 배포 후 이벤트 로그).

## 9. 엣지 케이스
- 100KB 초과 파일 선택 → "파일이 너무 큽니다(최대 100KB). 더 작은 파일을 사용하세요." 클라이언트 사이드 pre-check.
- textarea에 HTML 태그 입력 → 그대로 plain text로 전송(sanitize 없음, 서버 DTO에서 처리).
- evidence_count = 0 반환 → preview 패널에 "기술/경력 정보를 찾지 못했습니다. 다시 확인해보세요." + 재입력 유도, "분석 시작" disabled 유지.

## 10. 의존성
- F-013(resume-upload-api) — `POST /api/v1/resumes` 엔드포인트. T-038은 T-034 이후.
- F-014(resume-parse-pii) — 마스킹본 + evidence 요약이 API 응답에 포함되어야 preview 렌더 가능. T-038은 T-036 이후(또는 mock API로 UI 선행 가능).

## 11. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§4 G4, §8 흐름2)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components), [## 2 Colors](../../20-system/DESIGN.md#design-2-colors)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 12. 열린 질문
- 마스킹 preview 패널의 텍스트 표현 방식: 전체 마스킹본 텍스트를 보여줄지 vs 플레이스홀더 위치만 하이라이트 목록으로 보여줄지 → T-038에서 결정(긴 이력서는 스크롤 필요, 요약 목록이 UX 상 낫다는 가정).
- feed 연결 시 `resume_id`를 어떤 방식으로 feed 페이지에 전달할지(URL param vs localStorage vs server session) → M3 로컬 E2E 범위에서는 localStorage/URL param으로 단순하게.
