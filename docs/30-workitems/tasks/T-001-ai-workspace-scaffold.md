# T-001-ai-workspace-scaffold

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
Scorer/Collector/Eval 알고리즘을 담을 Python 실행 단위(`ai/core`·`ai/worker`·`ai/eval`·`crawler`)를 uv workspace로 scaffold한다. 이후 모든 알고리즘 이식 task의 토대 (ARCH §3-2 / STACK_SETUP_PLAN §0).

## 2. 작업 범위
- `ai/` uv workspace(`pyproject.toml`) + 멤버 패키지 `ai/core`·`ai/worker`·`ai/eval`, 그리고 `crawler`(workspace 멤버, `ai/core` 의존).
- 공통 도구 설정: ruff(lint/format), pytest(+conftest), 패키지 `__init__`.
- `schema-contract` pytest 스텁(R6 가드 placeholder — 실제 컬럼 검증은 후속) + `ai/core` 빈 모듈 placeholder.

## 3. 구현 항목
- `ai/pyproject.toml` — uv workspace 선언(members: core, worker, eval; crawler 포함). Python 3.10+(3.11+ 권장).
- 패키지 디렉터리 `ai/core/`, `ai/worker/`, `ai/eval/`, `crawler/` + 각 `__init__.py` + 최소 `pyproject` 또는 workspace 멤버 설정.
- `ruff.toml`(또는 pyproject `[tool.ruff]`) + pytest 설정(`[tool.pytest.ini_options]`).
- `ai/tests/test_smoke.py` — 각 패키지 import 스모크.
- `ai/tests/test_schema_contract.py` — 스텁(현재는 skip/placeholder, Worker 의존 컬럼 검증은 DB 스키마 확정 후).
- 의존성 선언: pydantic>=2.5, python-dotenv, openai(worker), httpx·beautifulsoup4(crawler), pytest(dev), ruff(dev). (scipy/playwright 미포함 — SPEC §5·§9.)

## 4. 제외 항목
- 실제 알고리즘 코드(T-002~) · DB 마이그레이션(Prisma — `podo/apps/api`) · CI YAML.
- `podo/`(TS) scaffold — 본 task 비범위.

## 4-1. 변경 예정 파일/경로
<!-- 구현 시점 갱신. scaffolding이라 5개 초과 자연스러움. -->
- `ai/pyproject.toml`, `ai/core/`, `ai/worker/`, `ai/eval/`, `crawler/`, `ai/ruff.toml`, `ai/tests/`

## 5. 완료 조건
`uv sync`가 workspace를 설치하고 `uv run pytest`가 스모크 테스트를 발견·통과하며 네 패키지가 import된다.

## 6. Acceptance Criteria
- AC-1 [Given] clean checkout [When] `uv sync` 후 `uv run pytest` 실행 [Then] 스모크 테스트가 수집되고 통과한다(exit 0).
- AC-2 [Given] workspace 설치 [When] `import core`, `import worker`, `import eval`(또는 패키지명), `import crawler` [Then] 모두 ImportError 없이 로드된다.
- AC-3 [Given] `uv run ruff check .` [When] scaffold 코드에 대해 실행 [Then] lint 에러 0건.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/tests/test_smoke.py::test_AC_1_pytest_collects
- AC-2 → pytest::ai/tests/test_smoke.py::test_AC_2_packages_import
- AC-3 → (lint 게이트 — `uv run ruff check .`로 검증)

## 6-2. TDD opt-out
<!-- scaffold라 일부는 설정 파일이나, import 스모크는 테스트로 검증 가능 → TDD 적용. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-001-core-value](../features/F-001-core-value.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 실행 단위)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §1](../../20-system/SCORING_PIPELINE_SPEC.md)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-MONO uv workspace)

## 8. 메모
STACK_SETUP_PLAN §0 폴더 구조와 정합. `infra/`(docker-compose) · `podo/`(TS) scaffold는 별도.

## 9. 의존성
- depends_on: []
- write_set: ["ai/**", "crawler/**"]
- verifier: "uv run pytest ai/tests/test_smoke.py"
- (lockfile race: `ai/pyproject.toml`·`uv.lock` 생성 — 단독 wave 권장)
