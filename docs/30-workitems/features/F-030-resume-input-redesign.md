# F-030-resume-input-redesign

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
"너무 구린" resume 페이지를 두 입력 모드로 재설계한다: **모드1 파일 업로드(.txt/.md, 기존 흐름·UI만 개선)** + **모드2 직접 작성 폼(소개/경력/학력/자격증/기술스택 항목 scaffold → 표준 헤딩 마크다운 조립 → 기존 `{text}` POST 흐름)**. **구조화 데이터 모델 미도입** — 알고리즘·스키마 무변경(M7 §2-C·§2-H). 추가로 이력서 **신규/수정 시에만 채점**하도록 lifecycle을 정리한다.

## 2. 사용자 가치 (User Story)
- As 유진(Charter §2.1), I want 파일이 없어도 항목별로 이력서를 직접 작성하고 싶다, so that 바로 분석을 시작한다.
- As 유진, I want 이력서를 수정하면 그때만 다시 분석되길 바란다, so that 불필요한 재분석·혼란이 없다.

## 3. 핵심 시나리오 (Feature-level)
- **happy(모드1)**: .md 업로드 → 마스킹 preview → 분석 시작 → 피드.
- **happy(모드2)**: 항목 폼 작성 → 표준 헤딩 마크다운 조립 → 마스킹 preview → 분석 시작 → 피드.
- **alternate**: 마이페이지에서 편집 진입 → 내용 수정 → 새 버전 생성 → 1회 채점.
- **fail**: 빈 입력 제출 → RESUME_EMPTY 안내. 비허용 포맷 → 415 안내.

## 4. 범위
- ResumeUpload 재설계(파일 모드 UI 개선 + 직접작성 폼).
- 폼 항목 → 표준 마크다운 헤딩(`## 소개`/`## 경력`/`## 학력`/`## 자격증`/`## 기술스택`) 조립 후 기존 POST.
- 채점 트리거 lifecycle: 신규/수정 시에만 1회, 피드 탐색은 미트리거.
- 이력서 편집 재진입(마이페이지→/resume).

## 5. 비범위
- 구조화 데이터 모델(섹션 별도 영속)·section-aware 추출·섹션별 임베딩(M7 §4 — 알고리즘 무변경 보존).
- 파일 자동 섹션분배(LLM 파싱) — 모드2는 직접작성, 업로드는 blob 그대로. (자동분배는 후속 옵션.)
- 다중 이력서 버전 관리.

## 6. 요구사항
- **알고리즘 불변식**: 조립 마크다운은 기존 마스킹 → `content` blob → 기존 추출/채점. 추출 프롬프트·캐시버전·골든페어 무변경(GS-1/GS-2 보존).
- raw PII 미저장 — 업로드·직접작성 모두 마스킹본만(M3 / ADR-105).
- 직접작성 원문 보존(재작성 0). 빈 항목은 헤딩 생략.

## 7. Feature-level Acceptance Criteria
- FAC-1 사용자가 파일 업로드 또는 직접 작성으로 이력서를 입력하고 분석을 시작한다.
- FAC-2 직접작성이 표준 헤딩 마크다운으로 조립돼 기존 흐름(마스킹·채점)에 무변경으로 태워진다.
- FAC-3 이력서가 신규/수정될 때만 채점이 1회 트리거되고, 단순 탐색은 미트리거한다.

## 7-1. FAC ↔ AC 매핑표
- FAC-1 → T-095:AC-1, T-095:AC-2, T-095:AC-3
- FAC-2 → T-095:AC-2
- FAC-3 → T-096:AC-1, T-096:AC-2, T-096:AC-3 (채점 트리거 실패 복구 — repair-plan)

## 8. Non-functional Requirements
- 보안: PII 마스킹(ADR-105), raw 미영속. 100KB 상한(기존).
- 결정성: 채점 입력 포맷 불변(캐시 키 무변경, ARCH §7-3).

## 8-1. UX 흐름 품질
- primary task: 이력서 입력 후 "분석 시작" 1행동.
- empty/loading/error: 빈 입력 안내, 업로드/마스킹 로딩 skeleton(가짜 preview 0), 포맷/크기 에러.
- accessibility: 폼 label 연결, 항목 fieldset, 키보드.
- copy 톤: "포도가 분석할게요" 동반자 톤.
- success metric(HEART-Task success): resume 작성 완료율(온보딩 전환) — 실데이터 DISCOVERY §14.

## 9. 엣지 케이스
- 모드2 일부 항목만 작성 → 작성된 항목만 헤딩 포함.
- 수정인데 내용 동일 → 채점 중복 방지(동일 content면 재채점 스킵 권장).
- 업로드와 직접작성 동시 입력 → 우선순위 명시(파일 우선, 기존 동작).

## 10. 의존성
- 기존 ResumesController/Service(`POST /api/v1/resumes`, `:id/score`) · MaskingPreview.

## 11. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) · [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- 스코어링 계약: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-105](../../90-decisions/project/ADR-105-pii-masking-policy.md)

## 12. 열린 질문
- "수정"의 영속 모델: append-only 새 row vs 동일 row 갱신(현 content immutable → append-only 권장).
- 직접작성 폼 항목 셋의 고정 vs 사용자 추가 가능.
