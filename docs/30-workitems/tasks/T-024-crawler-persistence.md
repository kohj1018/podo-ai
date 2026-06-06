# T-024-crawler-persistence

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
crawler fetch/select(T-012/T-013, 현재 함수)를 DB 영속에 연결한다 — 토스·당근 fetch 결과를 `job_postings`에 upsert하고 신규/마감 diff를 설정하며, 수집 결과를 `crawl_runs`에 **run별 1행** 기록한다(cross-LLM P1 회수). 단건 실패는 skip+log(QA-M1-005).

## 2. 작업 범위
- crawler 영속: fetch/select → `job_postings` upsert(crawler 소유) + `diff_status`(신규/유지/마감임박/마감).
- coverage: `crawl_runs`에 run별 1행(channel·run_at·status·new_count·closed_count·error). `last_success_at`는 조회 시 `MAX(run_at WHERE success)` 파생(F-006).
- 단건 fetch 실패 → skip+log(전체 루프 중단 금지, QA-M1-005).

## 3. 구현 항목
1. `crawler/src/crawler/persistence.py` — 현재: 없음 → 변경: `upsert_jobs(db, jobs)` (`job_postings` upsert + 전일 대비 diff_status 계산), crawler만 write(§3-2). → 확인: 신규 `test_persistence.py`가 upsert 멱등 + diff 설정. (AC-1)
2. `persistence.py` — `record_crawl_run(db, channel, status, counts, error)` → `crawl_runs`에 **1행 append**(run_at=now 주입값). → 확인: 2회 수집 시 2행, 채널별 `MAX(run_at WHERE success)` 조회 가능. (AC-2)
3. `crawler/src/crawler/fetch_jobs.py` — 현재: 토스 상세 fetch `raise_for_status`(QA-M1-005) → 변경: 단건을 `try/except httpx.HTTPStatusError`로 감싸 skip+log(이미 파싱분 보존). → 확인: 단건 502 fixture에서 전체 루프 계속 + `crawl_runs.status='partial'`. (AC-2)

## 4. 제외 항목
- score 단계(F-007) · cron 트리거/진입점(T-025) · 추가 채널 · Playwright 승격.

## 4-1. 변경 예정 파일/경로
- `crawler/src/crawler/persistence.py`, `crawler/src/crawler/fetch_jobs.py`, `crawler/tests/test_persistence.py`

## 5. 완료 조건
crawler가 토스·당근을 fetch해 `job_postings`에 upsert+diff하고, 수집 결과를 `crawl_runs`에 run별 1행 기록하며, 단건 실패가 전체를 중단시키지 않는다.

## 6. Acceptance Criteria
- AC-1 [Given] 토스·당근 fetch 결과 [When] `upsert_jobs` [Then] `job_postings`에 멱등 upsert되고 신규/마감 `diff_status`가 설정된다(crawler만 write).
- AC-2 [Given] 수집 1회(일부 단건 502 포함) [When] crawler 실행 [Then] `crawl_runs`에 run별 1행이 append되고(채널별 `last_success_at` 파생 가능), 단건 502는 skip+log되어 루프가 계속되며 `status`가 실패를 표면화한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_persistence.py::test_AC_1_upsert_jobs_idempotent_diff
- AC-2 → pytest::crawler/tests/test_persistence.py::test_AC_2_crawl_run_row_and_single_failure_skip

## 6-2. TDD opt-out
<!-- TDD 적용 — fetch는 fixture/HTTP mock, DB는 compose PG. -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-008-collector-cron](../features/F-008-collector-cron.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§5 수집 흐름, §3-2 소유권)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- QA: [QA_FINDINGS QA-M1-005](../../40-validation/QA_FINDINGS.md) (toss 상세 fetch 중단)

## 8. 메모
- 해석 확정: `crawl_runs` = run별 1행(M2-repair-3) — last_success_at 파생. QA-M1-005 회수(단건 skip).
- `run_at` 등 시간은 *주입값*(결정성 — Date.now 직접 X, 호출자가 전달).

## 9. 의존성
- depends_on: [T-020, T-021]
- read_set: ["crawler/src/crawler/selection.py", "ai/core/src/core/db.py"]
- write_set: ["crawler/src/crawler/persistence.py", "crawler/src/crawler/fetch_jobs.py", "crawler/tests/test_persistence.py"]
- assumptions: ["T-020 마이그레이션 DB", "T-021 core.db 가용"]
- verifier: "uv run pytest crawler/tests/test_persistence.py"
