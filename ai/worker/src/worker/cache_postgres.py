"""worker/cache_postgres.py — Postgres 공유 캐시 어댑터 (T-088 expand 단계).

CacheAdapter 인터페이스를 Postgres JSONB `llm_cache` 테이블로 구현한다. 동일 캐시 키
(이력서 정규화본·JD·모델·프롬프트 버전이 make_key로 해시된 값)를 유지해 GS-1(결정론)을
멀티 worker 인스턴스에서 보존한다(디스크 캐시는 단일프로세스라 인스턴스 간 공유 불가).

DB 접근 실패는 get→None(cache miss)·put→no-op으로 graceful 처리한다 — 캐시는 재현성
보조이지 정확도 소스가 아니므로, 장애 시 재계산으로 정확도를 유지한다(ARCH §7-3).

`llm_cache`는 worker 소유 테이블(D-CONTRACT 규칙1) — NestJS는 읽기 금지.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.types.json import Json

from worker.cache import CacheAdapter


class PostgresCacheAdapter(CacheAdapter):
    """Postgres JSONB `llm_cache` 기반 공유 캐시 어댑터(CacheAdapter 구현).

    get/put/refresh를 DB로 오버라이드한다. namespace 격리는 부모 `_ns_key`를 재사용해
    디스크/인메모리 어댑터와 동일한 키 규약을 유지한다.

    매 호출 단일 연결(connect-per-call) — 단순성·장애 격리 우선(MVP). 연결 풀은 후속
    성능 최적화(F-027 후속).
    """

    def __init__(
        self,
        db_url: str,
        *,
        namespace: str = "default",
        model_version: str | None = None,
        prompt_version: str | None = None,
    ) -> None:
        super().__init__(namespace)  # namespace + _ns_key 확보 (_store는 미사용)
        self._db_url = db_url
        # 메타 컬럼(NOT NULL) — 키가 이미 인코딩하나 ops 추적용 보관.
        self._model_version = model_version or os.environ.get("OPENAI_MODEL", "unknown")
        self._prompt_version = prompt_version or os.environ.get("PROMPT_VERSION", "v1")

    def get(self, key: str) -> Any | None:
        """cache_key로 llm_cache를 조회한다. 미스·DB 장애 시 None(재계산 fallback)."""
        try:
            with psycopg.connect(self._db_url) as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT response FROM llm_cache WHERE cache_key = %s",
                    (self._ns_key(key),),
                )
                row = cur.fetchone()
                return row[0] if row is not None else None  # JSONB → dict (psycopg3)
        except Exception:  # noqa: BLE001 — 시스템 경계(DB): 장애 → cache miss
            return None

    def put(self, key: str, value: Any) -> None:
        """llm_cache에 UPSERT한다(동일 키 → response 갱신). DB 장애 시 silent."""
        try:
            with psycopg.connect(self._db_url) as conn, conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO llm_cache "
                    "(cache_key, response, model_version, prompt_version) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (cache_key) DO UPDATE SET "
                    "response = EXCLUDED.response, "
                    "model_version = EXCLUDED.model_version, "
                    "prompt_version = EXCLUDED.prompt_version",
                    (
                        self._ns_key(key),
                        Json(value),
                        self._model_version,
                        self._prompt_version,
                    ),
                )
                conn.commit()
        except Exception:  # noqa: BLE001 — 시스템 경계(DB): 쓰기 실패는 치명적 아님
            pass

    def refresh(self, key: str) -> None:
        """키를 llm_cache에서 제거 → 다음 get은 miss(SPEC §8-2). 장애 시 silent."""
        try:
            with psycopg.connect(self._db_url) as conn, conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM llm_cache WHERE cache_key = %s", (self._ns_key(key),)
                )
                conn.commit()
        except Exception:  # noqa: BLE001 — 시스템 경계(DB): 장애 무시
            pass
