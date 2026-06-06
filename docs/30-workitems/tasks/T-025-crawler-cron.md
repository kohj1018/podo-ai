# T-025-crawler-cron

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
`python -m crawler` 진입점 + GitHub Actions `crawl-jobs` 일일 cron을 만든다. **crawl(LLM無)과 score(LLM有)를 분리**해 수집 실패가 OpenAI 비용을 태우지 않게 한다.

## 2. 작업 범위
- `crawler/src/crawler/__main__.py` 진입점: fetch/select → `upsert_jobs`(T-024) + `record_crawl_run`.
- `.github/workflows/crawl-jobs.yml` 실동작: schedule(매일 오전 cron) + `workflow_dispatch`, `python -m crawler` 실행. crawl은 `OPENAI_API_KEY` 불요.

## 3. 구현 항목
1. `crawler/src/crawler/__main__.py` — 현재: 없음 → 변경: `main()` — fetch(토스·당근) → `upsert_jobs` → `record_crawl_run`. `run_at`은 진입점에서 1회 생성해 주입(결정성). → 확인: `python -m crawler`가 DB에 job_postings+crawl_runs 기록. (AC-1)
2. `.github/workflows/crawl-jobs.yml` — 현재: skeleton(T-019) → 변경: `on: { schedule: [{cron: "0 22 * * *"}], workflow_dispatch: {} }` + PG/secrets(`DATABASE_URL`) + `uv run python -m crawler`. **`OPENAI_API_KEY` env 미주입**(crawl/score 분리). → 확인: `actionlint` 통과 + dispatch dry-run. (AC-1)
3. crawl이 `OPENAI_API_KEY` 없이 동작함을 보장(crawler 코드가 OpenAI import/호출 0). → 확인: env에서 `OPENAI_API_KEY` 제거 후 `python -m crawler` 정상. (AC-2)

## 4. 제외 항목
- score 단계(F-007 worker는 별도 실행/워크플로) · 추가 채널 · 알림 · Playwright.

## 4-1. 변경 예정 파일/경로
- `crawler/src/crawler/__main__.py`, `.github/workflows/crawl-jobs.yml`, `crawler/tests/test_entry.py`

## 5. 완료 조건
`python -m crawler`가 수집→영속을 완주하고, `crawl-jobs` workflow가 cron/dispatch로 이를 실행하며, crawl이 `OPENAI_API_KEY` 없이 동작한다.

## 6. Acceptance Criteria
- AC-1 [Given] DB + `DATABASE_URL` [When] `python -m crawler`(또는 `crawl-jobs` dispatch) [Then] 토스·당근 수집분이 `job_postings`에 upsert되고 `crawl_runs`에 run 1행이 기록된다.
- AC-2 [Given] `OPENAI_API_KEY` 미설정 환경 [When] `python -m crawler` [Then] crawl이 정상 완주한다(LLM 분리 — OpenAI 호출 0).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_entry.py::test_AC_1_entry_crawls_and_persists
- AC-2 → pytest::crawler/tests/test_entry.py::test_AC_2_crawl_runs_without_openai_key

## 6-2. TDD opt-out
<!-- TDD 적용 — 진입점은 fetch mock + compose PG. workflow는 actionlint. -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-008-collector-cron](../features/F-008-collector-cron.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §7-3 cron)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3) (주기 수집 스케줄러)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-DEPLOY)

## 8. 메모
- 해석 확정: crawl/score 분리 — `crawl-jobs`는 `OPENAI_API_KEY` 미주입(F-008 FAC-4). cron 시각 `0 22 * * *`(UTC=KST 07:00) 가정, 구현 시 확정.
- secrets는 GH secrets(`.env` 커밋 금지, AGENTS.md).
- repair-plan 2026-06-06 [default] P1 Plan-dep: Adopt — depends_on에 T-019 추가(crawl-jobs.yml skeleton→실동작 write 순서).

## 9. 의존성
- depends_on: [T-019, T-024]   # T-019가 crawl-jobs.yml skeleton 생성 → 본 task가 실동작 수정(같은 파일 write 순서 — cross-LLM P1)
- read_set: ["crawler/src/crawler/persistence.py"]
- write_set: ["crawler/src/crawler/__main__.py", ".github/workflows/crawl-jobs.yml", "crawler/tests/test_entry.py"]
- assumptions: ["GH secrets DATABASE_URL 설정"]
- verifier: "uv run pytest crawler/tests/test_entry.py && actionlint .github/workflows/crawl-jobs.yml"
