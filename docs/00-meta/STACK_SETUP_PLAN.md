# Stack Setup Plan

> 모드: Reference (스택 설정 절차 + 자동화 권장)
> 스택 SSOT: [ADR-101](../90-decisions/project/ADR-101-stack-selection.md). 아키텍처 매핑: [ARCHITECTURE_OVERVIEW §3-2·§7·§7-0](../20-system/ARCHITECTURE_OVERVIEW.md).
> 본 파일은 *셋업 절차·명령·포트·env*를 모은다. 통합 `validate`·verify 스크립트·CI는 `/stack-guard`가 생성(아직 미생성 — 아래는 제안값).

## 0. 폴더 구조 (확정 — ADR-101 D-MONO)
```
podo-ai/                # git repo 1개 · Python uv workspace 루트(pyproject.toml + uv.lock) — ADR-101#amend-1
  podo/                 # Turborepo(pnpm): apps/web(Next→Vercel) + apps/api(NestJS+Prisma=스키마 SSOT)
  ai/                   # uv workspace 멤버: core(공유 모델·DB) + worker + eval (루트 아님 — 멤버만)
  crawler/              # uv workspace 멤버: ai/core에 의존 (자체 도구 설정 없음 — 루트 공유)
  infra/                # docker-compose(Postgres+pgvector, LocalStack), aws/
  .github/workflows/    # deploy-api, deploy-worker, crawl-jobs, schema-contract
  docs/
```
> 위 트리는 아직 *코드 미생성* 상태(현재 repo에 `podo/`·`ai/`·`crawler/`·`infra/` 디렉터리 없음). 마이그레이션 task(`/plan-workitem M1`)에서 scaffold.

## 1. 외부 의존 부트업 (DB / S3·SQS, ADR-025)
**Postgres + pgvector (필수):** `infra/docker-compose.yml`로 로컬 기동 권장.
- 이미지: `pgvector/pgvector:pg16`(또는 동등) — `CREATE EXTENSION vector`는 Prisma raw SQL 마이그레이션이 수행(DDL SSOT, §3-2).
- 포트 `5432`. 연결 = `DATABASE_URL`(Prisma·Worker·Crawler 공유).

**LocalStack S3/SQS (로컬):** `infra/docker-compose.yml`에 함께.
- 포트 `4566`. `S3_ENDPOINT`/`AWS_*`로 접근. **실물 AWS 이전은 *나중에*** (가정 A-INFRA — MVP는 로컬 Docker로 충분).

채택 시: README에 "로컬 인프라 기동" 1단락 + 통합 진입점(`docker compose up -d` → `pnpm dev` / `uv run ...`)에 wiring. 상세는 `/stack-guard` 이후.

## 2. 셋업 명령 (스택 자연 런타임 — `/stack-guard` 전 제안값)
**TS (`podo/`):**
```
pnpm install
pnpm dev                              # web + api (turbo)
pnpm --filter web dev                 # web 개별 (Next.js, :3000)
pnpm --filter api dev                 # api 개별 (NestJS, :3001 제안)
pnpm --filter api prisma migrate dev  # DDL SSOT — vector 컬럼/extension/HNSW는 raw SQL 마이그레이션
pnpm test                             # Vitest (unit)
pnpm exec playwright test             # e2e
pnpm exec biome check .               # lint/format
```
**Python (`ai/`, `crawler/` — uv workspace):**
```
uv sync                               # workspace 전체 (core + worker + eval + crawler)
uv run pytest                         # worker + eval + schema-contract
uv run ruff check .                   # lint
```
**인프라:**
```
docker compose -f infra/docker-compose.yml up -d   # Postgres+pgvector, LocalStack
```
> 통합 검증 명령 이름은 `validate`로 고정 — `/stack-guard`가 pnpm/uv 통합 1종으로 생성.

## 3. 포트 (개발 — 가정값, 충돌 시 조정)
| 서비스 | 포트 | 비고 |
|--------|------|------|
| web (Next.js) | 3000 | Vercel 배포(사용자 직접) |
| api (NestJS) | 3001 | 제안 — 구현 시 확정 |
| Postgres+pgvector | 5432 | docker compose |
| LocalStack (S3/SQS) | 4566 | docker compose, 추후 AWS 이전 |

## 4. 환경변수 (값 비움 — secrets는 `.env`, `.gitignore` 정합)
| 이름 | 소비자 | 비고 |
|------|--------|------|
| `DATABASE_URL` | Prisma · Worker · Crawler | Postgres+pgvector 연결(공유) |
| `OPENAI_API_KEY` | Worker | LLM 스코어링 |
| `OPENAI_MODEL_ID` | Worker | 캐시 키 핀 — GS-1 (구체 ID 미정) |
| `PROMPT_VERSION` | Worker | 캐시 키 핀 — GS-1 |
| `S3_ENDPOINT` / `AWS_*` | Worker/Crawler | LocalStack → 추후 AWS |
| `NEXT_PUBLIC_API_BASE_URL` | web | web → api |
> `.env`는 커밋 금지(AGENTS.md 민감파일 규율). 구체 기본값은 scaffold 시 `.env.example`로.

## 5. 통합 명령 사용법
`/stack-guard`가 생성한 통합 검증 진입점 (`package.json` → `scripts/verify.mjs`):

```bash
# 전체 검증 (format → lint → typecheck → unit test)
pnpm validate

# 변경 파일만 검증 (incremental, finalize-workitem 직전 권장)
node scripts/verify.mjs --changed

# 전체 + e2e (stabilize-milestone 전용)
pnpm validate:e2e
```

**단계 순서** (스택별 verify 풀세트 기준):
| 단계 | TS (podo/) | Python (ai/ + crawler/) |
|------|-----------|------------------------|
| format | Biome | ruff format --check |
| lint | Biome | ruff check |
| typecheck | tsc --noEmit | mypy --strict |
| unit test | Vitest | pytest (schema-contract 포함) |
| e2e | Playwright (`validate:e2e`) | — |

> **Python 테스트 레이아웃 (ADR-102):** `ai/tests/`=워크스페이스/foundational(smoke·schema-contract·core 데이터 계약), `ai/<pkg>/tests/`·`crawler/tests/`=패키지별 behavior. test 디렉터리엔 `__init__.py` 두지 않고 pytest `--import-mode=importlib`(동일명 `tests` 충돌 회피, `testpaths=["ai","crawler"]` 재귀 수집). `mypy --strict`·ruff `E501`은 test 제외(구현 코드는 유지). 구현 모듈은 src-layout `ai/<pkg>/src/<pkg>/`.

> `podo/`(미생성) TS 단계는 skip하고 "missing" 경고 출력 — scaffold 후 자동 활성화(`ai/`·`crawler/`는 T-001~ 생성됨).

> 폴리글랏이라 verify 스크립트는 Node.js(cross-platform) 로 구현. `verify.sh`(Unix hook용)·`verify.ps1`(Windows hook용)은 `verify.mjs`에 위임하는 thin wrapper.

**필요한 devDependencies (사용자가 `podo/` scaffold 후 직접 설치):**
```bash
# podo/ 디렉터리 이동 후
pnpm add -D @biomejs/biome typescript vitest @playwright/test
```

## 6. CI 권장 (ADR-025 — `/stack-guard`가 형식 출력, 파일 자동 생성 X)
필요 워크플로우(ADR-101 D-MONO/D-DEPLOY):
- **`schema-contract`** (R6 가드, *최우선*) — 갓 마이그레이션한 DB에 pytest로 Worker 의존 컬럼·타입 검증. PR마다.
- **`validate`** — TS+Python lint/typecheck/test 통합. push/PR.
- **`deploy-api`** — `podo/apps/api` 배포(GitHub Actions).
- **`deploy-worker`** — `ai/worker` 배포(GitHub Actions).
- **`crawl-jobs`** — 매일 오전 cron 크롤링 트리거(httpx 정적 fetch 우선, 필요 시 Playwright headless 승격 — A-1).
> web(Vercel)은 사용자가 웹에서 직접 처리 — GitHub Actions 아님.

GUARDRAILS_STRATEGY *"OS/셸 종속 hook 강제 X"* 정신 — 위는 권장만. `/stack-guard`가 구체 YAML 출력.

## 7. PostToolUse hook 등록 (옵션 — 매뉴얼)
hook 자동 등록 정책·예시의 SSOT는 [GUARDRAILS_STRATEGY.md "## PostToolUse hook 매뉴얼 등록 절차"](GUARDRAILS_STRATEGY.md#postToolUse-hook-매뉴얼-등록-절차).

> PostToolUse hook 자동 등록은 현재 미구현. 매뉴얼 등록 절차는 위 SSOT 링크 참조.
> 폴리글랏이라 verify 스크립트 내부에서 변경 파일 확장자(`.ts`/`.py`)로 분기. `defaultMode: acceptEdits` 비용 주의 — 로컬 only.

**생성된 스크립트 경로 (hook 등록 시 사용):**
- Unix/macOS: `${CLAUDE_PROJECT_DIR}/scripts/verify.sh`
- Windows: `powershell -File ${CLAUDE_PROJECT_DIR}/scripts/verify.ps1`
- Cross-platform: `node ${CLAUDE_PROJECT_DIR}/scripts/verify.mjs`

## Optional MCP Connectors
<!-- 기본 자동 연결 X (ADR-043). RCE급 도구(예: Playwright browser_run_code_unsafe)는 신뢰 클라이언트 한정. secret은 .env(커밋 X).
     연결 절차(ADR-043 + ADR-048, 전용 skill 없음 — 1회성 셋업): (a) researcher(ADR-040)로 해당 능력의 최신 공식 MCP 설정 조회; (b) Claude(`claude mcp add <name> --scope project` 또는 `.mcp.json`) + Codex(`.codex/config.toml [mcp_servers.<name>]`) 설정을 *사용자가 직접 실행*; (c) project ADR(ADR-1NN)에 purpose/official docs/scope/read-only/secret/왜 기록 + project README 인덱스 갱신; (d) 아래 표에 행 추가;
     (e) 사용 강제 셋업 (ADR-048#d2): `lifecycle usage` 결정 + `agent access` 부여 — skill `allowed-tools`에 `mcp__<server>__*` 추가 + read-only MCP는 `.claude/settings(.local).json` `permissions.allow`에도 등재. 둘 다 안 하면 implement가 `Needs MCP Access`로 멈춤. -->
> 현재 `.codex/config.toml`에 `[mcp_servers.*]` 미설정 — backfill 대상 없음. 향후 MCP 연결 시 위 절차로 아래 표에 행 추가(자동 연결 X — 사용자 직접, ADR-043 보안).

| name | purpose | official docs | scope | read-only | secret | lifecycle usage | agent access | smoke check | last-verified |
|------|---------|---------------|-------|-----------|--------|-----------------|--------------|-------------|---------------|
| (없음) | - | - | - | - | - | - | - | - | - |
