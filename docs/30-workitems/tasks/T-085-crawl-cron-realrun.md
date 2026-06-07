# T-085-crawl-cron-realrun

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
`.github/workflows/crawl-jobs.yml`(T-019 skeleton)을 실가동한다. **매일 오전 cron**으로 crawler(GitHub Actions 직접 실행 — AWS 서비스 아님)가 공식 소스에서 공고를 수집하고 `diff_status`(신규/마감)를 갱신한다. 크롤 실패 시 커버리지 패널/로그에 노출(Fail #3 조용한 실패 금지). 알림 *발송* 기능은 비범위. [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)(D-CRAWL·D-DEPLOY).

## 2. 작업 범위
- `.github/workflows/crawl-jobs.yml` 실가동: `schedule: cron` 실 시각 설정 + `workflow_dispatch` 유지 + crawler Python 실 실행 단계.
- crawler가 **`DATABASE_URL`만** GitHub Secrets에서 주입받아 실 RDS에 upsert. **`OPENAI_API_KEY` 불요** — crawler=Collector라 LLM 미호출(ARCH §3-2 경계, `crawler/__main__.py`가 이미 무키 전제).
- 크롤 실패 시 GHA job fail + 실패 로그 출력. 가시화는 **기존 `crawl_runs` 테이블**(M2 T-024가 crawler에서 이미 write, 커버리지 API가 channel별 `MAX(run_at WHERE status='success')` 파생) 재사용 — 새 컬럼/migration 불요.
- `diff_status` 갱신 검증: cron 실행 후 `job_postings` 테이블에 신규/마감 행이 반영됨을 스모크 쿼리로 확인.
- cron 타임존 설정(한국 오전 기준 UTC 변환 — 오전 첫 진입 전 반영).

## 3. 구현 항목
1. `.github/workflows/crawl-jobs.yml` — 현재: skeleton(cron trigger + no-op) → 변경: `schedule: - cron: '0 21 * * *'`(UTC 21:00 = KST 06:00) + `workflow_dispatch` 유지 + `jobs.crawl` step: `uv run python -m crawler.main`(또는 동등 진입점) → 확인: `actionlint` exit 0. (AC-1)
2. crawler GitHub Secrets 연결(사용자 수행) — **`DATABASE_URL`만** 저장소 Secrets에 등록(OPENAI_API_KEY 불요 — crawler는 LLM 미호출). → 확인: workflow에서 `${{ secrets.DATABASE_URL }}` 참조 존재 + 실값 미커밋. (AC-2)
3. `crawler/main.py`(또는 진입점) — 현재: 존재(M4/M5 완성) → 변경: 크롤 결과(수집 수·실패 여부)를 stdout에 출력 + 실패 시 non-zero exit code → GHA job fail 전파. → 확인: `python -m crawler.main --dry-run` 또는 단위 테스트에서 실패 시 non-zero exit 확인. (AC-3)
4. 크롤 실패 가시화 — **기존 `crawl_runs` 테이블 재사용**(M2 T-024 crawler가 run별 1행 append, 커버리지 API가 channel별 last success 파생 — *새 컬럼/migration 불요*). 미구현분만: 커버리지 API가 `crawl_runs` 기반 마지막 성공/실패를 반환하는지 확인·보강. → 확인: 커버리지 API 응답에 마지막 크롤 성공 시각·실패 반영. (AC-3)

## 4. 제외 항목
- 이메일/푸시 알림 발송 — 비범위(M6 §1, M7 이후).
- crawler AWS 호스팅(ECS/Lambda) — crawler = GitHub Actions cron(ADR-101 D-DEPLOY).
- Playwright 승격 — httpx 정적 fetch 기본(ADR-101 D-CRAWL). 필요 시 A-1 관측 후.
- 크롤 커버리지 UI 변경 — M4/M5 완성분 재활용.

## 4-1. 변경 예정 파일/경로
- `.github/workflows/crawl-jobs.yml`
- `crawler/src/crawler/__main__.py`(또는 진입점) — exit code 보장 확인/최소 수정
- `podo/apps/api/src/coverage/**` — `crawl_runs` 기반 마지막 성공/실패 반환(미구현분만)
- *(새 migration 불요 — 기존 `crawl_runs` 재사용)*

## 5. 완료 조건
`crawl-jobs` cron이 매일 오전 자동 실행되어 `job_postings`의 `diff_status`를 갱신하고, 실패 시 GHA job이 fail 상태로 표시되며 커버리지 패널에 마지막 성공 시각이 반영된다.

## 6. Acceptance Criteria
- AC-1 [Given] `.github/workflows/crawl-jobs.yml` [When] `actionlint` [Then] 파일이 유효하고 `schedule: cron`(UTC 기준 KST 오전) + `workflow_dispatch` 트리거를 모두 가진다.
- AC-2 [Given] workflow 파일 전체 [When] `git grep -rn "DATABASE_URL" -- .github/` [Then] 실값 하드코딩 행이 0개다(secrets 참조만). crawler workflow에 `OPENAI_API_KEY` 참조가 없다(Collector 경계 — LLM 미호출).
- AC-3 [Given] crawler가 수집 실패(네트워크 오류 시뮬레이션) [When] `python -m crawler.main` [Then] non-zero exit code를 반환하고, 커버리지 패널 API가 `lastCrawlAt`·`lastCrawlSuccess: false`를 포함하는 응답을 반환한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → `actionlint .github/workflows/crawl-jobs.yml` exit 0; `grep -c "schedule" .github/workflows/crawl-jobs.yml` ≥ 1
- AC-2 → `git grep -rn "sk-\|postgres://.*:.*@" -- .github/` exit 0 (매칭 0)
- AC-3 → `pytest crawler/tests/test_main_exit_code.py` (실패 시 non-zero exit) + `pytest podo/apps/api/test/coverage.e2e-spec.ts` (lastCrawlAt 필드 포함)

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Feature: [F-025-service-deploy-pipelines](../features/F-025-service-deploy-pipelines.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-3 cron·크롤러)
- Architecture-Iface: [ARCH ## 7-3 백엔드/크롤러](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-CRAWL·D-DEPLOY)

## 8. 메모
- cron 시각: `0 21 * * *`(UTC) = KST 06:00. 사용자 오전 첫 진입 전 반영 목표. 타임존은 GHA schedule이 UTC 고정이므로 변환 필요.
- `last_crawl` 컬럼이 M4/M5에 이미 존재하면 §3-4 스킵. 존재 여부 확인 후 migration 결정.
- 알림 발송(이메일/푸시)은 이 task 범위 아님 — cron은 수집만.

## 9. 의존성
- depends_on: [T-082, T-083]   # RDS(실 DB) + Secrets 연결 후 실행 가능
- write_set: [".github/workflows/crawl-jobs.yml", "crawler/src/crawler/__main__.py", "podo/apps/api/src/coverage/**"]
- assumptions: ["T-082 RDS가 apply됨", "crawler M4/M5 기능 완성됨 + 기존 `crawl_runs` write 경로 존재(M2)", "GitHub Secrets에 DATABASE_URL 등록됨(사용자 수행) — OPENAI_API_KEY 불요"]
- verifier: "actionlint .github/workflows/crawl-jobs.yml"
