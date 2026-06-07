# T-073-tier2-foreign-company-sources

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
Target universe **Tier2(외국계 한국 채용, 19사)** 수집을 구현한다. 표준 ATS(Workday·Greenhouse) 또는 글로벌 자체사이트(custom)이며 **location=KR 필터로 한국 공고만** 수집한다. 공유 ATS 어댑터(T-071 Workday, T-062 Greenhouse)는 레지스트리 등록으로, 글로벌 custom 사이트는 `BaseCustomAdapter`(T-072) 재사용 어댑터로 처리.

## 2. 작업 범위 (대상 19사 — T-070 검증 후 확정)
- **workday**(T-071): NVIDIA(nvidia.wd5)·Intel(intel.wd1)·Salesforce(salesforce.wd1)·Snowflake.
- **greenhouse**(T-062): Moloco(job-boards.greenhouse.io/moloco)·Sendbird·Databricks.
- **custom 글로벌**(BaseCustomAdapter + location=KR): Google(careers.google.com)·Microsoft·AWS/Amazon(amazon.jobs)·Meta(metacareers)·Apple(jobs.apple.com)·Oracle·Cisco·IBM(Avature)·Uber·Atlassian·LinkedIn·SAP(jobs.sap.com).
- ATS 소스 → 공유 어댑터로 레지스트리 등록(어댑터 신규 X). 글로벌 custom → 사이트별 목록 엔드포인트·파싱 + **location=KR 필터**(Seoul/Korea facet·쿼리). 한국 채용 0 → status=`no-korea-jobs`. 오프라인 fixture(무키).

## 3. 구현 항목
1. T-070 `registry_seed`의 Tier2 19사 항목(read-only — seed는 T-070 단일 소유) 기반 method별 어댑터 매핑·수집 검증. → 매핑·수집 assert (AC-1)
2. 글로벌 custom 어댑터(`adapters/foreign_*.py`) — `BaseCustomAdapter` + location=KR. → fixture 테스트 (AC-1, AC-2)
3. workday/greenhouse Tier2 소스는 공유 어댑터 + `location="KR"` 인자로 수집. → 테스트 (AC-2)
4. fixture + `crawler/tests/test_tier2_foreign.py`. AC-1~AC-3.

## 4. 제외 항목
- ATS 어댑터 자체 구현 — T-071/T-062.
- **로그인 뒤 크롤링 — 영구 비범위**(공개 목록만).
- Tier3/4/5 — T-074/075/076.

## 4-1. 변경 예정 파일/경로
- `crawler/src/crawler/sources/registry_seed.py` (Tier2 등록)
- `crawler/src/crawler/adapters/foreign_*.py` (글로벌 custom 어댑터)
- `crawler/tests/test_tier2_foreign.py`

## 5. 완료 조건
Tier2 19사가 레지스트리에 등록되고, ATS + 글로벌 custom 소스에서 **location=KR 필터된 한국 공고**가 `job_postings`에 수집된다. 한국 채용 없는 소스는 no-korea-jobs status.

## 6. Acceptance Criteria
- AC-1 [Given] Tier2 19사 registry_seed [When] 수집 [Then] ATS(workday/greenhouse) + custom 글로벌 어댑터가 각 소스 공고를 `job_postings`에 upsert하고 미수집은 status로 기록된다.
- AC-2 [Given] location 혼합 fixture(서울/해외) [When] `fetch_jobs(location="KR")` [Then] 한국(Korea/Seoul) 공고만 수집된다.
- AC-3 [Given] 한국 채용 0 소스 [When] 수집 [Then] status=no-korea-jobs로 기록되고 조용히 누락되지 않는다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_tier2_foreign.py::test_AC_1_tier2_sources_collected
- AC-2 → pytest::crawler/tests/test_tier2_foreign.py::test_AC_2_korea_location_filter
- AC-3 → pytest::crawler/tests/test_tier2_foreign.py::test_AC_3_no_korea_jobs_status

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-020-source-coverage-expansion](../features/F-020-source-coverage-expansion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §3 Collector)

## 8. 메모
- T-070 discovery가 careers_url·method·location을 per-source 확정 → 본 task는 그에 따라 등록·구현. unknown(Atlassian/LinkedIn ATS)은 discovery 확정 후.
- 글로벌 custom 사이트는 구조 상이 → 공통 `BaseCustomAdapter`, 차이만 override.

## 9. 의존성
- depends_on: [T-070, T-071, T-072]
- read_set: ["crawler/src/crawler/adapters/**", "crawler/src/crawler/sources/registry_seed.py"]
- write_set: ["crawler/src/crawler/adapters/foreign_*.py", "crawler/tests/test_tier2_foreign.py"]  # registry_seed는 T-070 단일 writer (read-only)
- assumptions: ["T-070(registry_seed)·T-071(workday/greenhouse)·T-072(BaseCustomAdapter) 완료"]
- verifier: "uv run pytest crawler/tests/test_tier2_foreign.py"
