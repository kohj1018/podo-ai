# F-006-db-schema-contract: 최소 DB 스키마(Prisma SSOT) + 폴리글랏 schema-contract 가드

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 요약
Prisma를 스키마 SSOT로 최소 5테이블(`job_postings`·`crawl_runs`·`ranking_runs(result JSONB)`·`recommendations`·`resumes`)을 DDL로 정의·마이그레이션하고, Python(worker/crawler)이 같은 DB를 raw SQL로 안전히 읽/쓰도록 **폴리글랏 schema-contract test를 실가동**한다(현 `ai/tests/test_schema_contract.py` skipped placeholder 교체). 이 contract test가 R6(폴리글랏 schema drift)의 *유일한 컴파일-타임 대체 가드*다.

## 2. 사용자 가치 (User Story) — Type=technical-enabler 이므로 기술적 근거
- **무엇/왜:** Prisma가 스키마 SSOT(DDL 소유)지만 Python worker/crawler는 같은 DB를 손으로 읽으므로 **컴파일 가드가 없다** — Prisma 마이그레이션이 worker 의존 컬럼을 바꾸면 런타임에 터진다. schema-contract pytest가 PR에서 이를 잡는 유일한 방벽(ARCH §3-2 규칙2·R6).
- **서비스하는 결정/가정:** ADR-101 D-DB(Prisma SSOT)·D-CONTRACT(계약 3규칙) · ARCH §3-2 테이블 소유권 분리 · 가정 R6(schema drift).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. `prisma migrate dev` → 5테이블 + `CREATE EXTENSION vector`(raw SQL DDL) 생성.
2. Python이 raw SQL로 5테이블 read/write 가능.
3. `schema-contract` pytest가 갓 마이그레이션한 DB에 붙어 worker 의존 컬럼·타입 존재를 검증(green).
### Fail path
1. 🔴 마이그레이션이 worker 의존 컬럼을 제거/개명 → schema-contract test가 PR에서 **red**로 잡음(R6 차단).

## 4. 범위
- Prisma schema + 초기 migration:
  - `job_postings`(crawler 소유) · `crawl_runs`(crawler 소유 — **run별 1행** append: channel·run_at·status·counts·error)
  - `ranking_runs`(worker 소유 — `result` JSONB[evidence 상세, opaque] + 버전 필드)
  - **`recommendations`(worker 소유 — feed projection):** run_id·job_posting_id·`rank_position`·**`fit_level`(nullable — held=NULL)**·domain_alignment·`status`(scored|held) **scalar 컬럼**. scored는 `final_ranking`에서, **held는 `pending_job_ids`에서** 도출. NestJS가 *opaque JSONB를 파싱하지 않고* 정렬·커서 페이지·배지를 만드는 좁은 면(P0 해소 — §3-2가 worker-owned로 명명).
  - `resumes`(api 소유, seed 주입 대상).
- pgvector `CREATE EXTENSION vector`를 Prisma raw SQL 마이그레이션에 포함(DDL 소유권 = Prisma, §3-2 규칙2).
- `ai/core`에 Python DB 접근 모듈(raw SQL connection/helper) — worker·crawler·eval 공유.
- `ai/tests/test_schema_contract.py`를 placeholder → **실측 contract test**로 교체(worker/crawler 의존 컬럼·타입 assert).

## 5. 비범위
- vector 컬럼·HNSW 인덱스·vector 검색 — M2는 크롤된 job set을 직접 채점(후보검색 미사용) → vector *DML* 비범위(extension만 둠).
- `users`·`billing` 등 user-facing 테이블 — M2 비범위. (※ `recommendations`는 feed projection으로 §4 범위에 **포함** — opaque JSONB만으론 정렬 feed가 불가하다는 cross-LLM P0 해소. `matching_rows`/`pairwise`[알고리즘 내부 구조]는 `ranking_runs.result` JSONB 내 보존 — 여전히 YAGNI.)
- 모델/프롬프트 버전 bump 시 캐시 마이그레이션 *실행* — 본 feature는 마이그레이션을 *가능케 하는 버전 필드*만 보유(SPEC §8-2).

## 6. 요구사항
- 테이블 소유권 단일 writer(§3-2 규칙1): crawler→`job_postings`/`crawl_runs`, worker→`ranking_runs`/`recommendations`, api→`resumes`.
- `ranking_runs`는 좁은 JSONB 계약(`result`) + 버전 필드(`model`·`prompt_version`·`scoring_mode`·`ranking_mode`·`cache_key_version`) 보유(SPEC §8-2 / M2 milestone §7).
- **`recommendations`는 NestJS가 opaque JSONB를 파싱하지 않고 정렬·커서·배지를 만드는 scalar projection**(§7-1 opacity 보존). cursor stable key = `rank_position`(알고리즘 순서). `ranking_runs.result`는 evidence 상세로 opaque 유지.
- **`crawl_runs`는 run별 1행(append)**; coverage `last_success_at`는 채널별 `MAX(run_at WHERE status='success')`로 파생(F-008 기록 ↔ F-009 coverage API 동일 shape 의존 — cross-LLM P1 해소).
- schema-contract test는 **갓 마이그레이션한 DB**에 붙어 검증(ARCH §3-2 규칙2 / §7-3).
- JSONB 직렬화는 결정적(키 순서·float 안정) — GS-1-through-DB 전제(F-007과 정합).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** `prisma migrate dev`가 **5테이블** + `vector` extension을 생성한다.
- **FAC-2:** schema-contract pytest가 worker/crawler 의존 컬럼·타입 존재를 검증해 green이고, 의존 컬럼을 제거한 변형 스키마에선 red다.
- **FAC-3:** `ranking_runs`가 `result` JSONB + 5개 버전 필드를 보유하고, `recommendations`가 정렬/커서용 scalar 컬럼(`rank_position`·`fit_level`·`status`)을 보유한다.
- **FAC-4:** Python(`ai/core`)이 raw SQL로 5테이블에 read/write 하고, `crawl_runs`가 run별 1행으로 append되어 채널별 `last_success_at` 파생이 가능하다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 (5테이블+extension 마이그레이션) → T-020:AC-1
- FAC-2 (schema-contract green/red) → T-021:AC-2
- FAC-3 (ranking_runs 버전 필드 + recommendations projection 컬럼) → T-020:AC-2
- FAC-4 (Python raw SQL I/O + crawl_runs run별 1행) → T-021:AC-1

## 8. Non-functional Requirements
- 지배: schema drift 가드(R6). contract test가 CI PR 게이트.
- 보안: `DATABASE_URL`은 env(커밋 금지). `resumes`(PII)는 M2에선 합성 seed(F-007).

## 8-1. UX 흐름 품질
(해당 없음 — 비-UI.)

## 9. 엣지 케이스
- pgvector extension 생성과 테이블 생성의 마이그레이션 순서(extension 먼저).
- Prisma 타입 ↔ Python raw SQL 타입 매핑(JSONB·timestamptz·text[]).
- JSONB 재직렬화 시 키 순서 변동(결정성 위협 — F-007 라운드트립 테스트가 최종 검증).
- `recommendations` projection ↔ `ranking_runs.result`의 정합(같은 run의 projection 행 집합 ↔ JSONB ranking이 동일 순서·동일 job 집합).

## 10. 의존성
- **선행:** T-018(`podo/apps/api` scaffold — Prisma 초기화 위치).
- **블로킹:** F-007·F-008·F-009가 본 스키마에 의존.

## 11. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 폴리글랏 계약 3규칙·테이블 소유권)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3) (schema-contract·결정론 캐시 키)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (§3 데이터 계약, §8 캐시 키, §11 JSONB 산출)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-DB·D-CONTRACT) · [ADR-102](../../90-decisions/project/ADR-102-python-test-layout.md) (test 레이아웃 — schema-contract는 `ai/tests/` foundational)

## 12. 열린 질문
- pgvector를 M2에서 extension만 둘지, vector 컬럼까지 선반영할지 — 본 feature는 extension만(검색 DML 비범위).
- 캐시(`make_key` 산출)를 `ranking_runs`에 통합할지 별도 캐시 테이블로 둘지 — 통합(좁은 JSONB) 권장.
- Python DB 드라이버(psycopg vs asyncpg) — worker 동기 파이프라인 정합상 psycopg 권장(구현 시 확정).
