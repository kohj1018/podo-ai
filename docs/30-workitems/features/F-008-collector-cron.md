# F-008-collector-cron: crawler 영속 + 일일 cron (수집 골격)

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 요약
검증된 crawler fetch/select(T-012/T-013, 현재 함수 수준)를 실제 영속과 스케줄에 연결한다 — 토스·당근 fetch 결과를 `job_postings`에 upsert하고 신규/마감 diff를 반영하며, 수집 성공/실패·마지막 시각을 `crawl_runs`(coverage)에 기록하고, `python -m crawler` 진입점 + GitHub Actions `crawl-jobs` 일일 cron을 둔다. **crawl(LLM無)과 score(LLM有)를 분리**해 수집 실패가 OpenAI 비용을 태우지 않게 한다.

## 2. 사용자 가치 (User Story) — Type=technical-enabler 이므로 기술적 근거
- **무엇/왜:** T-012는 fetch+upsert+diff *함수*까지, 스케줄 트리거·영속 없음. 이를 닫아 "매일 신규 공고가 수집되어 쌓인다"가 실제로 동작. DISCOVERY F1·F3 서비스. Fail #1(알림 미수신)·#3(커버리지 미고지) 차단의 데이터원.
- **서비스하는 결정/가정:** ARCH §7-3 주기 수집 스케줄러(GH Actions cron) · §3-2 규칙1(crawler→`job_postings`/`crawl_runs` 소유) · 가정 A-1(크롤링 실증, 2026-06-04).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. `python -m crawler`가 토스·당근 fetch → 정규화 → `job_postings` upsert + 전일 대비 diff(신규/마감).
2. 수집 결과(채널·성공/실패·건수·마지막 성공 시각)를 `crawl_runs`에 기록.
3. GitHub Actions `crawl-jobs`가 매일 오전 cron으로 위를 실행.
### Alternate path
1. 신규가 빈약한 날 → 건수 0도 정상 기록(조용한 누락 아님).
### Fail path
1. 🔴 단건 502/404 → 전체 루프 중단 없이 skip+log(QA-M1-005 정합), 채널 실패를 `crawl_runs`에 노출(Fail #3 차단).

## 4. 범위
- crawler 영속: fetch/select → `job_postings` upsert(crawler 소유) + diff_status(신규/유지/마감임박/마감).
- coverage: `crawl_runs`에 **run별 1행**(채널·run_at·status·counts) 기록 — `last_success_at`는 조회 시 채널별 `MAX(run_at WHERE status='success')`로 파생(F-006 정합).
- 실행 진입점 `crawler/src/crawler/__main__.py`.
- GitHub Actions `crawl-jobs` 일일 cron + manual dispatch. crawl(LLM無)/score(LLM有) 분리.

## 5. 비범위
- score 단계(F-007이 별도 실행) — 본 workflow는 수집만.
- 추가 채널(토스·당근 2곳 유지, Charter §5).
- Playwright 승격(정적 httpx 우선, 필요 시 후속 — ADR-101 D-CRAWL).
- 알림 푸시(미정 채널, ARCH §10).

## 6. 요구사항
- crawler는 `job_postings`·`crawl_runs`만 write(§3-2 소유권).
- 단건 실패가 전체 수집을 중단시키지 않음(try/except skip+log — QA-M1-005).
- 실패를 조용히 넘기지 않고 `crawl_runs`에 노출(Fail #3 — ARCH §7-3).
- cron secrets(`DATABASE_URL` 등)는 GH secrets(레포 커밋 금지). crawl은 `OPENAI_API_KEY` 불필요(LLM 분리).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** `python -m crawler`가 토스·당근을 fetch해 `job_postings`에 upsert하고 신규/마감 diff_status를 설정한다.
- **FAC-2:** 수집 run별 status·counts·run_at이 `crawl_runs`에 1행 append되고(채널별 `last_success_at`는 `MAX(success)` 파생), 단건 fetch 실패는 skip+log되어 채널 실패로 표면화된다.
- **FAC-3:** `.github/workflows/crawl-jobs.yml`이 cron 및 manual dispatch로 crawler 진입점을 실행한다.
- **FAC-4:** crawl 단계가 `OPENAI_API_KEY` 없이 동작한다(LLM 분리).

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 (upsert+diff) → T-024:AC-1
- FAC-2 (coverage 기록+단건 skip) → T-024:AC-2
- FAC-3 (cron workflow) → T-025:AC-1
- FAC-4 (LLM 분리) → T-025:AC-2

## 8. Non-functional Requirements
- 신뢰성: 누락 0(Fail #1)·커버리지 투명(Fail #3). 운영성: fetch 실패율·캡차율 로깅(ARCH §8 운영성).
- 보안: secrets는 GH secrets. ToS 준수(운영 상시 원칙).

## 8-1. UX 흐름 품질
(해당 없음 — 비-UI. coverage *표시*는 F-010.)

## 9. 엣지 케이스
- 토스 상세 fetch 단건 502(QA-M1-005) → skip+log.
- 동일 공고 재수집 중복 → upsert 멱등.
- 신규 0건 날 → 정상 기록.

## 10. 의존성
- **선행:** T-020(스키마 — `job_postings`/`crawl_runs`), T-021(Python DB 접근).
- **병렬 가능:** F-007과 독립(서로 다른 소유 테이블).

## 11. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature(선행): [F-002-collector](F-002-collector.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§5 수집 흐름, §6 외부 연동)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3) (주기 수집 스케줄러)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-DEPLOY·D-CRAWL)

## 12. 열린 질문
- cron 시각(오전 N시 KST) 확정.
- (닫힘, cross-LLM P1 회수) `crawl_runs` = **run별 1행 append** + `last_success_at` 파생(F-006 §4/§6 확정).
