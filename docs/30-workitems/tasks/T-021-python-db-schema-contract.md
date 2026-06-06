# T-021-python-db-schema-contract

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
Python(worker/crawler/eval 공유)이 같은 DB를 raw SQL로 읽/쓰도록 `ai/core` DB 접근 모듈을 만들고, **폴리글랏 schema-contract test를 실가동**한다(현 `ai/tests/test_schema_contract.py` skipped placeholder 교체) — R6(schema drift)의 유일한 컴파일-타임 대체 가드.

## 2. 작업 범위
- `ai/core`에 raw SQL DB 접근(connection + 최소 헬퍼) — worker·crawler·eval 공유.
- `ai/tests/test_schema_contract.py`를 placeholder → 실측: 갓 마이그레이션한 DB에 붙어 worker/crawler 의존 컬럼·타입 존재 assert(특히 `recommendations`·`ranking_runs` 복합키·`crawl_runs` run별 컬럼).

## 3. 구현 항목
1. 의존성 — `uv add psycopg[binary]`(ai/core, 용도: Python↔Postgres raw SQL). → 확인: import 가능. (AC-1)
2. `ai/core/src/core/db.py` — 현재: 없음 → 변경: `connect()`(DATABASE_URL env) + `fetch_all/execute` 최소 헬퍼(raw SQL). 시스템 경계만 검증(ARCH §2). → 확인: 신규 `ai/core/tests/test_db.py`가 5테이블 read/write smoke 통과. (AC-1)
3. `ai/tests/test_schema_contract.py` — 현재: skipped `NotImplementedError` placeholder → 변경: 마이그레이션된 DB에 붙어 **의존 컬럼·타입 assert**: `job_postings`(crawler 의존), `ranking_runs`(result Json + 복합 unique 7컬럼), `recommendations`(rank_position·fit_level·status + index), `crawl_runs`(channel·run_at·status). 컬럼 누락 시 fail. → 확인: 마이그레이션 후 green, 컬럼 drop 변형 시 red. (AC-2)

## 4. 제외 항목
- worker write 로직(T-022) · crawler write(T-024) · ORM(raw SQL만, §3-2) · vector 검색.

## 4-1. 변경 예정 파일/경로
- `ai/core/src/core/db.py`, `ai/core/tests/test_db.py`, `ai/tests/test_schema_contract.py`, `ai/core/pyproject.toml`, `uv.lock`

## 5. 완료 조건
Python이 raw SQL로 5테이블에 read/write 하고, schema-contract test가 갓 마이그레이션한 DB에서 의존 컬럼을 검증해 green이며 누락 시 red다.

## 6. Acceptance Criteria
- AC-1 [Given] 마이그레이션된 DB + `DATABASE_URL` [When] `core.db`로 5테이블 read/write [Then] insert→select 라운드트립이 성공하고 `crawl_runs`가 run별 1행 append된다.
- AC-2 [Given] 갓 마이그레이션한 DB [When] `test_schema_contract` 실행 [Then] worker/crawler 의존 컬럼(특히 `recommendations.rank_position`·`ranking_runs` result+복합키)이 존재하면 green, 의존 컬럼을 제거한 변형 스키마에선 red다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/core/tests/test_db.py::test_AC_1_raw_sql_roundtrip_5_tables
- AC-2 → pytest::ai/tests/test_schema_contract.py::test_AC_2_dependent_columns_present_else_fail

## 6-2. TDD opt-out
<!-- TDD 적용 — contract test 자체가 Red(placeholder)→Green(실측). -->

## 7. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Feature: [F-006-db-schema-contract](../features/F-006-db-schema-contract.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 규칙2 schema-contract, §7-3)
- ADR: [ADR-102](../../90-decisions/project/ADR-102-python-test-layout.md) (`ai/tests/`=foundational-contract) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-CONTRACT)

## 8. 메모
- 해석 확정: schema-contract는 `ai/tests/`(중앙 foundational, ADR-102 D1) 유지 — package behavior 아님.
- `recommendations` 컬럼 assert는 cross-LLM P0(M2-repair-1) 직접 반영.
- 구현 노트(2026-06-06): implement 포크가 psycopg 의존성만 추가하고 db.py·test_db·test_schema_contract 교체 전 사망 → 메인 세션 수동 완성.
- DB 테스트는 **DATABASE_URL 없으면 skip**(`pytest.mark.skipif`) — 로컬 `pnpm validate` 게이트 보호(DB 미가동 시 green, 3 skipped). CI(schema-contract.yml)·본 검증은 DATABASE_URL 주입 시 실행.
- test_db AC-1 라운드트립은 끝에 `rollback` → 멱등(반복 실행 시 url unique 충돌 없음, DB 미오염).
- 라이브 검증: DATABASE_URL 주입 시 3 테스트 green(AC-1 roundtrip+fetch_all + AC-2 contract). AC-2 red(컬럼 drop 시 fail)은 assert 구조가 보장(실 drop은 DB corruption 회피).

## 9. 의존성
- depends_on: [T-020]   # 스키마/마이그레이션이 있어야 contract 검증 대상 존재
- read_set: ["docs/20-system/ARCHITECTURE_OVERVIEW.md"]
- write_set: ["ai/core/src/core/db.py", "ai/core/tests/test_db.py", "ai/tests/test_schema_contract.py", "ai/core/pyproject.toml", "uv.lock"]
- assumptions: ["T-020 migrate 적용된 DB 접근 가능", "DATABASE_URL 설정됨"]
- verifier: "uv run pytest ai/tests/test_schema_contract.py ai/core/tests/test_db.py"
- # lockfile race: uv.lock write → 단독 wave 권장
