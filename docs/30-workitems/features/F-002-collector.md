# F-002-collector: 토스·당근 수집 + 도메인 인지 선택

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
토스·당근 공식 채용 페이지(둘 다 Greenhouse 기반 JSON API)에서 SW 엔지니어링 공고를 주기 수집하고, 비싼 LLM 단계 전에 *값싼 휴리스틱*으로 사용자 도메인 기준 균형 후보를 선별한다. 신규/마감 diff를 감지해 단일 피드의 "누락 0" 신뢰 계약(G1)을 받친다. = DISCOVERY F1·F3. 알고리즘 SSOT: [SCORING_PIPELINE_SPEC §9](../../20-system/SCORING_PIPELINE_SPEC.md).

## 2. 사용자 가치 (User Story) — Type=feature 일 때
- As "유진"(신입/졸업예정 개발자 구직자, Charter §2.1), I want to 토스·당근의 신규·마감 공고가 매일 자동 수집되어 단일 피드에 누락 없이 모이길 원한다, so that 채널을 직접 순회하다 기회를 놓치지 않는다. (pain #1 / G1)
- As "유진", I want to 내 주력 도메인(프론트/풀스택) 공고가 우선 선별되되 대조군도 포함되길 원한다, so that 관련성 높은 공고를 먼저 보면서도 과도한 협소화를 피한다. (Charter §8 흐름 1)

## 3. 핵심 시나리오 (Feature-level)

### Happy path
1. 스케줄 트리거(GitHub Actions 매일 오전 cron).
2. 토스 목록 API + 당근 Greenhouse API에서 공고 목록 fetch.
3. 제목 키워드 필터(엔지니어링 토큰)로 비-엔지니어링 직군 차단.
4. 제목 휴리스틱으로 role_family 임시 분류 → 사용자 도메인 tier(primary/adjacent/weak/mismatch)로 풀 구성(`--pool-size` 기본 50).
5. `select_balanced`로 균형 선택(limit=10 → primary 5 + adjacent 3 + contrast 2). 상세 fetch는 선택분만.
6. `job_postings` upsert + 전일 대비 신규/마감 diff 계산 + CoverageState 갱신.

### Alternate path
1. 주력 도메인 공고가 풀에 없으면 리포트(`fetch_selection_report`)에 명시.
2. 스크래핑 실패 시 수동 JD 붙여넣기(jobs_manual 동등) 폴백으로 동일 파이프라인 가능.

### Fail path
1. 🔴 수집 실패를 *조용히* 넘김 → "전부 수집" 거짓 인상(Fail #3). 반드시 CoverageState에 노출.
2. 🔴 마감일 파싱 오류로 마감 임박 누락(Fail #4). 마감 필드 파싱 검증 필요.
3. 🟡 동일 공고 중복 노출 — dedup 실패(가독성 저하, 기회 손실 X).

## 4. 범위
- 토스(`api-public.toss.im/.../career/jobs` + 상세) · 당근(Greenhouse Board API `?content=true`) JSON fetch + HTML→텍스트 정규화.
- 제목 키워드 필터(`TARGET_KEYWORDS`, 엔지니어링 토큰 강제) + 회사 균형.
- 제목 기반 role_family 휴리스틱(`ROLE_PATTERNS`) + 도메인 tier 매핑 + `select_balanced`(50%/30%/20%).
- `job_postings` upsert(Collector 소유 테이블, §3-2) + 신규/유지/마감임박/마감 diff.
- 선택 내역 리포트(`fetch_selection_report` 동등 — tier/role_family 분포).

## 5. 비범위
- 다채널 풀커버리지(7개+) — Charter §5 비목표.
- 동적렌더링/anti-bot 우회 고도화 — httpx 정적 fetch 우선, Playwright 승격은 필요 시(A-1, 구현 시 확정).
- LLM 기반 role_family 확정 — Scorer(F-001)의 `jd_extract`가 최종 권위. 본 feature는 *선택용 임시* 분류만.
- 커버리지 투명성 패널 UI(F2) — Feed feature.

## 6. 요구사항
- fetch 엔드포인트·헤더·timeout(15s)·파싱은 SPEC §9-1을 그대로 따른다. `User-Agent`는 서비스 식별자로(ToS 준수 운영 원칙, ARCH §8).
- 키워드 필터·role_family 휴리스틱·`select_balanced` 정원은 SPEC §9-2·9-3·9-4를 그대로 이식.
- `job_postings`의 writer는 Collector 단일(§3-2 소유권). 다른 모듈은 읽기만.
- 수집 실패율·캡차율 로깅 + CoverageState 노출(Fail #3 차단, ARCH §7-3).
- `USER_PRIMARY/SECONDARY_DOMAINS`는 MVP 단일 사용자라 설정값으로 시작(후속: 후보별).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** 토스·당근 목록 API 응답을 파싱해 (job_id, company, title, url, raw_text)를 가진 raw 공고로 정규화한다.
- **FAC-2:** 제목 키워드 필터가 엔지니어링 토큰 없는 직군(마케팅/디자인 등)을 제외한다(대소문자/공백/하이픈 무시).
- **FAC-3:** limit=10·pool=50에서 `select_balanced`가 primary 5 + adjacent 3 + contrast 2(정원 미달 시 priority backfill)로 선택하고 선택 내역을 리포트로 남긴다.
- **FAC-4:** 수집 결과를 `job_postings`에 upsert하고 전일 대비 신규/마감 diff를 산출한다.
- **FAC-5:** 수집 실패가 조용히 무시되지 않고 CoverageState에 노출된다(Fail #3 차단).

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-012:AC-1 (목록·상세 파싱)
- FAC-2 → T-012:AC-2 (키워드 필터)
- FAC-3 → T-013:AC-1, T-013:AC-2 (role_family 휴리스틱 + select_balanced 정원 + 리포트)
- FAC-4 → T-012:AC-3 (job_postings upsert + diff)
- FAC-5 → T-012:AC-3 (CoverageState 실패 노출) ; (UI 노출은 Feed F2)

## 8. Non-functional Requirements
- **완결성 우선:** 수집은 주기 배치라 실시간성보다 누락 0이 우선(ARCH §8 성능).
- **운영성:** fetch 실패율·캡차율 로깅이 운영 1순위(A-1). 조용한 실패 금지.
- **보안/준법:** 외부 사이트 ToS/robots 준수 — 운영 상시 원칙.

## 8-1. UX 흐름 품질
(해당 없음 — 본 feature는 수집·선택 *백엔드*. UI 노출은 Feed/커버리지 패널 feature.)

## 9. 엣지 케이스
- 토스 상세 fetch가 `success.content`/`payload.content` 둘 다 없을 때 — 에러 문자열 반환 + 해당 공고 스킵(비치명).
- 당근은 목록에 content 포함(2차 fetch 불필요) — 소스별 분기 보존.
- 주력 도메인 공고 0건인 날 — 리포트에 명시(거짓 완전성 차단).
- 마감일 필드 부재/포맷 변형 — 파싱 실패를 diff에서 조용히 누락하지 않음.

## 10. 의존성
- **선행:** T-001(ai/ + crawler scaffold), T-002(데이터 계약 — JobPosting 등).
- **입력:** 외부 토스·당근 사이트(A-1 검증됨 2026-06-04).
- **출력 소비:** Scorer(F-001)가 `job_postings`를 읽어 스코어링.

## 11. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§4 G1·G3, §3 pain #1)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3 Collector, §3-2 job_postings 소유권, §6 토스·당근, §7-3 스케줄러)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §9](../../20-system/SCORING_PIPELINE_SPEC.md)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-CRAWL httpx)

## 12. 열린 질문
- 정적 httpx로 충분한가, Playwright headless 승격이 필요한가? (A-1 — 구현 시 확정, ADR-101 D-CRAWL)
- 마감일 파싱 신뢰성 — 소스별 필드 매핑은? (Fail #4 직결)
- 중복 공고(동일 공고 다중 채널) dedup 책임 경계 — Collector에서 어디까지?
