# T-075-tier4-conglomerate-sources

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
Target universe **Tier4(국내 대기업 + IT 핵심 계열사, 21사)** 수집을 구현한다. 대부분 custom 자체/그룹 통합포털 + 일부 한국 채용대행 SaaS(recruiter.co.kr)이며, **상당수가 로그인 게이트**다. **공개 목록(view)만 수집**하고 — 목록 자체가 로그인이면 status=`login-required`로 패널에 투명 노출(공개수집 정책·ToS — 로그인 크롤링 영구 비범위).

## 2. 작업 범위 (대상 21사 — T-070 view-vs-apply 검증 후 확정)
- **그룹 통합포털 custom**: 삼성(samsungcareers.com — 삼성전자·SDS·전기)·LG(careers.lg.com — 전자·CNS·U+)·SK(skcareers.com — C&C/AX, + 별도 SKT·하이닉스)·두산(career.doosan.com)·한화(hanwhain.com — 한화시스템).
- **개별 custom**: 현대자동차(talent.hyundai.com)·현대오토에버·현대모비스·기아·KT(recruit.kt.com)·포스코DX·롯데이노베이트·CJ올리브네트웍스.
- **위탁 SaaS(recruiter.co.kr)**: 신세계I&C·kt ds.
- **로그인 처리 (기본 가정 + 확정)**: 대기업 채용은 *목록 공개 + 지원 시 로그인*이 일반 패턴 → **대부분 list-public 예상**. 단 view 로그인 여부는 *behavioral*(web search로 안 나옴)이라 **T-070이 각 careers_url을 httpx로 실제 fetch해 per-source 확정**(목록 렌더 vs 로그인 redirect) → list-public만 수집, list-login은 status=login-required(미수집·투명). 그룹 통합포털은 계열사 필터.

## 3. 구현 항목
1. T-070 `registry_seed`의 Tier4 21사 항목(read-only — method·view_login 포함, T-070 단일 소유) 기반 어댑터 매핑·수집. → 매핑·수집 assert (AC-1)
2. 그룹 통합포털·개별 custom 어댑터(`adapters/conglomerate_*.py`, `BaseCustomAdapter`) — **list-public 소스만**. 그룹포털은 계열사 필터. → fixture 테스트 (AC-1)
3. 위탁 SaaS 어댑터 `adapters/recruiter_co_kr.py`(공유 — T-076 재사용) — 공개 목록 한정. → 테스트 (AC-2)
4. list-login 소스 → 수집 시도 없이 status=login-required 기록. → 테스트 (AC-3)
5. fixture + `crawler/tests/test_tier4_conglomerate.py`. AC-1~AC-3.

## 4. 제외 항목
- **로그인 뒤 크롤링 — 영구 비범위**(공개 목록만). list-login 소스는 catalog만.
- ATS 어댑터(없음 — Tier4는 ATS 미사용).
- Tier1/2/3/5 — 각 task.

## 4-1. 변경 예정 파일/경로
- (`registry_seed.py`는 T-070 소유 read-only [view_login 포함] — 본 task 미변경)
- `crawler/src/crawler/adapters/conglomerate_*.py` · `adapters/recruiter_co_kr.py` (신설, recruiter_co_kr은 T-076 공유)
- `crawler/tests/test_tier4_conglomerate.py`

## 5. 완료 조건
Tier4 21사가 레지스트리에 등록되고, **목록 공개 소스**는 공고가 `job_postings`에 수집되며, 로그인 목록 소스는 status=login-required로 투명 노출된다(미수집을 정직하게).

## 6. Acceptance Criteria
- AC-1 [Given] Tier4 21사 registry_seed(view_login 포함) [When] 수집 [Then] list-public custom/SaaS 소스 공고가 `job_postings`에 upsert되고, 그룹 통합포털은 계열사 단위로 구분된다.
- AC-2 [Given] recruiter.co.kr 위탁 소스(공개 목록) [When] `recruiter_co_kr` 어댑터 [Then] 공고가 수집되고 이 어댑터가 T-076 금융권에서도 재사용 가능하다.
- AC-3 [Given] list-login 소스(목록 로그인) [When] 처리 [Then] 크롤링 시도 없이 status=login-required로 기록되고 커버리지 패널에 투명 노출된다(거짓 완전성 0).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_tier4_conglomerate.py::test_AC_1_public_conglomerate_collected
- AC-2 → pytest::crawler/tests/test_tier4_conglomerate.py::test_AC_2_recruiter_co_kr_adapter_shared
- AC-3 → pytest::crawler/tests/test_tier4_conglomerate.py::test_AC_3_login_required_cataloged_not_crawled

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-020-source-coverage-expansion](../features/F-020-source-coverage-expansion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §3 Collector)

## 8. 메모
- 핵심 제약: 대기업 채용은 *지원 시 로그인*이 흔하나 *목록 view*는 공개일 수 있음 → T-070이 회사별 확정. 목록 로그인이면 수집 포기(catalog만).
- 그룹 통합포털(삼성/LG/SK/두산/한화)은 1포털에 다계열사 → 1어댑터 + 계열사 필터로 곱셈.
- recruiter.co.kr 어댑터는 Tier5(금융)와 공유 — 본 task에서 신설, T-076 재사용.

## 9. 의존성
- depends_on: [T-070, T-072]
- read_set: ["crawler/src/crawler/adapters/**", "crawler/src/crawler/sources/registry_seed.py"]
- write_set: ["crawler/src/crawler/adapters/conglomerate_*.py", "crawler/src/crawler/adapters/recruiter_co_kr.py", "crawler/tests/test_tier4_conglomerate.py"]  # registry_seed는 T-070 단일 writer (read-only)
- assumptions: ["T-070(registry_seed + view_login 판정)·T-072(BaseCustomAdapter) 완료"]
- verifier: "uv run pytest crawler/tests/test_tier4_conglomerate.py"
