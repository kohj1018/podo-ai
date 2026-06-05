# T-001-ai-workspace-scaffold

## 0. Status
done

## 0-1. Type
technical-enabler

## 1. 작업 목적
Scorer/Collector/Eval 알고리즘을 담을 Python 실행 단위(`ai/core`·`ai/worker`·`ai/eval`·`crawler`)를 uv workspace로 scaffold한다. 이후 모든 알고리즘 이식 task의 토대 (ARCH §3-2 / STACK_SETUP_PLAN §0).

## 2. 작업 범위
- uv workspace(repo 최상위 `pyproject.toml` — ADR-101#amend-1) + 멤버 패키지 `ai/core`·`ai/worker`·`ai/eval`, 그리고 `crawler`(workspace 멤버, `ai/core` 의존).
- 공통 도구 설정: ruff(lint/format), pytest(+conftest), 패키지 `__init__`.
- `schema-contract` pytest 스텁(R6 가드 placeholder — 실제 컬럼 검증은 후속) + `ai/core` 빈 모듈 placeholder.

## 3. 구현 항목
- `pyproject.toml`(repo 최상위) — uv workspace **루트** 선언(members: `ai/core`, `ai/worker`, `ai/eval`, `crawler`). Python 3.11+. 공통 도구(`[tool.ruff]`·`[tool.pytest.ini_options]`·`[dependency-groups] dev`)·`uv.lock` 1회. (ADR-101#amend-1 — 루트가 `ai/`가 아니라 repo 최상위인 이유)
- 멤버 패키지 디렉터리 `ai/core/`, `ai/worker/`, `ai/eval/`, `crawler/` + 각 멤버 `pyproject.toml`(hatchling build) + `src/<pkg>/__init__.py` + `py.typed`(mypy strict).
- `ai/tests/test_smoke.py` — 각 패키지 import 스모크.
- `ai/tests/test_schema_contract.py` — 스텁(현재는 skip/placeholder, Worker 의존 컬럼 검증은 DB 스키마 확정 후).
- 의존성 선언: pydantic>=2.5, python-dotenv(core), openai(worker), httpx·beautifulsoup4(crawler), pytest·ruff·mypy(dev, 루트). (scipy/playwright 미포함 — SPEC §5·§9.)

## 4. 제외 항목
- 실제 알고리즘 코드(T-002~) · DB 마이그레이션(Prisma — `podo/apps/api`) · CI YAML.
- `podo/`(TS) scaffold — 본 task 비범위.

## 4-1. 변경 예정 파일/경로
<!-- 구현 시점 갱신. scaffolding이라 5개 초과 자연스러움. -->
- 구현: `pyproject.toml`(루트), `uv.lock`(루트), `.gitignore`(Python `.venv`·캐시 ignore 추가), `ai/core/`, `ai/worker/`, `ai/eval/`, `crawler/`(+각 멤버 `pyproject.toml`), `ai/tests/`
- arch-decision A 결정 기록(ADR-101#amend-1): `docs/90-decisions/project/ADR-101-stack-selection.md`, `docs/00-meta/STACK_SETUP_PLAN.md`

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

### repair 결정 이력 (ADR-047 D7)
- repair-workitem 2026-06-05 P0 §3-members/deps: Adopt — core/worker/eval/crawler에 member `pyproject.toml`+`src/<pkg>/__init__.py` 추가, dev(pytest,ruff)+런타임(pydantic,python-dotenv,openai,httpx,beautifulsoup4) 선언. `uv sync` 통과.
- repair-workitem 2026-06-05 P0 AC-1/AC-2/AC-3: Adopt — `ai/`에서 uv sync→`uv run pytest`(2 pass·1 skip, exit 0)·4 패키지 import·`uv run ruff check .` 통과. `ai/uv.lock` 생성.
- repair-workitem 2026-06-05 P0 crawler↔core: Adopt-modified — `../crawler`는 `ai/`-rooted 워크스페이스 멤버로 `core = {workspace=true}`를 못 찾음(uv 구조적 제약) → crawler가 core를 path source(`../ai/core`, editable)로 의존하도록 변경.
- repair-workitem 2026-06-05 P0 ruff-I001: Adopt-modified — crawler가 `ai/` 밖이라 ruff가 third-party로 오분류 → `[tool.ruff.lint.isort] known-first-party`로 4 패키지 묶어 해소.
- repair-workitem 2026-06-05 P0 integrated-validate(ROOT-cwd): Reject-context — `verify.mjs`가 `uv run`을 repo ROOT에서 실행하나 워크스페이스가 `ai/`-rooted라 uv가 프로젝트 미발견(ruff/pytest spawn 실패, exit 2). T-001 write_set `["ai/**","crawler/**"]` 밖 → 루트 `pyproject.toml` 신설 또는 `verify.mjs`를 `ai/` 기준 실행으로 수정 필요. **아키텍처 결정 escalate**(plan/ADR). T-001 자체 AC(1/2/3)는 `ai/` 워크스페이스에서 green.
- arch-decision 2026-06-05 (사용자 승인 **A**): uv workspace 루트를 repo 최상위로 이전([ADR-101#amend-1](../../90-decisions/project/ADR-101-stack-selection.md#adr-101-amend-1)). 위 integrated-validate Reject-context **해소** — crawler가 깨끗한 멤버가 되어 path-source 우회 제거(`core = {workspace=true}`), `verify.mjs`(ROOT cwd) 무수정 통과, `mypy --strict` 단계 활성화. write_set에 루트 `pyproject.toml`·`uv.lock` 추가(§9 갱신).

## 9. 의존성
- depends_on: []
- write_set: ["pyproject.toml", "uv.lock", "ai/**", "crawler/**"]
- verifier: "pnpm validate"
- (lockfile race: 루트 `pyproject.toml`·`uv.lock` 생성 — 단독 wave 권장)
