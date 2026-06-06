# F-007-worker-persistence: worker 영속 어댑터 + 실행 진입점 (결정론 DB 경로)

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 요약
검증된 `run_scoring`(현재 in-memory dict-in/dict-out)을 실제 DB I/O에 연결한다 — DB에서 `job_postings`와 seed 이력서를 읽고, `run_scoring` 산출 JSONB를 `ranking_runs.result`에 영속하고 feed projection `recommendations`(scalar 정렬/커서 컬럼)를 함께 쓰며, `python -m worker` 실행 진입점을 만든다. **GS-1(결정론)은 DB 영속 경로를 통과해도 보존**된다(기존 `CacheAdapter` seam + `make_key` 불변 위에 Postgres 어댑터를 얹음).

## 2. 사용자 가치 (User Story) — Type=technical-enabler 이므로 기술적 근거
- **무엇/왜:** T-004(cache)·T-011(run_scoring)은 *dict/JSONB 계약*까지만 구현 — 실 서비스는 DB read/write가 필요. 이를 닫아 "수집 공고 → 점수·근거"가 실제로 저장된다. DISCOVERY F4·F5·F6·F7을 서비스.
- **서비스하는 결정/가정:** ADR-100 D3(결정론 캐시) · ARCH §3-1 결정론 경계 · §3-2 규칙3(좁은 JSONB) · 가정 A-12(캐시 결정성).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. `python -m worker`가 config seed 이력서 + DB `job_postings`를 로드.
2. `run_scoring(resume, jobs, ranking_mode="domain_fit_bt")` 실행.
3. 산출 JSONB(final_ranking·matching_tables·pairwise)를 `ranking_runs.result`에 upsert(버전 필드 동반).
### Alternate path
1. 캐시 hit → LLM 호출 없이 동일 result 재생산·저장.
### Fail path
1. 🔴 LLM miss 호출 실패 → 가짜 점수 금지, 해당 공고 **보류 상태**로 영속(FAC-3 / ARCH §7-4 보류 표현).
2. 🟡 DB write 실패 → 부분 저장 방지(트랜잭션), 재시도.

## 4. 범위
- worker 영속 어댑터: `job_postings`·`resumes`(또는 seed) **읽기**, `ranking_runs`(result JSONB) + `recommendations`(scalar feed projection) **쓰기**(자기 소유 테이블만, §3-2 규칙1). 기존 `worker/cache.py` `CacheAdapter` 인터페이스 구현.
- 실행 진입점 `ai/worker/src/worker/__main__.py` — load → run_scoring → persist.
- seed 이력서 주입: config(SPEC §9-4 USER_DOMAINS 방식)로 **합성** 이력서 로드.
- GS-1-through-DB 라운드트립 테스트(동일 입력 2회 → 저장 result 바이트 동일).

## 5. 비범위
- crawler 영속(F-008) · API 서빙(F-009) · Feed UI(F-010).
- 실 PII 이력서/UI 업로드 — M2는 합성 seed(Charter §5 / M2 milestone §4).
- vector 검색(F-006 비범위 정합).

## 6. 요구사항
- `ranking_runs.result`는 `run_scoring` 산출을 **verbatim JSONB**로 저장(파싱·변형 금지, §3-2 규칙3).
- 캐시 키(`make_key`)는 바이트 동일 유지 — 시간·랜덤·env 혼입 금지(§3-1 / ADR-100 D3). DB 어댑터는 키 *개념*을 바꾸지 않는다.
- 저장 시 버전 필드(`model`·`prompt_version`·`scoring_mode`·`ranking_mode`·`cache_key_version`) 동반.
- LLM miss 실패는 보류 상태로 영속(가짜 점수 금지).
- worker는 `ranking_runs`/`recommendations`만 write, 나머지는 read-only(소유권).
- `recommendations`(feed projection)를 `final_ranking`(scored: `rank_position`·`fit_level`·`status='scored'`) + **`pending_job_ids`(held: `fit_level`=NULL·`status='held'`·scored 뒤)**에서 도출해 함께 영속. NestJS가 opaque JSONB 없이 정렬 feed를 만드는 면(F-009·F-006 정합).
- **`ranking_runs` upsert 키 = `(resume_id, job_set_hash, model, prompt_version, scoring_mode, ranking_mode, cache_key_version)`** 결정적 복합키(중복 run 방지 + FAC-2 바이트 동일성 직결 — cross-LLM P1 해소).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** `python -m worker`가 seed 이력서 + DB `job_postings`로 `run_scoring`을 돌려 `ranking_runs`(result) + `recommendations`(scalar projection)에 upsert한다.
- **FAC-2 (GS-1-through-DB):** 동일 (이력서, 공고집합) + 웜 캐시로 2회 실행 시 저장된 `result`가 바이트 동일하다.
- **FAC-3:** LLM miss 실패 공고가 가짜 점수 없이 보류 상태로 `result`에 보존된다.
- **FAC-4:** worker는 `ranking_runs`/`recommendations`에만 write하고 `job_postings`/`resumes`는 read-only다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 (진입점 실행→영속) → T-023:AC-1
- FAC-2 (GS-1-through-DB 결정성) → T-022:AC-2
- FAC-3 (보류 영속) → T-022:AC-3, T-023:AC-2
- FAC-4 (소유권 write 경계) → T-022:AC-1

## 8. Non-functional Requirements
- 지배: 신뢰성(GS-1) — DB 왕복·JSONB 재직렬화가 결정성을 흔들지 않음.
- 성능: 캐시 hit은 LLM 지연과 분리(즉시). miss 배치 지연 목표는 후속.

## 8-1. UX 흐름 품질
(해당 없음 — 비-UI. 보류 상태의 *표시*는 F-010.)

## 9. 엣지 케이스
- JSONB 재직렬화 키 순서 변동(결정성 위협 — 라운드트립 테스트로 고정).
- 부분 공고 보류 + 나머지 정상(혼합 result).
- 캐시 miss 다발 시 LLM 비용 — crawl/score 분리(F-008)로 수집 실패가 비용 안 태움.

## 10. 의존성
- **선행:** T-020(스키마 — `ranking_runs`/`job_postings`), T-021(Python DB 접근).
- **블로킹:** F-009(API가 `ranking_runs`를 서빙하려면 데이터 필요).

## 11. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature(선행 알고리즘): [F-001-core-value](F-001-core-value.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-1 결정론 경계, §3-2 규칙1·3, §5 스코어링 흐름)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3) (결정론 캐시 키 — Worker 책임)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (§8 캐시, §9-4 이력서 주입, §11 JSONB)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) (D3) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-CONTRACT)

## 12. 열린 질문
- seed 이력서 형식·위치(env JSON vs 파일) — SPEC §9-4 방식 준용.
- **결정(cross-LLM P1 회수):** `ranking_runs` upsert 키 = `(resume_id, job_set_hash, model, prompt_version, scoring_mode, ranking_mode, cache_key_version)` 결정적 복합키 — F-006 unique 제약에 반영.
