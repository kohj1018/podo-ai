# T-012-fetch-jobs

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
토스·당근 공식 채용 JSON API에서 공고를 수집·정규화하고 `job_postings`에 upsert + 신규/마감 diff를 산출한다(`crawler`). 키워드 필터로 비-엔지니어링 직군 차단 (SPEC §9-1·§9-2).

## 2. 작업 범위
- 토스(`api-public.toss.im/.../career/jobs` 목록 + `/jobs/{id}` 상세) · 당근(Greenhouse `?content=true`) httpx fetch + HTML→텍스트 정규화(BeautifulSoup).
- 제목 키워드 필터(`TARGET_KEYWORDS`, `_norm` 대소문자/공백/하이픈 무시) + 회사 round-robin 균형.
- `job_postings` upsert(Collector 소유) + 전일 대비 신규/유지/마감임박/마감 diff + CoverageState(수집/실패 노출).
- `jobs_manual` 동등 폴백(스크래핑 실패 시 수동 JD → 동일 raw 형식).

## 3. 구현 항목
- `crawler/src/crawler/fetch_jobs.py` — `_norm`, `keyword_match`, 토스/당근 fetch, `_clean_html`, raw 공고 dict(job_id="{source}-{gid}", company, title, url, raw_text).
- `crawler/src/crawler/store.py`(또는 동등) — `job_postings` upsert + diff 계산 + CoverageState 갱신. 실패율/캡차율 로깅(조용한 실패 금지).
- `crawler/src/crawler/manual.py` — `parse_manual`(=== JOB === 블록) 폴백.

## 4. 제외 항목
- 도메인 인지 선택(T-013) · LLM 구조화(F-001 jd_extract) · Playwright 승격(A-1, 필요 시 후속) · 마감일 파싱 고도화(엣지, 후속).

## 4-1. 변경 예정 파일/경로
- `crawler/src/crawler/fetch_jobs.py`, `crawler/src/crawler/store.py`, `crawler/src/crawler/manual.py`, `crawler/tests/test_fetch.py`

## 5. 완료 조건
두 소스의 목록·상세를 파싱해 raw 공고로 정규화하고, 키워드 필터가 동작하며, job_postings upsert + diff가 산출된다.

## 6. Acceptance Criteria
- AC-1 [Given] 토스·당근 API 응답 샘플(fixture) [When] fetch 파서 [Then] 각 공고가 (job_id, company, title, url, raw_text) 필드로 정규화되고, HTML은 텍스트로 변환된다.
- AC-2 [Given] 엔지니어링 토큰 없는 제목("콘텐츠 마케터")과 있는 제목("Frontend Engineer") [When] `keyword_match` [Then] 전자는 제외·후자는 포함된다(대소문자/공백/하이픈 무시).
- AC-3 [Given] 전일 공고 집합과 금일 fetch 결과 [When] upsert + diff [Then] 신규/마감 항목이 산출되고 수집 실패가 CoverageState에 노출된다(조용한 무시 없음).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_fetch.py::test_AC_1_parse_toss_daangn_fixtures
- AC-2 → pytest::crawler/tests/test_fetch.py::test_AC_2_keyword_filter
- AC-3 → pytest::crawler/tests/test_fetch.py::test_AC_3_upsert_diff_and_coverage

## 6-2. TDD opt-out
<!-- TDD 적용 — HTTP는 fixture/fake로 주입(실 네트워크 금지). -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-002-collector](../features/F-002-collector.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3 Collector, §3-2 job_postings 소유권, §6, §7-3 스케줄러)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §9-1·§9-2](../../20-system/SCORING_PIPELINE_SPEC.md)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-CRAWL httpx)

## 8. 메모
- 외부 API(토스/당근) 연동 — 구현 전 엔드포인트 응답 형태 재확인(researcher/research-pack, ADR-040). ToS 준수 운영 원칙.
- `User-Agent`는 서비스 식별자로 갱신.
- repair-workitem 2026-06-05 P0 type-import: Adopt-modified — store.collect sources를 dict[str,Callable[[],list[RawJob]]]로 정확화(Any 불요+Callable 사용+mypy 해소)
- repair-workitem 2026-06-05 P0 ruff-I001: Adopt — test_fetch.py import 정렬(ruff --fix)

## 9. 의존성
- depends_on: [T-002]
- read_set: ["ai/core/src/core/models.py", "docs/20-system/SCORING_PIPELINE_SPEC.md"]
- write_set: ["crawler/src/crawler/fetch_jobs.py", "crawler/src/crawler/store.py", "crawler/src/crawler/manual.py", "crawler/tests/test_fetch.py"]
- verifier: "uv run pytest crawler/tests/test_fetch.py"
