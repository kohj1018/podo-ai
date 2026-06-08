# T-088-postgres-cache-adapter

## 0. Status
done

## 0-1. Type
migration

## 1. 작업 목적
`ai/worker/src/worker/cache.py`의 디스크 캐시(`.cache/llm`, 단일프로세스)를 **Postgres 공유 어댑터**로 교체한다. `CacheAdapter` 인터페이스는 이미 존재 — 동일 캐시 키(이력서 정규화본·JD·모델·프롬프트 버전)를 유지해 GS-1(결정론) 보존. S3 미사용(ARCH §7-3 — 바이너리 저장 없음). F-027 FAC-1.

**expand-contract 단계:**
1. Expand: Postgres 어댑터 신규 구현(기존 디스크 어댑터 유지).
2. Contract: 환경변수 플래그로 Postgres 어댑터 활성화.
3. 검증 후 디스크 어댑터 참조 제거.

## 2. 작업 범위
- `ai/worker/src/worker/cache_postgres.py`: `CacheAdapter` 구현 — Postgres JSONB 테이블(`llm_cache`, 컬럼: `cache_key TEXT PK`, `response JSONB`, `created_at`, `model_version`, `prompt_version`). 동일 캐시 키 → 동일 결과 반환.
- Prisma migration: `llm_cache` 테이블 raw SQL 추가(Python worker 소유 테이블 — DDL=Prisma SSOT).
- `ai/worker/src/worker/cache.py`: `USE_POSTGRES_CACHE` 환경변수 플래그로 어댑터 선택(expand 단계).
- 캐시 장애 시 graceful fallback: DB 접근 실패 → cache miss(재계산, 정확도 유지).
- 기존 디스크 캐시 키와 동일 포맷 사용 — 마이그레이션 중 키 호환.

## 3. 구현 항목
1. `podo/apps/api/prisma/migrations/YYYYMMDD_add_llm_cache/migration.sql` — 현재: 없음 → 변경: `CREATE TABLE IF NOT EXISTS llm_cache (cache_key TEXT PRIMARY KEY, response JSONB NOT NULL, model_version TEXT NOT NULL, prompt_version TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW())` → 확인: `prisma migrate deploy` green + `\d llm_cache` 컬럼 존재. (AC-1)
2. `ai/worker/src/worker/cache_postgres.py` — 현재: 없음 → 변경: `class PostgresCacheAdapter(CacheAdapter)` — `get(key)`: `SELECT response FROM llm_cache WHERE cache_key=$1`, `set(key, value)`: `INSERT INTO llm_cache ... ON CONFLICT DO UPDATE`, DB 접근 실패 시 `None` 반환(cache miss) → 확인: `pytest ai/tests/test_cache_postgres.py` pass. (AC-1)
3. `ai/worker/src/worker/cache.py` — 현재: 디스크 어댑터 고정 → 변경: `if os.getenv('USE_POSTGRES_CACHE') == '1': return PostgresCacheAdapter(db_url)` else 기존 디스크 어댑터 → 확인: `USE_POSTGRES_CACHE=1` 환경변수 설정 시 PostgresCacheAdapter가 선택됨을 단위 테스트 확인. (AC-1)
4. `ai/tests/test_cache_postgres.py` — 현재: 없음 → 변경: ①동일 키 2회 get → 2회째 캐시 히트(DB round-trip 1회); ②DB 연결 실패 시 `None` 반환(graceful); ③다른 키 → 다른 결과 → 확인: `pytest ai/tests/test_cache_postgres.py -v` 3케이스 pass. (AC-1)
5. `ai/tests/test_cache_gss1.py` — 현재: 없거나 디스크 대상 → 변경: PostgresCacheAdapter에서 동일 입력 → 동일 결과 검증(GS-1 회귀 테스트) → 확인: `pytest ai/tests/test_cache_gss1.py` pass. (AC-2)

## 4. 제외 항목
- S3 어댑터 — S3 미사용(ARCH §7-3, 바이너리 저장 없음).
- 캐시 무효화 정책 전면 재설계 — 버전 핀 유지(M5 출력계약 동결).
- 디스크 어댑터 코드 삭제 — contract 단계(배포 환경 검증 후 별도 PR).
- 다중 worker 인스턴스 실행 — F-027 후속(미분해)(F-027 후속).

## 4-1. 변경 예정 파일/경로
- `podo/apps/api/prisma/migrations/20260608140000_add_llm_cache/migration.sql` (신규) — `llm_cache` 테이블(cache_key PK·response JSONB·model_version·prompt_version·created_at)
- `podo/apps/api/prisma/schema.prisma` — `LlmCache` 모델 추가(migration↔schema drift 방지; Prisma=DDL SSOT §3-2)
- `ai/worker/src/worker/cache_postgres.py` (신규) — `PostgresCacheAdapter(CacheAdapter)` get/put/refresh(namespace 재사용) + graceful fallback + 메타 컬럼
- `ai/worker/src/worker/cache.py` — `get_cache_adapter()` factory(`USE_POSTGRES_CACHE` 플래그, 순환 import 회피 지연 import)
- `ai/tests/test_cache_postgres.py` (신규) — AC-1 7 테스트(mock psycopg, 항상 실행): 히트·미스·graceful fallback·put silent·다른 키·어댑터 선택
- `ai/tests/test_cache_gss1.py` (신규) — AC-2 GS-1 멀티인스턴스 + refresh(DATABASE_URL 게이트)
- `ai/tests/test_schema_contract.py` — `test_AC_3_llm_cache_columns_exist`(AC-3, DB 게이트)

## 5. 완료 조건
`USE_POSTGRES_CACHE=1` 환경변수 설정 시 worker가 Postgres llm_cache 테이블에서 캐시를 조회하고, 동일 입력에 대해 인스턴스와 무관하게 동일 결과를 반환하며(GS-1), DB 장애 시 cache miss로 재계산한다.

## 6. Acceptance Criteria
- AC-1 [Given] `USE_POSTGRES_CACHE=1` + Postgres 연결 [When] 동일 cache_key로 2회 get [Then] 2회째는 DB에서 캐시 히트하고 동일 response를 반환하며, DB 연결 실패 시 `None`을 반환한다.
- AC-2 [Given] PostgresCacheAdapter + 동일 입력(이력서 정규화본·JD·모델·프롬프트 버전 동일) [When] worker 인스턴스 2개가 동일 키로 조회 [Then] 두 인스턴스가 동일 결과를 반환한다(GS-1 멀티인스턴스).
- AC-3 [Given] `prisma migrate deploy` 실행 [When] `llm_cache` 테이블 존재 확인 [Then] `cache_key`·`response`·`model_version`·`prompt_version`·`created_at` 컬럼이 모두 존재한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → `pytest::ai/tests/test_cache_postgres.py::test_AC_1_cache_hit_and_miss_fallback`
- AC-2 → `pytest::ai/tests/test_cache_gss1.py::test_AC_2_same_key_same_result_multiinstance`
- AC-3 → `pytest::ai/tests/test_schema_contract.py::test_AC_3_llm_cache_columns_exist`

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M6-deployment](../milestones/M6-deployment.md)
- Feature: [F-027-shared-cache-and-hardening](../features/F-027-shared-cache-and-hardening.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-3 캐시 어댑터)
- Architecture-Iface: [ARCH ## 7-3 백엔드/캐시](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-DB)

## 8. 메모
- GS-1 보존 핵심: 캐시 키 포맷(이력서 정규화본 해시 + JD ID + 모델 ID + 프롬프트 버전)이 디스크 어댑터와 동일해야 함. 키 포맷 변경 시 기존 캐시 무효화(허용 — 재계산 fallback).
- expand 단계: `USE_POSTGRES_CACHE` 플래그로 점진 전환. 디스크 어댑터는 로컬 개발 유지.
- llm_cache는 worker 소유 테이블(D-CONTRACT 규칙 1) — NestJS는 읽기 금지.
- 테스트 DB: pytest fixture에서 postgres test DB(또는 `testcontainers-python`) 사용 권장.

## 9. 의존성
- depends_on: [T-082, T-084]   # RDS(Postgres, T-082) + F-025 단일 worker 배포(T-084) 선행(F-025→F-027 순서). T-085(crawl cron)은 무관.
- write_set: ["podo/apps/api/prisma/migrations/**", "ai/worker/src/worker/cache_postgres.py", "ai/worker/src/worker/cache.py", "ai/tests/test_cache_postgres.py", "ai/tests/test_cache_gss1.py"]
- assumptions: ["T-082 RDS·Prisma migrate 완료", "CacheAdapter 인터페이스가 ai/worker/src/worker/cache.py에 존재", "F-025 단일 worker 배포됨(T-084)"]
- verifier: "uv run pytest ai/tests/test_cache_postgres.py -v"
