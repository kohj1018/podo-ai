# T-096-resume-edit-and-score-trigger

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
이력서 **편집 재진입**(마이페이지→/resume)을 지원하고, **신규/수정 시에만 1회 채점** 트리거되도록 lifecycle을 정리한다(피드 탐색은 미트리거 — 사용자 결정 §2-C).

## 2. 작업 범위
프론트 lifecycle + (필요 시) 중복 채점 방지. 알고리즘 무변경.

## 3. 구현 항목
1. `podo/apps/web/components/ResumeUpload.tsx:115-130` (handleStartAnalysis) — 현재: 제출 시 `POST :id/score` 1회 후 `localStorage('podo_active_resume_id')` 세팅 → 변경: 그대로 유지(신규/수정 제출 경로에서만 호출). 편집=새 입력 제출 → 새 resume_id 생성(append-only) → 그 id score → active 교체. → 확인: 수정 시 새 id 채점 1회 (AC-1).
2. 편집 진입 — 변경: /resume를 편집 모드로 열 때 안내("새로 작성해 교체해요" — content는 마스킹본이라 원문 prefill 불가). 기존 active를 교체하는 흐름 명시. → 확인: 편집→새 resume→채점 (AC-1).
3. 미트리거 보장 — 변경: 피드 진입(`feed/meta` GET)·단순 네비는 score 호출 경로가 없음을 회귀로 고정(현재도 read-only). 동일 active resume 재제출(내용 동일) 시 중복 채점 방지(선택: 직전 active와 동일 content면 score 스킵). → 확인: 탐색 미트리거 (AC-2).
4. `podo/apps/web/components/ResumeUpload.tsx:118-130` (handleStartAnalysis) — 현재: `await fetch(:id/score, {POST})`의 **`res.ok`를 검사하지 않고** 곧바로 `localStorage` 세팅 + `/` 이동(score 실패가 조용히 묻힘) → 변경: `res.ok` 검사, 실패(non-2xx/네트워크) 시 **피드 이동 중단 + 에러 메시지/재시도** 표시. → 확인: 실패 시 미이동 (AC-3).

## 4. 제외 항목
- 다중 이력서 버전 보관/전환(단일 active 유지).
- 마스킹본 → 원문 복원 prefill(불가 — raw 미저장).

## 4-1. 변경 예정 파일/경로

## 5. 완료 조건
이력서를 수정하면 새 버전 생성 + 채점 1회가 돌고, 피드 재진입·탐색은 재채점하지 않는다.

## 6. Acceptance Criteria
- AC-1 [Given] 기존 이력서 사용자 [When] /resume에서 수정 제출 [Then] 새 resume가 생성되고 그 id로 채점이 정확히 1회 트리거된다.
- AC-2 [Given] 채점 완료된 사용자 [When] 피드 재진입·네비 탐색 [Then] 추가 채점이 트리거되지 않는다(score 호출 0).
- AC-3 [Given] "분석 시작" 클릭 시 `POST :id/score`가 실패(non-2xx 또는 네트워크 오류) [When] 응답/에러 [Then] 피드로 이동하지 않고 에러 메시지 + 재시도를 표시한다(현재 `res.ok` 미검사 후 무조건 이동 — 회귀 차단).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → podo/apps/web/test/resume_lifecycle.spec.tsx > test_AC_1_edit_creates_new_and_scores_once
- AC-2 → podo/apps/web/test/resume_lifecycle.spec.tsx > test_AC_2_browsing_no_rescore
- AC-3 → podo/apps/web/test/resume_lifecycle.spec.tsx > test_AC_3_score_failure_no_nav_shows_error

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M7-ux-completion](../milestones/M7-ux-completion.md)
- Feature: [F-030-resume-input-redesign](../features/F-030-resume-input-redesign.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) · [## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components)
- ADR: [ADR-105](../../90-decisions/project/ADR-105-pii-masking-policy.md) · [ADR-106](../../90-decisions/project/ADR-106-worker-trigger-boundary.md)(비동기 채점 트리거)

## 8. 메모
- 해석 확정: "수정" = append-only 새 resume row 생성(content immutable blob이라 갱신 불가) → 새 id 채점 → active 교체. 동일 content 재제출은 채점 스킵(중복 방지).
- repair-plan 2026-06-10 [default] P1 Plan-design: Adopt — handleStartAnalysis가 score POST `res.ok` 미검사 후 무조건 `/` 이동(실측 ResumeUpload.tsx:121-129) → AC-3(실패 시 미이동+에러+재시도) 신설. 채점 트리거 robustness는 T-096 소유라 T-102 포괄 스윕 대신 여기에 명시 AC로.

## 9. 의존성
- depends_on: [T-095]
- write_set: ["podo/apps/web/components/ResumeUpload.tsx"]
- 비고: ResumeUpload.tsx를 T-095와 공유 → T-095 종료 후.
