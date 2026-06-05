"""T-004 Acceptance Criteria tests — LLM 게이트웨이 + 결정론 캐시 키.

AC-1: call_structured가 1회 재시도 후 검증된 결과를 반환하고, 2회 모두 실패 시 LLMError.
AC-2: make_key가 동일 입력에 동일 키를 생성하고, SCHEMA_VERSION 변경 시 키가 달라진다.
AC-3: call_structured가 계속 실패하면 LLMError를 raise하고 가짜 결과를 만들지 않는다.
"""

import pytest

from worker.cache import CacheAdapter, make_key
from worker.config import SCHEMA_VERSION
from worker.llm import LLMError, call_structured

# ---------------------------------------------------------------------------
# AC-1: 잘못된 JSON 1회 후 올바른 JSON → 1회 재시도 후 검증된 결과 반환
#        2회 모두 실패 시 LLMError
# ---------------------------------------------------------------------------


def test_AC_1_structured_retry_once() -> None:
    """AC-1a: 가짜 LLM이 1회 실패 후 올바른 JSON을 줄 때 call_structured가 재시도 후 반환."""
    call_count = 0

    def fake_call(system: str, user: str, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "not valid json {{{"
        return '{"value": 42}'

    def validate(data: dict) -> dict:
        assert "value" in data
        return data

    result = call_structured(
        system="sys",
        user="usr",
        validate=validate,
        max_tokens=100,
        _call_fn=fake_call,
    )
    assert result == {"value": 42}
    assert call_count == 2  # 1회 실패 + 1회 성공 = 2회 호출


def test_AC_1_both_fail_raises_llm_error() -> None:
    """AC-1b: 2회 모두 실패(JSON 파싱/검증 실패) 시 LLMError를 raise한다."""
    call_count = 0

    def fake_call(system: str, user: str, **kwargs):
        nonlocal call_count
        call_count += 1
        return "always invalid json {{{"

    def validate(data: dict) -> dict:
        return data

    with pytest.raises(LLMError):
        call_structured(
            system="sys",
            user="usr",
            validate=validate,
            max_tokens=100,
            _call_fn=fake_call,
        )
    assert call_count == 2


# ---------------------------------------------------------------------------
# AC-2: make_key 결정론 + SCHEMA_VERSION 변경 시 키 무효화
# ---------------------------------------------------------------------------


def test_AC_2_cache_key_determinism() -> None:
    """AC-2a: 동일 (model, rendered_prompt, SCHEMA_VERSION) → 동일 키."""
    model = "gpt-4o"
    system = "system prompt"
    user = "user prompt"
    schema_version = SCHEMA_VERSION

    key1 = make_key(model, system, user, schema_version)
    key2 = make_key(model, system, user, schema_version)
    assert key1 == key2, "동일 입력에 대해 make_key가 다른 키를 반환함"


def test_AC_2_cache_put_then_get() -> None:
    """AC-2b: put 후 get이 동일 값을 반환한다."""
    adapter = CacheAdapter()
    key = make_key("gpt-4o", "sys", "usr", SCHEMA_VERSION)
    value = {"fit": 3, "label": "보통"}

    adapter.put(key, value)
    result = adapter.get(key)
    assert result == value, f"캐시 get이 put한 값과 다름: {result}"


def test_AC_2_schema_version_invalidates_key() -> None:
    """AC-2c: SCHEMA_VERSION이 달라지면 캐시 키도 달라진다(자동 무효화)."""
    model = "gpt-4o"
    system = "system prompt"
    user = "user prompt"

    key_v1 = make_key(model, system, user, "v1")
    key_v2 = make_key(model, system, user, "v2")
    assert key_v1 != key_v2, "SCHEMA_VERSION 변경 시 캐시 키가 달라져야 함"


# ---------------------------------------------------------------------------
# AC-3: LLM 호출이 계속 실패 → 가짜 결과 없이 LLMError raise
# ---------------------------------------------------------------------------


def test_AC_3_failure_raises_not_fakes() -> None:
    """AC-3: 계속 실패하는 LLM에 대해 call_structured가 LLMError를 raise하고 가짜 결과를 반환하지 않는다."""

    def always_fail(system: str, user: str, **kwargs):
        return "invalid }"

    def validate(data: dict) -> dict:
        return data

    with pytest.raises(LLMError) as exc_info:
        call_structured(
            system="sys",
            user="usr",
            validate=validate,
            max_tokens=50,
            _call_fn=always_fail,
        )
    # LLMError가 raise됐으므로 가짜 결과가 반환되지 않았음이 보장된다.
    assert exc_info.value is not None
