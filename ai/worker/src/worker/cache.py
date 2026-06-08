"""worker/cache.py — 결정론 캐시 키 + LLM 응답 디스크 캐시 + 인메모리 어댑터.

키 구성: sha256(NUL(model, system, user, schema_version)) (SPEC §8-2).
시간·랜덤·환경 값 혼입 금지 (ARCH §3-1 결정론 경계 규칙).

LLM 응답 캐시(llm_cache_get/put): _openai_call이 쓰는 디스크 캐시. 동일 입력은 동일
응답을 재현해 재현성을 보장한다 — gpt-5.4-mini는 seed로도 비결정적이라 캐시가 유일한
재현 메커니즘이다(없으면 새로고침마다 fit ±1 흔들림). env:
  LLM_CACHE          기본 on (0/false/off → 비활성)
  LLM_CACHE_REFRESH  on → 강제 미스 + 신선 재기록
  LLM_CACHE_DIR      기본 = 레포 루트 .cache/llm
프로덕션은 ARCH §7-3대로 동일 키로 Postgres JSONB 어댑터 교체 가능.

CacheAdapter: 향후 DB 어댑터용 인터페이스(현재 인메모리).
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

_ROOT_MARKERS = (".git", "uv.lock", "pnpm-lock.yaml", ".env.example")


def make_key(model: str, system: str, user: str, schema_version: str) -> str:
    """결정론 캐시 키 — sha256(NUL(model, system, user, schema_version)).

    NUL 구분자로 파트 경계를 분리해 ("ab","c") vs ("a","bc") 충돌을 막는다.
    렌더링된 프롬프트(system + user) + 모델 ID + 스키마 버전으로 구성한다.
    SPEC §8-2: 키에 시간·랜덤·환경 값 혼입 금지.
    """
    h = hashlib.sha256()
    for part in (model, system, user, schema_version):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# LLM 응답 디스크 캐시 (재현성) — _openai_call이 사용
# ---------------------------------------------------------------------------

# env는 호출 시점에 읽는다(테스트 monkeypatch 용이).
_FALSEY = {"0", "false", "off", "no", ""}
_TRUTHY = {"1", "true", "on", "yes"}


def _cache_enabled() -> bool:
    return os.environ.get("LLM_CACHE", "1").strip().lower() not in _FALSEY


def _cache_refresh() -> bool:
    return os.environ.get("LLM_CACHE_REFRESH", "0").strip().lower() in _TRUTHY


def _cache_dir() -> Path:
    env_dir = os.environ.get("LLM_CACHE_DIR")
    if env_dir:
        return Path(env_dir)
    for parent in Path(__file__).resolve().parents:
        if any((parent / m).exists() for m in _ROOT_MARKERS):
            return parent / ".cache" / "llm"
    return Path(".cache") / "llm"


def llm_cache_get(key: str) -> str | None:
    """디스크 캐시에서 LLM 원응답 텍스트를 읽는다. 비활성/refresh/미스/손상 → None."""
    if not _cache_enabled() or _cache_refresh():
        return None
    path = _cache_dir() / f"{key}.json"
    if not path.exists():
        return None
    try:
        response = json.loads(path.read_text(encoding="utf-8")).get("response")
        return response if isinstance(response, str) else None
    except (OSError, ValueError):
        return None


def llm_cache_put(key: str, response: str) -> None:
    """LLM 원응답 텍스트를 디스크에 저장한다(쓰기 실패는 치명적 아님)."""
    if not _cache_enabled():
        return
    directory = _cache_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{key}.json").write_text(
            json.dumps({"response": response}, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def get_cache_adapter() -> "CacheAdapter":
    """환경변수에 따라 캐시 어댑터를 선택한다 (T-088 expand 단계).

    USE_POSTGRES_CACHE=1 → PostgresCacheAdapter(DATABASE_URL) (멀티 인스턴스 공유, GS-1)
    그 외 → CacheAdapter(인메모리 기본값 — 로컬 개발).
    PostgresCacheAdapter가 CacheAdapter를 상속하므로 순환 import 회피용 지연 import.
    """
    if os.environ.get("USE_POSTGRES_CACHE") == "1":
        from worker.cache_postgres import PostgresCacheAdapter

        return PostgresCacheAdapter(os.environ.get("DATABASE_URL", ""))
    return CacheAdapter()


class CacheAdapter:
    """캐시 저장 어댑터 — 인터페이스 고정, 구현은 인메모리(MVP).

    get(key) → dict | None
    put(key, value) → None
    refresh(key) → None  # 해당 키를 캐시에서 제거해 재계산 강제 (SPEC §8-2 REFRESH)

    Postgres JSONB 어댑터 교체 시 이 인터페이스를 구현하면 된다.
    """

    def __init__(self, namespace: str = "default") -> None:
        # namespace 격리 — eval/fixture 캐시가 일반 실행 캐시와 섞이지 않게 (SPEC §8-2)
        self._store: dict[str, Any] = {}
        self.namespace = namespace

    def _ns_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    def get(self, key: str) -> Any | None:
        return self._store.get(self._ns_key(key))

    def put(self, key: str, value: Any) -> None:
        self._store[self._ns_key(key)] = value

    def refresh(self, key: str) -> None:
        """SPEC §8-2 --refresh-cache 동등: 해당 키 제거 → 다음 get은 miss."""
        self._store.pop(self._ns_key(key), None)
