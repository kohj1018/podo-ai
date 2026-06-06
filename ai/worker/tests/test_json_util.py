"""T-030 AC-1: extract_json 단일 함수 행동 불변 검증.

_json_util.extract_json이 기존 _extract_json / _extract_json_raw의
동작 합집합을 커버하는지 확인한다 (code-fence 제거 + greedy shrink).
"""

import json

import pytest

from worker._json_util import extract_json

# ---------------------------------------------------------------------------
# AC-1: code-fence 제거 케이스
# ---------------------------------------------------------------------------


def test_AC_1_extract_json_plain_object() -> None:
    """순수 JSON object 응답을 파싱한다."""
    text = '{"winner": "a", "confidence": "high"}'
    result = extract_json(text)
    assert result == {"winner": "a", "confidence": "high"}


def test_AC_1_extract_json_code_fence_json() -> None:
    """```json ... ``` code-fence 래핑을 제거하고 파싱한다."""
    text = '```json\n{"winner": "b", "confidence": "medium"}\n```'
    result = extract_json(text)
    assert result == {"winner": "b", "confidence": "medium"}


def test_AC_1_extract_json_code_fence_bare() -> None:
    """``` ... ``` (언어 없는) code-fence를 제거하고 파싱한다."""
    text = '```\n{"key": "value"}\n```'
    result = extract_json(text)
    assert result == {"key": "value"}


def test_AC_1_extract_json_greedy_shrink_object() -> None:
    """앞뒤에 불필요한 텍스트가 있어도 { ... } 범위를 greedy shrink로 추출한다."""
    text = 'Some preamble text {"ranking": [1, 2, 3]} trailing'
    result = extract_json(text)
    assert result == {"ranking": [1, 2, 3]}


def test_AC_1_extract_json_array_wrapped() -> None:
    """LLM이 ranking을 object로 감싸서 반환하는 케이스 (_extract_json_raw 실사용 패턴).

    실제 listwise LLM 응답은 {"ranking": [...]} 형태이므로 object wrapper가 있다.
    순수 배열 [...]은 내부에 {}가 섞이면 greedy shrink가 object 우선 탐색하므로
    원본 3개 구현과 동일하게 object wrapper 형태를 정상 경로로 다룬다.
    """
    text = '{"ranking": [{"job_id": "j1"}, {"job_id": "j2"}]}'
    result = extract_json(text)
    assert result == {"ranking": [{"job_id": "j1"}, {"job_id": "j2"}]}


def test_AC_1_extract_json_array_with_fence() -> None:
    """code-fence로 감싼 object ranking을 파싱한다 (_extract_json_raw 케이스)."""
    text = '```json\n{"ranking": [{"job_id": "j1", "reason": "test"}]}\n```'
    result = extract_json(text)
    assert result == {"ranking": [{"job_id": "j1", "reason": "test"}]}


def test_AC_1_extract_json_nested() -> None:
    """중첩 JSON을 greedy shrink로 올바르게 파싱한다."""
    data = {"outer": {"inner": [1, 2, 3]}}
    text = json.dumps(data)
    result = extract_json(text)
    assert result == data


def test_AC_1_extract_json_raises_on_no_json() -> None:
    """JSON을 찾을 수 없으면 ValueError를 raise한다."""
    with pytest.raises(ValueError, match="JSON을 찾을 수 없음"):
        extract_json("no json here at all")


def test_AC_1_extract_json_single_source_behavior() -> None:
    """compare_pairwise·llm·rerank_listwise 3곳의 동작이 단일 함수로 수렴한다.

    각 모듈의 대표 케이스를 한 함수로 통과시켜 동작 합집합을 확인한다.
    """
    # compare_pairwise 케이스: plain object
    r1 = extract_json('{"winner": "a", "confidence": "high", "reason": "skill match"}')
    assert r1["winner"] == "a"

    # llm 케이스: code-fence + trailing backticks
    r2 = extract_json('```json\n{"result": true}\n```')
    assert r2["result"] is True

    # rerank_listwise (_extract_json_raw) 케이스: object-wrapped ranking (실사용 {"ranking": [...]}).
    # 원본 3개 구현은 object-first(첫 { 탐색)라 bare array가 아니라 object wrapper가 정상 경로 —
    # 동작 보존 검증이므로 실제 rerank 응답 형태로 단언한다.
    r3 = extract_json('{"ranking": [{"job_id": "j-1", "reason": "best fit"}]}')
    assert r3["ranking"][0]["job_id"] == "j-1"
