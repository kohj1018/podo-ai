# F-020-source-coverage-expansion: 채용공고 커버리지 확대 (공식 채용 페이지·ATS 어댑터)

## 0. Status
draft

> **잠정 (M5).** 커버리지 확대는 Charter §5 "다채널 풀커버리지 비목표"의 *숫자 상한*을 건드린다 → **M5 task 생성 *전* Charter §5 scope-note 반영이 필수 선행(blocking gate)**: 상위(Charter) 승인 없이 하위 task 착수 금지(AGENTS.md "상위 문서 없이 하위 먼저 X"). scope-note 내용 = 공식 페이지 한정·티어드·소스별 게이트. **별도 ADR은 불필요**(검증된 A-1 재사용·가역적·"공식만"은 기존 ToS 연장이라 비가역 트레이드오프 없음 — 사용자 판단 2026-06-07). *Charter 편집 자체는 repair-plan 범위 밖 → 메인세션 별도 처리.*

## 0-1. Type
feature

## 1. 요약
수집 커버리지를 토스·당근 2곳 → **5-tier target universe(~85개사, 웹검색 실측 픽스 — 회사 목록은 per-tier 구현 task에 명시: Tier1=T-072·Tier2=T-073·Tier3=T-074·Tier4=T-075·Tier5=T-076)**: Tier1 네카라쿠배+계열사 / Tier2 외국계 한국 / Tier3 Series C+·유니콘 스타트업 / Tier4 국내 대기업+IT계열사 / Tier5 금융권+IT자회사로 확대한다. **애그리게이터(잡코리아·직행·원티드 등)는 영구 비범위.** 회사별 bespoke를 줄이도록 **ATS 어댑터 전략**(실측 우선순위 **그리팅 greetinghr·Workday·Greenhouse·Lever·Ashby**로 곱셈 확장) + 자체사이트 `BaseCustomAdapter`(Tier1 우선). 각 신규 소스는 **A-1형 게이트** 통과 시 "수집 중" 승격. **⚠️ Tier4/5 다수 login-gated → 목록 공개분만 수집, 로그인 목록은 투명 status(`login-required`).**

범위 갱신: Charter §5 scope-note(M5 진입 시, 별도 ADR 불필요). 원 제약: Charter §5 "다채널 풀커버리지" 비목표(숫자 상한).

## 2. 사용자 가치 (User Story)
- As a **유진(신입/졸업예정 개발자 구직자)**, I want postings from many companies' official career pages in one feed, so that I miss fewer real opportunities while trusting that coverage is explicit(not aggregator noise).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 크롤러가 ATS 어댑터(예: Greenhouse)로 등록된 회사들의 공고를 수집 → `job_postings` upsert.
2. 자체 페이지 회사(네카라쿠배 등)는 회사별 어댑터로 수집.
3. 커버리지 패널에 수집 성공 소스 목록 + 마지막 성공 시각 노출(미수집은 명시).
### Alternate path
1. 일부 소스 일시 실패 → 그 소스만 "수집 실패/지연" 표기, 나머지는 정상(부분 커버리지 정직 고지).
### Fail path
1. 🔴 소스 구조 변경/차단 → 게이트가 감지 → 해당 소스 커버리지 강등 + 로그(조용한 실패·거짓 완전성 금지, Fail #3).
2. 🔴 애그리게이터를 실수로 추가 → 정책 위반(금지) — 코드/리뷰에서 차단.

## 4. 범위
- **소스 discovery 선행**(T-070): target universe 전 회사 → 공식 URL·method(ATS 종류/custom)·한국 location 필터·차단여부 조사 → 레지스트리 seed.
- 어댑터 **2 family**: (A) 표준 ATS(공통 인터페이스 + **실측 우선순위 그리팅·Workday > Lever·Ashby**, Greenhouse=T-062 — ATS별 곱셈 확장) + (B) 자체사이트 bespoke(`BaseCustomAdapter` 공통 골격 + 회사별, Tier1 우선).
- **location 필터를 어댑터 1급 파라미터**(`fetch_jobs(location="KR")`) — 외국계 한국 채용만.
- 소스 레지스트리(회사↔어댑터↔method↔status) + 티어드(네카라쿠배 최우선 → 외국계 → 스타트업).
- 소스별 A-1형 게이트 + 커버리지 패널 연동 — **상태 taxonomy**(active/blocked/captcha/login-required/no-korea-jobs/unsupported) 투명 노출.
- 정적 httpx 우선 → 필요 시 Playwright headless(ARCH §6).
- crawler 구조 국소 리팩토링(`crawler/sources/*` 어댑터 분리 — ADR-101#amend).
- ToS/robots 준수 상시(공식 페이지만, 애그리게이터 영구 제외).

## 5. 비범위
- 애그리게이터(잡코리아·직행·원티드 등) — **영구 비범위**.
- 비개발 직군 공고 — Charter §5 비목표.
- 실 배포 cron 실가동 — M6(M5는 로컬/수동 트리거로 수집 검증).
- 알고리즘 변경 — F-021~023.

## 6. 요구사항
- **공식 채용 페이지에서만** 수집(정책). 소스별 게이트 통과해야 커버리지 승격.
- ATS 어댑터 우선(공수 절감) + 회사별 어댑터 보완.
- 부분 커버리지 정직 고지(커버리지 패널 — Fail #3 차단).
- 결정성: 수집 fixture/오프라인 모드로 무키 E2E 보존(M2 패턴).

## 7. Feature-level Acceptance Criteria
> **Target universe ≠ Graduation line** (사용자 결정 2026-06-08): "최대한 많이"는 *점진 확대 대상*이지 졸업 조건이 아니다. 졸업은 아래 수렴 가능한 선.
- **FAC-1 (target universe 기록):** T-070 discovery가 target universe **Tier1~5 전 회사**(네카라쿠배+계열사 / 외국계 / 스타트업 / 대기업+IT계열사 / 금융권+IT자회사)의 (공식 URL·method·**view-vs-apply 로그인**·location·status)를 소스 레지스트리에 기록한다(미구현·로그인 소스도 status로 남김).
- **FAC-2 (graduation 수집):** 표준 ATS(그리팅·Workday·Greenhouse·Lever·Ashby) ats-ready + **Tier2 외국계(location=KR)·Tier3 스타트업·Tier1 본사 커스텀·Tier4/5 목록 공개분**을 등록 가능한 만큼 수집 → 공고가 `job_postings`에 수집되고 수집→채점→피드 렌더 E2E가 무키로 완주한다.
- **FAC-3 (A-1 게이트):** 신규 소스는 A-1형 게이트(차단/구조변경/캡차 미관측)를 통과해야 "수집 중"으로 승격된다.
- **FAC-4 (투명 상태):** 부분 실패·미지원 소스도 상태(`blocked`/`captcha`/`login-required`/`no-korea-jobs`/`unsupported`)로 커버리지 패널에 투명 노출되고 "전부 수집" 거짓 인상이 없다(Fail #3).
- **FAC-5 (외국계 location):** 외국계 소스는 location=Korea/Seoul 필터로 한국 채용만 수집한다(discovery 실측 기반; 불가 시 no-korea-jobs).
- **FAC-6 (애그리게이터 가드):** 애그리게이터 소스는 추가/수집되지 않는다(정책 가드).

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-070:AC-1, T-070:AC-2
- FAC-2 → T-072:AC-1, T-073:AC-1, T-074:AC-1, T-075:AC-1, T-076:AC-1, T-071:AC-1, T-063:AC-1
- FAC-3 → T-062:AC-2
- FAC-4 → T-063:AC-2, T-063:AC-3, T-075:AC-3, T-076:AC-3
- FAC-5 → T-070:AC-3, T-071:AC-2, T-073:AC-2
- FAC-6 → T-062:AC-3

## 8. Non-functional Requirements
- 운영성: 소스별 fetch 실패율·캡차율 로깅(M6 알람 토대).
- 유지보수: ATS 어댑터로 회사 추가 비용 최소화. 어댑터별 구조변경 회귀 테스트.
- 법무: ToS/robots 준수 상시(공식 페이지 한정).

## 8-1. UX 흐름 품질
(해당 없음 — 수집 레이어. 커버리지 표시는 F-018 CoveragePanel.)

## 9. 엣지 케이스
- 같은 회사가 자체 페이지 + ATS 양쪽 게시 → 중복제거(url 기준 + 회사·직무 휴리스틱).
- 외국계 영어 JD → 수집은 가능, fit 교차는 F-023에서 검증.
- ATS 페이지네이션/동적 렌더 → 어댑터별 처리(headless 승격).
- robots 비허용 소스 → 추가하지 않음.

## 10. 의존성
- 범위 갱신: Charter §5 scope-note(M5 진입 시, 별도 ADR 불필요).
- 연계: F-021(많아진 JD를 임베딩·prefilter로 받아내야 비용 폭증 방지) — 함께 가야 의미.
- F-018 CoveragePanel(소스 상태 표시).

## 11. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§5 다채널 비목표 — 반전, G3 커버리지)
- Discovery: [DISCOVERY](../../10-charter/DISCOVERY.md) (§12 A-1·A-11, F1·F2)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§6 외부 연동, §3 Collector)
- 범위 갱신: Charter §5 scope-note(M5 진입 시, 별도 ADR 불필요) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md)(크롤링 방식)

## 12. 열린 질문 — 결정 확정 (2026-06-08, 사용자 승인)
- ✅ Target universe = Tier1 네카라쿠배+계열사(최우선) / Tier2 외국계 한국 / Tier3 Series C+·유니콘. 자체 공식사이트 운영처 한정. **graduation은 별도 수렴선**(§7 FAC-1/2).
- ✅ ATS 우선순위 = **그리팅·Workday > Lever·Ashby**(Greenhouse=T-062 기반) — T-070 실측 반영. 자체사이트는 Tier1부터 우선.
- ✅ 어댑터 비중: ATS family는 곱셈 확장(저비용), custom family는 Tier1 우선 bespoke(`BaseCustomAdapter` 공통 골격). 구체 분포는 T-070 discovery 산출.
- ✅ 외국계 location=Korea/Seoul 필터 — discovery에서 실측(불가 시 no-korea-jobs).
- ⏳ 중복제거 강화(회사·직무 정규화): 기존 url 기준 + §9 휴리스틱 유지, 확대 후 필요 시 후속.
