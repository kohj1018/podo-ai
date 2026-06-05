# ADR-101: 스택 선택 (폴리글랏 모노레포 — TS web/api + Python worker/crawler)

> scope: project
> area: infra

## Status
accepted

## 배경
> evidence label (ADR-022): 본 ADR의 근거는 혼합이다. 스택 선택 자체는 **[관측됨]** — 창업자가 별도 레포에서 fit 로직을 이미 고도화·실험한 결과 Python+OpenAI SDK가 검증됨(마이그레이션만 남음). 게이트 충족 가능성(GS-1 결정론·GS-2 grounding이 이 스택에서 실제로 달성되는가)은 **[가설]** — DISCOVERY §12 전 항목 미검증과 동일 상태. A-1(크롤링 안정성)·A-12(캐시 결정론)는 미검증.

ADR-100이 스택을 미정으로 남기고 `/bootstrap-stack`에 위임했다(ADR-100 후속 작업). 본 ADR은 그 스택을 확정한다. 선택 동인은 ADR-100과 동일하게 **"틀린 점수 > 근거 없는 점수"** thesis이며, 추가로 두 제약이 스택을 강하게 규정했다:

1. **기존 fit 로직 자산** — 창업자가 다른 레포에서 fit 적합도 로직을 Python으로 이미 고도화·실험했다. 본 프로젝트는 그 로직의 *마이그레이션*이 주이며, 재작성이 아니다. → Scorer 런타임은 Python으로 사실상 고정.
2. **pgvector 검색** — 후보 JD 검색은 vector 유사도 기반이고, 이는 랭킹 파이프라인의 일부다(경계 규율상 Scorer 소속). Prisma의 vector 지원이 제한적이라 raw SQL이 필요하다.

이 두 제약이 "Scorer는 Python, 그 외 user-facing은 TS"라는 폴리글랏 경계를 만든다. 폴리글랏은 새 리스크(R6 — 컴파일 타임 가드 부재)를 만들므로, 본 ADR은 스택 선택과 *동시에* 그 계약 규율을 못 박는다(상세는 ARCHITECTURE_OVERVIEW §3-2가 SSOT).

## 결정

### D-LANG. 폴리글랏 — TypeScript(web/api) + Python(worker/crawler/eval)
- **TypeScript**: `podo/apps/web`(Next.js → Vercel), `podo/apps/api`(NestJS + Prisma).
- **Python**: `ai/`(core·worker·eval), `crawler/`.
- 경계: user-facing CRUD·서빙·UI = TS / 랭킹·fit·BT·domain tier·pgvector 검색·크롤링 = Python.
- Scorer(Python)가 ARCHITECTURE_OVERVIEW §3-1의 결정론 캐시 경계·JD grounding 경계를 소유한다.

### D-MONO. Turborepo(pnpm)는 `podo/`만 — `ai/`·`crawler/`는 uv workspace로 분리
- TS 모노레포 orchestrator = **Turborepo + pnpm**, 범위는 `podo/`(apps/web + apps/api)에 한정.
- Python 멀티패키지 = **uv workspace**, 멤버 = `ai/core`(공유 모델·DB) + `ai/worker` + `ai/eval` + `crawler`(`ai/core`에 의존).
- **단일 turbo가 TS+Python을 통째로 묶지 않는다(의도된 결정).** 두 생태계의 의존성·캐시·태스크 그래프를 한 orchestrator로 강제하면 비용이 가치를 초과한다(ADR-006 단순성). git repo는 1개로 유지(폴리글랏 계약 테스트를 단일 PR에서 돌리기 위함 — schema-contract workflow).
- 폴더 구조:
  ```
  podo-ai/                # git repo 1개
    podo/                 # Turborepo(pnpm): apps/web(Next→Vercel) + apps/api(NestJS+Prisma=스키마 SSOT)
    ai/                   # Python(uv workspace): core(공유 모델·DB) + worker + eval
    crawler/              # Python: ai/core에 의존(uv workspace 멤버)
    infra/                # docker-compose(Postgres+pgvector, LocalStack), aws/
    .github/workflows/    # deploy-api, deploy-worker, crawl-jobs, schema-contract
    docs/
  ```

### D-DB. PostgreSQL + pgvector / 스키마 SSOT = Prisma / "DDL은 Prisma, DML은 Python"
- 저장소 = **PostgreSQL + pgvector**(MVP는 Docker Compose 로컬, 추후 AWS RDS).
- **Prisma migration이 DB schema의 단일 원천**(DDL 포함). vector 컬럼·`CREATE EXTENSION vector`·HNSW 인덱스는 Prisma 마이그레이션의 *raw SQL*에 넣는다.
- vector *검색 쿼리(DML)*만 Worker(Python)에서 raw SQL로. Worker는 vector 스키마를 *소유하지 않고* 사용만 한다.
- 스코어 캐시 저장소 = Postgres(worker 소유 테이블 + 좁은 JSONB). **별도 Redis 미도입**(YAGNI — 단일 사용자 MVP, 캐시는 영속이 더 중요).

### D-CONTRACT. 폴리글랏 계약 3규칙 (R6 가드) — SSOT는 ARCHITECTURE_OVERVIEW §3-2
TS는 Prisma가 타입을 보장하지만 Python은 같은 DB를 손으로 읽으므로 컴파일 타임 가드가 없다. 세 규칙으로 막는다:
1. **테이블 소유권 분리** — writer는 정확히 하나. NestJS=user-facing(`users`/`resumes`/`user_events`/`billing`) 쓰기, Worker=분석 산출(`ranking_runs`/`recommendations`/`matching_rows`/`pairwise`/`job_requirements`/`resume_evidence`) 쓰기, Crawler=`job_postings` 쓰기. 서로의 소유 테이블은 읽기만.
2. **CI 스키마 계약 테스트** — 갓 마이그레이션한 DB에 붙어 Worker 의존 컬럼·타입 존재를 `pytest`로 확인(`schema-contract` workflow). 폴리글랏의 *유일한* 컴파일-타임 대체 가드.
3. **좁고 안정적인 JSONB 계약면** — 알고리즘 내부 구조는 단일 JSONB 칼럼(`ranking_runs.result`)에 담고, NestJS는 파싱 없이 pass-through 서빙. 계약면이 작을수록 폴리글랏 비용이 0에 수렴.

### D-CRAWL. httpx 정적 fetch 우선 → 필요 시 Playwright headless 승격
- 크롤링은 **httpx 정적 fetch**를 기본으로, 동적렌더링/anti-bot이 관측될 때만(A-1 결과) Playwright headless로 승격.
- 트리거 = **GitHub Actions 매일 오전 cron**(`crawl-jobs` workflow).

### D-LLM. OpenAI(OpenAI SDK, Python Worker) — 모델 ID·프롬프트 버전을 캐시 키에 핀
- LLM 제공자 = **OpenAI**(OpenAI SDK, Python Worker). 구체 모델 ID는 ARCHITECTURE_OVERVIEW §7-3에서 핀.
- 모델 ID·프롬프트 버전을 캐시 키에 핀(ADR-100 D3 결정론 전제 — GS-1 직결).

### D-DEPLOY. web=Vercel(사용자 직접) / api·worker·crawler=GitHub Actions
- `podo/apps/web` → **Vercel**(사용자가 웹에서 직접 처리, GitHub Actions 아님).
- `podo/apps/api`·`ai/worker`·`crawler` → **GitHub Actions** CI/CD(`deploy-api`·`deploy-worker`·`crawl-jobs`).
- 로컬 인프라 = **Docker Compose**(Postgres+pgvector, LocalStack S3/SQS). 실물 AWS 이전은 *나중에*(가정 A-INFRA).

### D-TOOL. pnpm+Biome(TS) / uv+ruff+pytest(Python) / Vitest+Playwright+pytest(test)
- 패키지 매니저: **pnpm**(TS) + **uv**(Python).
- Lint/format: **Biome**(TS) + **ruff**(Python).
- 테스트: **Vitest**(TS unit) + **Playwright**(e2e) + **pytest**(Python — schema-contract 포함).
- 검증 데이터 모델: **Pydantic**(Python Worker 입출력 계약).

## 근거

**D-LANG (폴리글랏) 근거 / 대안:**
- 채택 이유: (1) fit 로직이 이미 Python으로 고도화됨 — 재작성은 검증된 자산 폐기(비합리). (2) pgvector raw SQL이 어차피 필요하고 검색은 랭킹 파이프라인 소속 → Python이 자연스러움. (3) user-facing 영역은 Next.js+NestJS 생태계 성숙도·타입 안정성이 우위.
- 대안 A — **all-TS**(스코어링도 TS로 재작성): 기각. 검증된 Python fit 로직을 버리는 비용 + LLM/데이터 생태계(numpy/scipy 류 랭킹·BT 계산)가 Python에 두꺼움. 단일 언어의 단순성 이득 < 재작성·생태계 손실.
- 대안 B — **all-Python**(web/api도 Python, 예: FastAPI + HTMX/React-별도): 기각. 단일 사용자 SaaS의 user-facing UX·타입 안정 CRUD는 Next.js+NestJS+Prisma 조합이 더 적합. Prisma의 마이그레이션·타입 생성이 스키마 SSOT를 깔끔히 보증.
- 잔여 비용: 폴리글랏 = 컴파일 타임 가드 부재(R6). D-CONTRACT 3규칙으로 완화하되 *비용이 0은 아님*을 명시.

**D-MONO (turbo는 podo/만) 근거 / 대안 (ADR-008#amend-1 monorepo 라운드):**
- orchestrator 결정: TS는 Turborepo+pnpm, Python은 uv workspace로 *분리*. 단일 orchestrator로 두 생태계를 묶는 도구(nx 폴리글랏 등)는 학습·설정 비용이 단일 개발자 MVP에 과도(ADR-006).
- shared 패키지: `ai/core`(Python 공유 모델·DB 접근)가 worker·eval·crawler에 의존성으로 제공. TS 쪽은 현재 `podo/apps/{web,api}` 2개라 shared 패키지 분리는 *아직* 없음(3회 반복 전 추출 금지 — 단순성).
- publish 정책: **internal-only**(외부 publish 없음). 단일 제품.
- scope vocabulary: `web` / `api`(TS), `core` / `worker` / `eval`(Python ai), `crawler`. 커밋 scope는 이 어휘 정합(ADR-008).
- 대안 — **단일 turbo가 Python까지**: 기각. turbo의 Python 태스크 통합은 정합성이 약하고, 두 락파일(pnpm-lock + uv.lock)·두 캐시를 한 그래프로 강제할 이득이 없음. git repo 1개 + 워크플로우 1세트면 폴리글랏 PR 정합은 충분.

**D-DB (Prisma SSOT + DDL/DML 분리) 근거 / 대안:**
- 채택 이유: 스키마 writer가 둘(Prisma + Python)이면 schema drift가 런타임에 터진다(R6). DDL을 Prisma로 단일화하면 vector 컬럼조차 Prisma가 소유 → 스키마 SSOT 보존. Python은 *읽기·검색만* 하므로 DDL 권한 불필요.
- 대안 A — **Python(Alembic 등)이 vector 스키마 소유**: 기각. 스키마 SSOT가 둘로 쪼개져 drift 추적 불가. Prisma가 모르는 컬럼이 생기면 user-facing 타입 보증도 깨짐.
- 대안 B — **Redis 캐시 추가**: 기각(YAGNI). 단일 사용자 MVP에서 캐시 핵심 요구는 *영속·결정론*이지 저지연이 아니다. Postgres JSONB가 결정론 캐시에 충분. 도입 시 ADR.
- 대안 C — **전용 vector DB(Pinecone/Qdrant 등)**: 기각. 별도 인프라·동기화 비용. pgvector가 단일 Postgres에서 스키마·트랜잭션 일관성을 공짜로 줌.

**D-CRAWL 근거:** httpx 정적 fetch가 가능하면 가장 단순·빠름·차단 위험 낮음. Playwright는 비용(브라우저 런타임)이라 *필요할 때만*(A-1 관측 후) 승격 — 추측성 선도입 금지(YAGNI).

**D-LLM 근거:** 기존 fit 실험이 OpenAI SDK 기반(관측됨). 모델/프롬프트 버전 핀은 ADR-100 D3 결정론의 전제라 캐시 키에 강제.

**D-DEPLOY 근거:** web은 Vercel이 Next.js 1급 지원 + 사용자가 직접 처리 선호. 나머지는 GitHub Actions로 통일해 CI/CD 표면을 단일화. 인프라 실물 이전(LocalStack→AWS)은 게이트 검증과 직교하므로 *나중에*(MVP는 로컬 Docker로 충분).

## 결과
- ARCHITECTURE_OVERVIEW §3-2(물리 배치 + 폴리글랏 계약), §7(기술 선택 표), §7-1(API 컨벤션), §7-3(백엔드 결정), §7-4(프론트 결정)가 본 ADR을 SSOT로 참조한다.
- **R6(폴리글랏 컴파일 타임 가드 부재)가 새 리스크면으로 추가**된다 — `schema-contract` workflow가 유일한 대체 가드. 이게 깨지면 워커 런타임이 조용히 터진다.
- 커밋 scope·테이블 소유권·DDL/DML 경계 위반은 `/validate-workitem`·코드 리뷰 점검 항목.
- 인증·푸시 알림 채널·구체 OpenAI 모델 ID는 *여전히 미정*(ARCHITECTURE_OVERVIEW §10 / §7 표) — 외부 노출 전 결정 필요.
- 다음: `/stack-guard`가 `schema-contract`·`validate` 스크립트·verify hook를 생성. `/plan-workitem M1`로 마이그레이션·셋업 task 분해.

## Surfaces
> 본 ADR의 스택·계약 결정이 동기 반영되는 파일 (fan-out SSOT — ADR-045#d3). 변경 시 함께 갱신.
- [ARCHITECTURE_OVERVIEW.md](../../20-system/ARCHITECTURE_OVERVIEW.md) — §3-2(물리 배치+계약), §7(기술 선택 표), §7-0(운영 기술 사실), §7-1(API 컨벤션), §7-3(백엔드), §7-4(프론트).
- [STACK_SETUP_PLAN.md](../../00-meta/STACK_SETUP_PLAN.md) — 셋업 절차·명령·포트·env·CI 워크플로우 목록.
- [project/README.md](README.md) — ADR 인덱스 행.

## 후속 작업
- `/stack-guard` — `validate` 통합 명령 + `scripts/verify.*` + `schema-contract` CI 권장 생성. 도구 감지로 pnpm/uv/Biome/ruff/pytest 보존.
- `/bootstrap-design` — `podo/apps/web`(Next.js) UI 시각 결정(ARCHITECTURE_OVERVIEW §7-4 시각 축).
- A-1(토스·당근 robots/ToS + 7일 fetch 로그)·A-12(100회 결정성 테스트) 선검증 — 크롤링 승격 여부·캐시 키 설계 확정.
- 구체 OpenAI 모델 ID·temperature/seed 파라미터를 §7-3에 핀(GS-1 직결).
- 인증·푸시 알림 채널 결정 시 별도 project ADR.

<a id="adr-101-amend-1"></a>
## Amendment 1 (2026-06-05) — uv workspace 루트 = repo 최상위 (T-001 실증 정정)
D-MONO는 uv workspace 멤버를 `ai/core`·`ai/worker`·`ai/eval`·`crawler`로 정의했다. `crawler/`는 `ai/`의 형제(repo 최상위 직속)이며 `ai/core`에 의존하므로, **uv 규칙상(멤버는 워크스페이스 루트의 하위여야 함) 이 4개를 한 워크스페이스로 묶는 유일한 방법은 루트를 둘의 공통 조상 = repo 최상위에 두는 것**이다. 따라서:
- uv workspace 루트 = **`podo-ai/pyproject.toml`**(repo 최상위). 멤버 = `ai/core`·`ai/worker`·`ai/eval`·`crawler`. `ai/`는 워크스페이스 루트가 아니라 멤버를 담는 폴더(별도 `ai/pyproject.toml` 없음).
- 공통 도구 설정(ruff·pytest·mypy·`uv.lock`)은 루트 `pyproject.toml`에 1회. crawler는 자체 도구 설정 없이 루트 설정을 공유(얇은 멤버 `pyproject.toml`만).
- `scripts/verify.mjs`(통합 validate)가 `uv run`을 repo 최상위 cwd에서 실행하는 설계와 정합 — 루트에서 워크스페이스를 발견, `mypy --strict ai/ crawler/`까지 활성화.
- **정정 근거(실증):** T-001 §3가 "`ai/pyproject.toml` = 워크스페이스 선언"이라 기술했으나 `../crawler`를 `ai/`-rooted 워크스페이스 멤버로 두면 uv가 crawler의 `core = {workspace=true}`를 해결하지 못해 빌드 실패(2026-06-05 `uv sync` 실패로 관측). T-001 §3/§4-1/§9를 루트 워크스페이스로 정정.

### 적용 surface
- [STACK_SETUP_PLAN.md](../../00-meta/STACK_SETUP_PLAN.md) §0 — 폴더 트리(워크스페이스 루트 = repo 최상위).
- [T-001](../../30-workitems/tasks/T-001-ai-workspace-scaffold.md) §3·§4-1·§9 — 루트 `pyproject.toml`.
- `podo-ai/pyproject.toml`(신규 — 워크스페이스 루트), `crawler/pyproject.toml`(`core = {workspace=true}`).

<!-- 관련: ADR-100(초기 결정 — 본 ADR이 그 후속 작업), ARCHITECTURE_OVERVIEW §3-2·§7·§7-1·§7-3·§7-4, STACK_SETUP_PLAN.md(셋업 절차).
     정책 근거: ADR-006(단순성), ADR-008#amend-1(monorepo 라운드), ADR-022(evidence label), ADR-025(외부 의존 부트업), ADR-031(직접지원 5유형 — web/API/monorepo 정합). -->
