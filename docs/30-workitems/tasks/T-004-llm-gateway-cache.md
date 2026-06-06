# T-004-llm-gateway-cache

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
결정론 경계(GS-1)의 인프라인 LLM 게이트웨이(OpenAI, 구조화 출력 검증 + 1회 재시도)와 결정론 캐시 키(model+prompt+SCHEMA_VERSION)를 `ai/worker`에 이식한다. miss 시 temperature=0/seed/버전 핀 (SPEC §8 / ARCH §3-1·§7-3).

## 2. 작업 범위
- `JSON_SYSTEM` 시스템 프롬프트 + `call_text` + `call_structured(validate, cache_label)`(JSON 추출·validate·1회 재시도·캐시) — SPEC §8-1.
- OpenAI 파라미터 자동 적응(max_tokens↔max_completion_tokens, seed/temperature fallback) — 모델명 하드코딩 금지. provider는 OpenAI 핀(멀티-provider 추상화 버림).
- 캐시 키 `sha256(model + rendered_prompt + SCHEMA_VERSION)` + 네임스페이스 격리 + REFRESH 경로 — SPEC §8-2. 저장은 **Postgres worker 소유 테이블/JSONB**(파일 캐시 대체).

## 3. 구현 항목
- `ai/worker/src/worker/llm.py` — 게이트웨이(`call_text`/`call_structured`/`_extract_json`/재시도).
- `ai/worker/src/worker/cache.py` — `make_key`/get/put/네임스페이스/REFRESH + 저장 어댑터(Postgres JSONB; MVP는 worker 소유 테이블, ARCH §7-3). 캐시 키에 시간·랜덤·환경 값 혼입 금지(§3-1, /validate 1순위 점검).
- `ai/worker/src/worker/config.py` — `SCHEMA_VERSION`·`OPENAI_MODEL`·`PROMPT_VERSION`·`LLM_SEED`·도메인 토큰 env 로딩(STACK_SETUP_PLAN §4 env명). (경로: src-layout — ADR-102 D5)

## 4. 제외 항목
- 프롬프트 내용(T-005) · 캐시 무효화/마이그레이션 정책(F-001 §12 열린 질문, 후속) · Redis(YAGNI, ADR-101 D-DB).

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/llm.py`, `ai/worker/src/worker/cache.py`, `ai/worker/src/worker/config.py`, `ai/worker/tests/test_llm_cache.py` (impl: src-layout — ADR-102 D5; test: co-located — D1)

## 5. 완료 조건
구조화 호출이 JSON을 검증·재시도하고, 동일 입력에 동일 캐시 키가 나오며 hit이 재현되고, 실패 시 명확히 에러를 surface한다.

## 6. Acceptance Criteria
- AC-1 [Given] 잘못된 JSON을 1회 후 올바른 JSON을 주는 가짜 LLM [When] `call_structured` [Then] 1회 재시도 후 검증된 결과를 반환한다(2회 모두 실패 시 LLMError).
- AC-2 [Given] 동일 (model, rendered_prompt, SCHEMA_VERSION) [When] `make_key` 두 번 + put 후 get [Then] 키가 동일하고 저장값이 그대로 재현되며, SCHEMA_VERSION 변경 시 키가 달라진다(무효화).
- AC-3 [Given] LLM 호출이 계속 실패 [When] `call_structured` [Then] 가짜 결과를 만들지 않고 LLMError를 raise한다(상위에서 보류 처리 — FAC-5).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_llm_cache.py::test_AC_1_structured_retry_once
- AC-2 → pytest::ai/worker/tests/test_llm_cache.py::test_AC_2_cache_key_determinism
- AC-3 → pytest::ai/worker/tests/test_llm_cache.py::test_AC_3_failure_raises_not_fakes

## 6-2. TDD opt-out
<!-- TDD 적용 — LLM은 가짜(fake)로 주입해 결정적 테스트. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-001-core-value](../features/F-001-core-value.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-1 결정론 캐시 경계)
- Architecture-Iface: [ARCH ## 7-3](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §8](../../20-system/SCORING_PIPELINE_SPEC.md)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) (D3 결정론 캐시)

## 8. 메모
- 외부 SDK(OpenAI) 연동 — 구현 전 최신 공식문서 확인(researcher 위임 또는 /research-pack, ADR-040). 모델 지식 컷오프 보완.
- 캐시 저장소는 Postgres(ARCH §7-3). DB 미확정 단계면 인메모리/파일 어댑터로 시작하고 인터페이스만 고정.

### repair 결정 이력 (ADR-047 D7)
- repair-workitem 2026-06-05 P0 ruff-format/check/mypy: Adopt — `ruff format` 2파일 + `ruff check --fix`(I001) + impl E501 단축 + mypy bare `dict` 2건(`llm.py:94,100` → `dict[str, Any]`). 통합 `pnpm validate` green. 로직·테스트·레이아웃(co-located, ADR-102)은 무변경.
- repair-workitem 2026-06-05 P1 _openai_call unreachable except (발견): Adopt-modified — 동일 try의 2번째 `except BadRequestError`가 unreachable → `max_tokens→max_completion_tokens` 적응(§3 scope)이 사문화돼 있었음. 중첩 try로 정정해 두 적응 모두 도달. **단 `_openai_call`은 미테스트(AC는 fake LLM 주입) + 실 OpenAI SDK 동작·적응 순서 검증은 researcher follow-up(§8 메모 — 공식문서 확인, ADR-040). oracle gap 잔존.**

## 9. 의존성
- depends_on: [T-001]
- read_set: ["docs/20-system/SCORING_PIPELINE_SPEC.md", "docs/00-meta/STACK_SETUP_PLAN.md"]
- write_set: ["ai/worker/src/worker/llm.py", "ai/worker/src/worker/cache.py", "ai/worker/src/worker/config.py", "ai/worker/tests/test_llm_cache.py"]
- verifier: "uv run pytest ai/worker/tests/test_llm_cache.py"
