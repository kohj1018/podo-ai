# ADR-102: Python 테스트 레이아웃 + 검증 설정 컨벤션

> scope: project
> area: tooling

## Status
accepted

## 배경
> evidence label (ADR-022): **[외부실증]** — T-002·T-003 `/validate-workitem`에서 동일 결함이 *2회 연속* 관측됨(2026-06-05). 근본 원인은 plan 의도와 루트 config의 불일치.

T-001이 `ai/tests/`(중앙) + `testpaths=["ai/tests"]`로 워크스페이스를 scaffold했다. 그러나 M1의 후속 task plan **14개 전부**(T-004~T-017)가 일관되게 **co-located** 테스트(`ai/<pkg>/tests/`·`crawler/tests/`)를 지정한다 — 즉 plan 작성자의 의도는 명확히 co-located다. 중앙 단일 dir만 지원하는 루트 config와 충돌해 다음이 반복 발생했다:

1. **mypy `Duplicate module "tests"`** — `ai/tests/`와 `ai/<pkg>/tests/`가 같은 top-level `tests` 모듈로 충돌(`__init__.py` 보유 시).
2. **전체 `pnpm validate`가 co-located 테스트 미수집** — `testpaths=["ai/tests"]`가 `ai/<pkg>/tests/`를 못 봄.
3. **test 픽스처의 mypy --strict 마찰** — 픽스처가 의도적으로 느슨한 입력(dict·bogus enum)을 넣어 coercion/validation을 검증하는데 strict가 `Model(**dict)`·Literal 불일치를 계속 잡음.
4. **test 한국어 docstring E501 반복** — 서술형 docstring이 88자 초과.

T-002 repair는 이를 *중앙화*로 회수했으나, 이는 14개 plan 의도를 거스르는 미봉책이었다. 본 ADR은 plan 의도(co-located)를 *정식 지원*하는 방향으로 컨벤션을 확정한다.

## 결정

### D1. 테스트 위치 — 2계층
- **`ai/tests/`** = 워크스페이스/cross-package/**foundational-contract** 테스트. 현재: `test_smoke`(패키지 import), `test_schema_contract`(R6 가드 stub), `test_models`(T-002 — 모든 단계가 의존하는 공유 데이터 계약 → foundational).
- **`ai/<pkg>/tests/`·`crawler/tests/`** = 해당 패키지 *behavior* 테스트. 예: `ai/worker/tests/test_compute_fit.py`(T-003~), `crawler/tests/`(T-012~), `ai/eval/tests/`(T-014~).

### D2. test 디렉터리에 `__init__.py` 없음 + pytest `--import-mode=importlib`
- test 디렉터리는 패키지가 아니다(`__init__.py` 두지 않음). pytest `importlib` 모드 + 고유 test 파일명(`test_<area>.py`)으로 동일명 `tests` 충돌을 원천 회피하고 재귀 수집한다.
- 루트 `pyproject.toml`: `testpaths=["ai","crawler"]`, `addopts="--import-mode=importlib"`.

### D3. `mypy --strict`는 test 제외 (`exclude=['(^|/)tests/']`)
- test 픽스처는 *의도적으로* 느슨한 입력을 넣어 런타임 coercion/validation을 검증한다 → strict 타입체크는 마찰만 키운다. **테스트 정합성은 pytest 실행으로 보증**한다. **구현 코드는 strict 유지**(타입 안전 가치 큼).

### D4. ruff — test는 `E501`(줄 길이)만 제외 (`per-file-ignores "**/tests/**" = ["E501"]`)
- 한국어 서술 docstring 가독성 > 줄 길이. **format·F(unused)·I(import 정렬)는 test에도 적용**. 구현 코드는 `E501` 유지.

### D5. 구현 파일·패키지 데이터는 src-layout `ai/<pkg>/src/<pkg>/` — task 문서도 이 경로를 *명시*한다
- T-001 scaffold가 src-layout(`packages=["src/<pkg>"]`)이므로 import 가능한 구현 모듈은 `ai/<pkg>/src/<pkg>/X.py`에 둔다(`from <pkg>.X import` resolve).
- **패키지 데이터(프롬프트·픽스처)도 src-layout 안에 둔다** — `ai/worker/src/worker/prompts/`, `ai/eval/src/eval/fixtures/`. 이유: hatchling이 `src/<pkg>/` 내용을 wheel에 포함 → deploy-worker가 프롬프트를 번들·패키지 상대 로딩. 밖에 두면 wheel 미포함으로 배포 시 깨짐.
- **task 문서(§3·§4-1·§9 write_set/read_set)는 이 src-layout 경로를 그대로 적는다.** finalize의 `## 4-1` guard가 *literal* 비교를 하므로 약기(`ai/<pkg>/X.py`)는 Needs Review를 유발한다(`--apply` 우회 가능하나 비권장). **test 경로만 예외** — D1대로 `ai/<pkg>/tests/`(co-located, src-layout 아님). §6-1 테스트 시나리오 경로도 그대로.
- 기존 plan(T-005~T-017)의 약기 경로는 본 ADR 확정과 함께 일괄 src-layout로 정정함(2026-06-05).

## 근거
- **plan 의도 존중:** 14개 task가 co-located를 일관 지정 — 중앙화는 plan 전면 재작성 + 의도 위배. co-located는 표준이며 패키지 수 증가에 확장적.
- **strict 완화 범위 최소화:** mypy/ruff 완화는 *test에 한정*, 구현 코드는 full strict. "검증된 알고리즘 이식 + 픽스처 테스트" 성격상 test의 over-strict는 비용>편익(ADR-006 단순성). 실행(pytest)이 1차 oracle.
- **대안 — 중앙 `ai/tests/` 강제:** 기각. 14 task plan 재작성 비용 + co-located 표준 이점 포기.
- **대안 — test도 mypy strict 유지:** 기각. 픽스처마다 `model_validate`/Literal-typed helper 강제 → task마다 반복 마찰(T-002에서 실측).

## 결과
- 루트 `pyproject.toml` 갱신: `[tool.pytest.ini_options]`(testpaths·import-mode), `[tool.mypy]`(exclude), `[tool.ruff.lint.per-file-ignores]`.
- `ai/tests/__init__.py`(T-001) 삭제 — D2 정합(importlib는 불필요). `ai/worker/tests/`는 `__init__.py` 없이 co-located.
- T-002 `test_models`는 `ai/tests/`에 잔존 — D1상 *foundational-contract*로 분류(정합, 이전 불필요).
- T-003~T-017 plan의 co-located test 경로는 **이미 본 컨벤션과 정합**(문서 변경 불필요). 구현 path 약기는 D5로 해소.
- 검증: `pnpm validate` exit 0 — pytest가 `ai/tests/`+`ai/worker/tests/` 모두 수집(11 collected), mypy 구현만 strict, ruff green.

## Surfaces
> 본 ADR이 동기 반영되는 파일. 변경 시 함께 갱신.
- [pyproject.toml](../../../pyproject.toml) — pytest·mypy·ruff 설정.
- [STACK_SETUP_PLAN.md](../../00-meta/STACK_SETUP_PLAN.md) §5 — 검증 단계·테스트 레이아웃.
- [project/README.md](README.md) — ADR 인덱스 행.

<!-- 관련: ADR-101(스택·src-layout uv workspace), ADR-009(TDD 디폴트), ADR-006(단순성), ADR-007(workitem lifecycle — validate 책임 경계). -->
