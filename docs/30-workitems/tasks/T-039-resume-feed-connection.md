# T-039-resume-feed-connection

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
T-038 업로드 화면의 "이 이력서로 분석 시작"을 기존 스코어링·feed 흐름에 연결한다 — 클릭 시 업로드 이력서(`resume_id`) 기준으로 스코어링을 기동하고 feed(`/`)로 이동해 **업로드 이력서 기준 적합도 5단계 배지 + 근거(JD 인용)**가 렌더되게 한다(F-015 §3 happy path 완주). M3 로컬 E2E done-line의 UI 종단(§5 E2E).

## 2. 작업 범위
- "분석 시작" 핸들러: 스코어링 기동(T-037 worker `resume_id` 채점) 트리거 + feed 이동(`resume_id` 전달).
- feed가 업로드 이력서의 current run을 렌더하도록 연결(기존 FeedList = 최신 ranking_run = 업로드 run).
- happy path 종단 검증(적합도 배지 렌더).

## 3. 구현 항목
1. `podo/apps/web/components/ResumeUpload.tsx`(T-038 산출) "분석 시작" onClick — 현재: T-038은 disabled 토글까지만 → 변경: 클릭 시 (a) `POST /api/v1/resumes/:id/score` 호출(T-037 확정 트리거) → 채점 완료 대기 + (b) `resume_id`를 feed로 전달해 `router.push('/')`(localStorage 또는 URL param — F-015 §12). → 확인: 클릭 → score 호출 → `/` 이동. (AC-1)
2. `podo/apps/web/components/FeedList.tsx:31` — 현재: `GET /api/v1/feed?cursor=`(최신 current run) → 변경: 업로드 이력서 run이 current(최신 ranking_run)가 되도록 보장(필요 시 `?resume_id=` 전달; 단일 사용자/단일 활성 이력서면 최신 run으로 충분). → 확인: 업로드 채점 후 feed가 그 이력서 기준 항목 렌더. (AC-1)
3. happy path 종단 — 현재: feed는 seed 기준 → 변경: 업로드 이력서 기준 적합도 5단계 배지(JobCard, `fit_level`→`band-*`) + 근거 노출. → 확인: `test_AC_1`(RTL: 업로드→분석시작→feed 적합도 배지) + 전체 흐름은 stabilize의 `scripts/e2e.mjs`(§5 E2E)가 실증. (AC-1)

## 4. 제외 항목
- 업로드 화면/preview(T-038). · 마스킹·스코어링 내부(T-036/T-037). · 합격확률 % 표시(Charter §5 비목표). · 다중 이력서 전환·히스토리(M4). · `scripts/e2e.mjs` 업로드-경로 재배선·웜캐시 재생성(**stabilize-milestone M3 책임** — M2 패턴, feature 비범위).

## 4-1. 변경 예정 파일/경로
<!-- 구현 시점에 채운다. -->

## 5. 완료 조건
"이 이력서로 분석 시작" 클릭 시 업로드 이력서가 채점되고 feed로 이동해 그 이력서 기준 적합도 5단계 배지가 렌더된다.

## 6. Acceptance Criteria
- AC-1 [Given] 업로드·마스킹된 이력서 preview 화면 [When] "이 이력서로 분석 시작" 클릭 [Then] feed 페이지(`/`)로 이동하고 업로드 이력서 기준 적합도 5단계 배지(fit_level 직결)가 렌더된다(가짜 점수 없음; 전체 종단은 §5 E2E가 실증).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/web/test/resume_feed.spec.tsx::test_AC_1_start_navigates_feed_renders_fit_band

## 6-2. TDD opt-out
<!-- TDD 적용 — RTL(navigation mock + feed mock)로 클릭→이동→배지 렌더 단언. 전체 E2E는 scripts/e2e.mjs(stabilize). -->

## 7. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md) (§5 E2E done-line)
- Feature: [F-015-resume-upload-ui](../features/F-015-resume-upload-ui.md)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components) (JobCard·적합도 배지 재사용)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)

## 8. 메모
- 해석 확정(스코어링 트리거 — repair-plan P1): T-037이 `POST /api/v1/resumes/:id/score`(→ worker subprocess)로 확정. 본 task onClick이 그 엔드포인트를 호출 후 feed 이동. NestJS→Python 경계는 architect 권장(T-037 §8).
- repair-plan 2026-06-07 [default] P1 Plan-ambiguity: Adopt — 스코어링 트리거 확정(T-037 POST /resumes/:id/score); AC-1이 그 계약 경유로 명확화(builder가 mock만으로 green 내는 위험 차단).
- 해석 확정: feed는 단일 활성 이력서의 current run(최신 ranking_run) 렌더 — 단일 사용자 M3에선 업로드 채점 run이 곧 current. `resume_id` 명시 전달은 단순화 옵션(localStorage/URL param).
- 적합도 배지 = `fit_level` 1:1(M2 결정, T-028 정합) — 별도 calibration X.

## 9. 의존성
- depends_on: [T-038, T-037]   # 업로드 UI + worker resume_id 채점 둘 다 필요(종단 연결)
- read_set: ["podo/apps/web/components/JobCard.tsx", "podo/apps/web/components/FeedList.tsx"]
- write_set: ["podo/apps/web/components/ResumeUpload.tsx", "podo/apps/web/components/FeedList.tsx", "podo/apps/web/test/resume_feed.spec.tsx"]
- assumptions: ["T-038 업로드/preview 완료", "T-037 worker resume_id 채점 + score 트리거 엔드포인트 완료"]
- verifier: "pnpm --filter web test"
- # T-038과 ResumeUpload.tsx write_set 교집합 → 같은 wave 금지(T-038 후 순차)
