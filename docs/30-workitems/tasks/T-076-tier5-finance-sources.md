# T-076-tier5-finance-sources

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
Target universe **Tier5(금융권 + IT 자회사, 20사)** 수집을 구현한다. 표준 글로벌 ATS는 0이고, 한국 채용대행 SaaS(recruiter.co.kr·incruit·careerlink·applyin·그리팅) 위탁 + 일부 custom(인터넷은행·증권)이며 **대부분 로그인 게이트**다. **공개 목록만 수집**, 로그인 목록은 status=`login-required`로 투명 노출(로그인 크롤링 영구 비범위).

## 2. 작업 범위 (대상 20사 — T-070 view-vs-apply 검증 후 확정)
- **recruiter.co.kr 위탁**(T-075 어댑터 재사용): 신한은행·신한DS·하나은행·하나금융티아이·현대카드.
- **incruit 위탁**: KB국민은행·IBK기업은행·신한카드.
- **careerlink 위탁**: 우리은행·우리에프아이에스.
- **그리팅**(T-071 재사용): KB데이타시스템.
- **applyin / custom**: 코스콤(applyin)·NH농협(with.nonghyup 범농협 통합).
- **custom 인터넷은행·증권**: 카카오뱅크(recruit.kakaobank.com)·케이뱅크·토스뱅크·미래에셋증권·한국투자증권·삼성화재(삼성 통합).
- **로그인 처리 (기본 가정 + 확정)**: 금융권도 *목록 공개 + 지원 시 로그인*이 일반 → **대부분 list-public 예상**. view 로그인은 *behavioral*이라 **T-070이 각 URL 실제 fetch로 확정**(위탁SaaS는 플랫폼 단위 판정 가능 — 같은 SaaS 동일 동작) → list-public만 수집, list-login은 status=login-required.

## 3. 구현 항목
1. T-070 `registry_seed`의 Tier5 20사 항목(read-only — method·view_login 포함, T-070 단일 소유) 기반 어댑터 매핑·수집. → 매핑·수집 assert (AC-1)
2. 위탁 SaaS 어댑터: `recruiter_co_kr`(T-075 재사용) + `incruit`·`careerlink`·`applyin` 신설(`BaseCustomAdapter` 기반, 공개 목록 한정). → fixture 테스트 (AC-1, AC-2)
3. custom 인터넷은행·증권 어댑터(`adapters/finance_*.py`) — list-public만. → 테스트 (AC-1)
4. list-login 소스 → status=login-required 기록(미크롤). → 테스트 (AC-3)
5. fixture + `crawler/tests/test_tier5_finance.py`. AC-1~AC-3.

## 4. 제외 항목
- **로그인 뒤 크롤링 — 영구 비범위**(공개 목록만).
- Tier1/2/3/4 — 각 task. (recruiter.co.kr 어댑터는 T-075 신설분 재사용.)

## 4-1. 변경 예정 파일/경로
- (`registry_seed.py`는 T-070 소유 read-only [view_login 포함] — 본 task 미변경)
- `crawler/src/crawler/adapters/incruit.py` · `careerlink.py` · `applyin.py` · `finance_*.py` (신설; recruiter_co_kr은 T-075 재사용)
- `crawler/tests/test_tier5_finance.py`

## 5. 완료 조건
Tier5 20사가 레지스트리에 등록되고, **목록 공개 소스**(위탁SaaS·custom)는 공고가 `job_postings`에 수집되며, 로그인 목록 소스는 status=login-required로 투명 노출된다.

## 6. Acceptance Criteria
- AC-1 [Given] Tier5 20사 registry_seed(view_login 포함) [When] 수집 [Then] list-public 위탁SaaS·custom 소스 공고가 `job_postings`에 upsert되고 미수집은 status로 기록된다.
- AC-2 [Given] 위탁SaaS(incruit/careerlink/applyin) 공개 목록 [When] 각 SaaS 어댑터 [Then] 같은 SaaS를 쓰는 여러 회사가 1어댑터로 수집된다(곱셈 — 신규 어댑터 최소).
- AC-3 [Given] list-login 소스 [When] 처리 [Then] 크롤링 시도 없이 status=login-required로 기록되고 패널에 투명 노출된다(거짓 완전성 0).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_tier5_finance.py::test_AC_1_public_finance_collected
- AC-2 → pytest::crawler/tests/test_tier5_finance.py::test_AC_2_saas_adapter_multiplexes_companies
- AC-3 → pytest::crawler/tests/test_tier5_finance.py::test_AC_3_login_required_cataloged_not_crawled

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-020-source-coverage-expansion](../features/F-020-source-coverage-expansion.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §3 Collector)

## 8. 메모
- 금융권은 표준 글로벌 ATS 0 — 한국 위탁SaaS(recruiter.co.kr/incruit/careerlink/applyin)가 주류. SaaS별 어댑터 1개로 여러 회사 곱셈 수집(공개 목록 한정).
- 대부분 *지원 시 로그인*이나 *목록 view*는 공개 가능 → T-070 회사별 확정. 목록 로그인이면 catalog만.
- 카카오뱅크는 Tier5(금융), 카카오 본사·페이 등은 Tier1.

## 9. 의존성
- depends_on: [T-070, T-072, T-075]
- read_set: ["crawler/src/crawler/adapters/**", "crawler/src/crawler/sources/registry_seed.py"]
- write_set: ["crawler/src/crawler/adapters/incruit.py", "crawler/src/crawler/adapters/careerlink.py", "crawler/src/crawler/adapters/applyin.py", "crawler/src/crawler/adapters/finance_*.py", "crawler/tests/test_tier5_finance.py"]  # registry_seed는 T-070 단일 writer (read-only)
- assumptions: ["T-070(registry_seed + view_login)·T-072(BaseCustomAdapter)·T-075(recruiter_co_kr 어댑터) 완료"]
- verifier: "uv run pytest crawler/tests/test_tier5_finance.py"
