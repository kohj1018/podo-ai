"""worker/llm.py — LLM 게이트웨이 (OpenAI 핀).

call_text: 텍스트 응답.
call_structured: JSON 파싱 + validate + 1회 재시도 + 선택적 캐시 (SPEC §8-1).

OpenAI 파라미터 자동 적응(max_tokens↔max_completion_tokens, seed 지원 여부)은
API 에러 기반으로 처리 — 모델명 하드코딩 없음 (SPEC §8-1).
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from worker.cache import llm_cache_get, llm_cache_put, make_key
from worker.config import LLM_SEED, OPENAI_API_KEY, OPENAI_MODEL, SCHEMA_VERSION

# JSON_SYSTEM 시스템 프롬프트 (SPEC §8-1).
# 프로토타입 검증 문구 — 추출형·사실성 보장 지시("never invent facts / follow
# instructions exactly")가 7개 LLM 단계 전부를 감싼다. 임의 약화 금지.
JSON_SYSTEM = (
    "You are a careful, literal information-extraction and evaluation engine. "
    "You follow instructions exactly, never invent facts, and output ONLY valid JSON "
    "with no extra text, no markdown, and no code fences."
)


class LLMError(Exception):
    """LLM 호출 또는 검증이 최대 시도 후에도 실패한 경우."""


def _extract_json(text: str) -> Any:
    """응답에서 JSON을 추출한다 — code fence 제거 + greedy shrink (SPEC §8-1).

    실패 시 ValueError를 raise한다.
    """
    # code fence 제거
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    # 첫 { 또는 [ 부터 마지막 } 또는 ] 까지 greedy shrink
    for start_ch, end_ch in [("{", "}"), ("[", "]")]:
        start = cleaned.find(start_ch)
        end = cleaned.rfind(end_ch)
        if start != -1 and end != -1 and end >= start:
            return json.loads(cleaned[start : end + 1])
    raise ValueError(f"JSON을 찾을 수 없음: {text[:120]!r}")


def _openai_call(system: str, user: str, max_tokens: int, temperature: float) -> str:
    """실제 OpenAI API 호출 — 모델 파라미터 자동 적응 포함.

    시스템 경계: 외부 API 호출 — 여기서만 OpenAI SDK를 사용한다.

    신형 모델(o-series / gpt-5 계열, 예: gpt-5.4-mini)은 max_tokens 대신
    max_completion_tokens를 요구하고 기본 temperature(=1)만 허용한다. 공통 형태를
    먼저 시도하고 API 에러 메시지에 따라 token 파라미터·seed·temperature를 순차
    fallback한다 — 모델명 하드코딩 없음 (SPEC §8-1).

    재현성: 동일 (model, system, user, SCHEMA_VERSION)이면 디스크 캐시 응답을 반환해
    LLM 비결정성을 제거한다 (cache miss일 때만 실제 API 호출). cache.llm_cache_* 참조.
    """
    cache_key = make_key(OPENAI_MODEL, system, user, SCHEMA_VERSION)
    cached = llm_cache_get(cache_key)
    if cached is not None:
        return cached

    import openai

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    token_param = "max_tokens"
    send_temperature = temperature != 1.0
    send_seed = True
    last_err: Exception | None = None
    for _ in range(5):
        kwargs: dict[str, Any] = {
            "model": OPENAI_MODEL,
            "messages": messages,
            token_param: max_tokens,
        }
        if send_temperature:
            kwargs["temperature"] = temperature
        if send_seed:
            kwargs["seed"] = LLM_SEED
        try:
            response = client.chat.completions.create(**kwargs)
            text = (response.choices[0].message.content or "").strip()
            llm_cache_put(cache_key, text)
            return text
        except Exception as exc:  # noqa: BLE001 — 시스템 경계: API 에러로 파라미터 적응
            msg = str(exc).lower()
            if token_param == "max_tokens" and "max_completion_tokens" in msg:
                token_param = "max_completion_tokens"
                last_err = exc
                continue
            if send_seed and "seed" in msg:
                send_seed = False
                last_err = exc
                continue
            if send_temperature and "temperature" in msg:
                send_temperature = False  # 모델 기본 temperature로 fallback
                last_err = exc
                continue
            raise
    if last_err:
        raise last_err
    raise LLMError("지원되는 파라미터로 OpenAI 호출을 만들 수 없습니다")


def call_text(
    system: str,
    user: str,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    *,
    _call_fn: Callable[..., str] | None = None,
) -> str:
    """텍스트 LLM 호출 — 구조화 검증 없음."""
    fn = _call_fn or _openai_call
    return fn(system=system, user=user, max_tokens=max_tokens, temperature=temperature)


def call_structured(
    system: str,
    user: str,
    validate: Callable[[dict[str, Any]], dict[str, Any]],
    max_tokens: int = 1024,
    temperature: float = 0.0,
    cache_label: str | None = None,
    *,
    _call_fn: Callable[..., str] | None = None,
) -> dict[str, Any]:
    """JSON 파싱 + validate + 1회 재시도 (SPEC §8-1).

    1차 실패 시 직전 에러를 user 프롬프트에 첨부해 재시도한다.
    2회 모두 실패하면 LLMError를 raise한다 (가짜 결과 생성 금지 — AC-3).

    _call_fn: 테스트용 주입 인터페이스 (기본값 = _openai_call).
    cache_label: 캐시 레이블 — 현재 인터페이스 보존용, 저장 통합은 후속.
    """
    fn = _call_fn or _openai_call
    last_error: str = ""

    for attempt in range(2):
        if attempt == 0:
            current_user = user
        else:
            # 재시도: 직전 에러를 첨부해 LLM에 수정 기회를 준다 (SPEC §8-1)
            current_user = (
                f"{user}\n\n[이전 응답 오류: {last_error}]\n"
                "위 오류를 수정해 유효한 JSON만 반환하세요."
            )

        raw = fn(
            system=system,
            user=current_user,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            data = _extract_json(raw)
            result = validate(data)
            return result
        except Exception as exc:  # noqa: BLE001 — 시스템 경계(LLM 외부 출력) 에러 수집
            last_error = str(exc)

    raise LLMError(f"LLM 호출이 2회 모두 실패했습니다. 마지막 오류: {last_error}")
