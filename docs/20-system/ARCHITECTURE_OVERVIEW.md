# 아키텍처 개요

## 0. Status
draft

> 입력 SSOT: [PROJECT_CHARTER.md](../10-charter/PROJECT_CHARTER.md) (← [DISCOVERY.md](../10-charter/DISCOVERY.md)). **스택 확정 (ADR-101)** — §7 기술 선택 표 + §3-2 물리 배치 참조. 잔존 미정 축(인증·푸시 채널)만 미정 표기.

## 1. 기술 요약
채용공고 수집 → 결정론적 LLM 스코어링 → 추천 피드로 이어지는 3단 파이프라인 SaaS. 핵심 비기능 제약은 **점수 재현성(GS-1)** 과 **근거 사실성(GS-2)** 이며, 이 두 게이트가 아키텍처의 1차 설계 동인이다. 구체 런타임·프레임워크·DB·배포는 **미정** (제약: Charter §7).

## 2. 시스템 경계
> C4 System Context 레벨.

**시스템이 다루는 것:**
- 토스·당근 공식 채용 페이지에서 공고/JD 주기 수집 (MVP 커버리지 2곳).
- 일자별 신규/마감 diff 감지.
- (이력서, JD) 쌍에 대한 결정론적 fit/합격가능성 스코어링 + JD 인용 근거.
- 수집 공고의 상대 랭킹 피드 + 커버리지 투명성 패널.

**시스템이 다루지 않는 것 (외부 경계):**
- 채용 공고의 *원천* — 외부 사이트가 SSOT. 본 시스템은 사본 캐시만 보유.
- 실제 지원 행위 — 원본 채널로 링크 이동(자동지원 비범위, Charter §5).
- LLM 추론 자체 — 외부 LLM 제공자에 위임. 본 시스템은 입력 구성 + 출력 캐시·검증을 책임.
- 이력서 원본 작성/첨삭 (비범위).

**신뢰 경계:** 외부 사이트(비신뢰 입력, ToS·구조변경 리스크) / LLM 제공자(비결정 출력원) / 사용자 이력서(민감 PII). 입력 검증·에러 핸들링은 이 세 경계에만 둔다 (AGENTS.md 단순성 규율).

## 3. 상위 아키텍처
> C4 Container 레벨. *논리 모듈* 기준으로 적는다. 물리 배치(실행 단위 매핑)는 §3-2에 스택 확정(ADR-101) 기준으로 채워졌다.

논리 모듈 3개 + 공유 데이터 저장:

1. **Collector (수집)** — 토스·당근 fetch → 정규화 → 공고 저장 → 일자 diff. 외부 사이트 변경·차단에 가장 취약. (F1·F2·F3)
2. **Scorer (스코어링)** — (이력서, JD) → 결정론 캐시 조회 → miss 시 LLM 호출(temperature=0/seed 고정/버전 핀) → JD 근거 추출 → 점수·랭킹 산출 → 캐시 저장. **결정론 경계의 소유자.** (F4·F5·F6·F7)
3. **Feed (피드)** — 저장된 공고 + 점수를 사용자에게 노출. 단일 피드, 커버리지 패널, 5단계 밴드, 직군 분리 탭, 지원 기록. (UI — 스택 확정 시 surface 결정)

데이터 흐름은 단방향: `Collector → (저장) → Scorer → (저장) → Feed`. Feed는 Collector/Scorer를 직접 호출하지 않고 저장된 결과만 읽는다.

## 3-1. 레이어 경계 + 의존성 규칙
> **self-check (ADR-006):** 프로젝트 규모가 4-layer Clean Architecture(Domain/UseCase/Adapter/Framework)를 정당화하는가? → **아니다.** 단일 개발자 MVP, 모듈 3개(Collector/Scorer/Feed) 규모. 따라서 **단일 layer + 모듈 단위 의존성 규칙**을 채택한다 (ADR-006 단순성 1순위). 다만 모듈이 3개(Collector/Scorer/Feed)로 분리되고, 그중 **Scorer의 결정론 경계는 GS-1 게이트의 구조적 전제**라 아래 한 가지 의존성 규칙만 명시적으로 못 박는다.

**모듈 의존성 규칙 (drift 시 ADR로 변경):**
- 세 모듈은 *데이터 저장*을 통해서만 통신한다. `Feed → Collector` / `Feed → Scorer` 직접 호출 금지 (저장된 결과만 읽음).
- **Scorer 결정론 경계 규칙 (게이트 핵심):** 캐시 키에 영향을 주는 모든 입력(이력서 정규화본·JD 정규화본·모델 ID·프롬프트 버전·파라미터)은 *명시적이고 직렬화 가능*해야 한다. 캐시 키에 시간·랜덤·환경 의존 값을 섞지 않는다 (A-12 / GS-1). 이 규칙 위반은 곧 게이트 붕괴이므로 코드 리뷰·validate에서 1순위 점검.
- **근거 grounding 규칙 (게이트 핵심):** Scorer가 산출하는 모든 근거 문장은 JD 원문 span에 매핑되어야 한다. JD에 없는 요구를 근거로 생성하는 경로 금지 (GS-2).

```
  [외부 사이트]              [외부 LLM 제공자]
       │ fetch                     │ infer (cache miss only)
       ▼                           ▼
   ┌─────────┐   저장   ┌─────────┐   저장   ┌────────┐
   │Collector│ ───────▶ │ Scorer  │ ───────▶ │  Feed  │ ──▶ 사용자
   └─────────┘  (공고)  └─────────┘ (점수·근거) └────────┘
                          ▲ 결정론 캐시 경계 (GS-1)
                          └ JD grounding 경계 (GS-2)
```

> 위반 예시: `Feed`가 점수를 즉석 재계산하려 `Scorer`의 LLM 경로를 직접 호출 → 캐시 우회로 GS-1 변동 발생 (violation). `Collector`가 fetch한 원문을 Scorer 캐시 키에 정규화 없이 그대로 사용 → 사이트 사소 변경으로 캐시 무효화 폭증 (violation).
>
> `/stabilize-milestone`이 모듈 수 ≥3을 확인하면 본 섹션 갱신을 권장한다.

## 3-2. 물리 배치 + 폴리글랏 계약 경계 (스택 확정)
> `/bootstrap-stack`이 채움 (스택 SSOT: [ADR-101](../90-decisions/project/ADR-101-stack-selection.md)). §3-1의 *논리 모듈*(Collector/Scorer/Feed)을 *실행 단위*에 매핑한다. 폴리글랏(TS+Python) 경계는 새 리스크면(R6)을 만들므로 계약 규율을 여기에 못 박는다.

**실행 단위 ↔ 논리 모듈 매핑:**

| 실행 단위 | 런타임 | 담당 논리 모듈 | DB 접근 |
|----------|--------|--------------|---------|
| `podo/apps/web` (Next.js → Vercel) | TS | **Feed** UI surface | 없음 (api 경유) |
| `podo/apps/api` (NestJS + Prisma) | TS | **Feed** 서빙 + user-facing CRUD | Prisma (스키마 SSOT) |
| `ai/worker` (Python + OpenAI SDK) | Python | **Scorer** (랭킹·fit·BT·domain tier·pgvector 검색) | raw SQL (소유 테이블 쓰기, 그 외 읽기) |
| `crawler` (Python httpx, 필요 시 Playwright) | Python | **Collector** | raw SQL (공고 upsert) |
| `ai/eval` (Python + pytest) | Python | Scorer 오프라인 평가 (GS-3 τ 프록시·GS-1 결정성 테스트) | read-only |

> Vercel 배포(web)는 사용자가 웹에서 직접 처리. api·worker·crawler는 GitHub Actions로 CI/CD (ADR-101). 인프라 실물 이전(LocalStack → AWS)은 *나중에* — MVP는 로컬 Docker Compose (가정 A-INFRA, §10).

**폴리글랏 계약 경계 규칙 (게이트 핵심 — drift 시 ADR로 변경):**
이 규칙들은 §3-1의 "Scorer 결정론·grounding 경계"를 *폴리글랏 환경으로 확장*한다. TS는 Prisma가 타입을 보장하지만 Python은 같은 DB를 손으로 읽으므로 **컴파일 타임 가드가 없다** — Prisma 마이그레이션이 워커 의존 컬럼을 바꾸면 런타임에 터진다. 세 규칙으로 막는다.

1. **테이블 소유권 분리 (write-owner 단일화):**
   - NestJS(api) 소유·쓰기: user-facing 테이블 (예: `users` / `resumes` / `user_events` / `billing`).
   - Worker 소유·쓰기: 분석 산출 테이블 (예: `ranking_runs` / `recommendations` / `matching_rows` / `pairwise` / `job_requirements` / `resume_evidence`).
   - Collector(crawler) 소유·쓰기: 공고 원천 (예: `job_postings`).
   - **서로의 소유 테이블은 읽기만 한다.** 한 테이블의 writer는 정확히 하나.
   - NestJS는 ranking·fit·score·domain tier·BT를 **계산하지 않는다** — Worker가 저장한 결과를 조회·서빙만 한다.

2. **스키마 SSOT = Prisma migration / 워커는 schema-contract test로 계약 검증:**
   - Prisma migration이 DB schema의 단일 원천(DDL 포함).
   - **pgvector는 "DDL은 Prisma, DML은 Python"**: vector 컬럼·`CREATE EXTENSION vector`·HNSW 인덱스는 **Prisma 마이그레이션의 raw SQL**에 넣어 스키마 단일 원천을 지킨다. vector *검색 쿼리*만 Worker에서 (Prisma의 vector 지원이 제한적 + 후보 JD 검색은 랭킹 파이프라인의 일부 → 경계 규율상 Worker 소속). 컬럼 소유권만 Prisma로 확실히 둔다.
   - **CI 스키마 계약 테스트** (R6 가드): 갓 마이그레이션한 DB에 붙어 Worker가 의존하는 컬럼·타입이 존재하는지 `pytest`로 확인 → PR에서 깨짐을 잡는다 (`schema-contract` workflow). 이게 폴리글랏의 *유일한* 컴파일-타임 대체 가드.

3. **워커 산출물은 좁고 안정적인 JSONB 계약면으로:**
   - 매칭표·비교결과 같은 알고리즘 *내부* 구조는 단일 JSONB 칼럼(예: `ranking_runs.result`)에 담는다. Prisma가 다른 테이블을 바꿔도 워커 계약이 안 흔들린다.
   - **NestJS는 그 JSONB를 파싱하지 않고 그대로 서빙**한다. 계약면이 작을수록 폴리글랏 비용이 0에 수렴 (R6 완화의 핵심 설계).

> 위반 예시: NestJS가 `ranking_runs`에 직접 write (소유권 위반 → 두 writer 경쟁). Worker가 vector 컬럼을 `ALTER TABLE`로 추가 (DDL은 Prisma 소유 위반 → 스키마 SSOT 붕괴). NestJS가 `ranking_runs.result` JSONB 내부를 파싱해 비즈니스 로직 분기 (계약면 확대 → Worker 변경마다 NestJS 깨짐).

## 4. 주요 도메인 모델
> 개념 수준. 세부 필드는 스택·DB 확정 후.

- **JobPosting (공고)** — 출처 채널, 회사, 직무, JD 원문, 마감일, 수집 시각, diff 상태(신규/유지/마감임박/마감). Collector 소유.
- **Resume (이력서)** — 사용자 보유 신호(스택·프로젝트·키워드·자격). 정규화본이 Scorer 캐시 키 입력. 민감 PII.
- **Score (점수)** — (Resume, JobPosting) 쌍에 대한 fit 점수·합격가능성 밴드·랭킹 위치. 캐시 키(모델/프롬프트 버전 포함)와 1:1.
- **Evidence (근거)** — Score를 뒷받침하는 JD 원문 span 인용 + 이력서↔JD 매핑 항목. GS-2 사실성 점검 단위.
- **CoverageState (커버리지)** — 현재 수집/미수집 채널 목록 + 마지막 성공 수집 시각. F2 투명성 패널의 데이터 소스, Fail #3 차단.

## 5. 데이터 흐름
1. **수집 흐름 (주기):** 스케줄 트리거 → Collector가 토스·당근 fetch → 정규화 → JobPosting upsert → 전일 대비 diff 계산 → CoverageState 갱신.
2. **스코어링 흐름:** (이력서, 공고집합) → 각 쌍 캐시 키 계산 → hit면 저장값 반환, miss면 LLM 호출(temp=0/seed/버전 핀) → JD span grounding 근거 추출 → Score·Evidence 저장.
3. **피드 흐름:** 사용자 진입 → 저장된 JobPosting + Score를 랭킹 정렬 → 5단계 밴드·커버리지 패널·직군 탭 렌더 → 근거 펼침 시 Evidence 노출.
4. **알림 흐름:** 수집 diff에 신규/마감임박 발생 → 오전 푸시("신규 N / 마감임박 M"). 실패 시 Fail #1 치명.

## 6. 외부 연동 지점
- **토스 채용 페이지 / 당근 채용 페이지** — Collector(crawler)가 **httpx 정적 fetch 우선**, 동적렌더링/anti-bot 시에만 Playwright headless로 승격. **A-1 검증됨(2026-06-04 — 크롤링 실증 동작 확인)** → 입력 확보. ToS 준수는 운영 상시 원칙(리스크 아님). 트리거는 GitHub Actions 매일 오전 cron.
- **LLM 제공자 — OpenAI (OpenAI SDK, Python Worker)** — 스코어링·근거 추출. 모델 ID·버전을 캐시 키에 핀(결정론 전제). 구체 모델 ID·temperature/seed 파라미터는 `## 7-3` 백엔드 결정 + ADR-101.
- **푸시 알림 채널 (미정)** — 오전 신규/마감 알림. 채널 구현은 MVP 후반 — 현재 미정 (§10).
- **데이터 저장 — PostgreSQL + pgvector (Docker Compose 로컬, 추후 AWS RDS 예정)** — 공고·이력서·점수·근거·vector embedding 영속. PII(이력서) 보관 → 보안 요구(§8). 스키마 SSOT는 Prisma.
- **오브젝트 스토리지 / 큐 — LocalStack S3·SQS (로컬), 추후 실제 AWS 이전** — 이전 시점은 *나중에* (가정 A-INFRA, §10).

## 7. 기술 선택
> **확정** (ADR-101). 상세 근거·대안·tradeoff는 [ADR-101](../90-decisions/project/ADR-101-stack-selection.md). 셋업 절차·명령·포트·env는 [STACK_SETUP_PLAN.md](../00-meta/STACK_SETUP_PLAN.md). 미해결 축은 미정으로 남긴다.

| 결정 축 | 선택 | 비고 (게이트 영향) |
|---------|------|-------------------|
| 언어 / 런타임 | TypeScript (web/api), Python (worker/crawler/eval) — 폴리글랏 | 폴리글랏 계약 경계는 §3-2. R6 신규 리스크면 |
| Monorepo orchestrator | Turborepo (pnpm) — `podo/`만. `ai/`·`crawler/`는 uv workspace | TS·Python을 단일 turbo가 안 묶음 (의도) — §3-2·ADR-101 D-MONO |
| 백엔드 프레임워크 | NestJS + TypeScript + Prisma | 서빙·user-facing CRUD만. ranking/score 미계산 (§3-2) |
| 프론트(UI) 프레임워크 | Next.js + TypeScript + Tailwind | Feed UI surface → `/bootstrap-design` 대상 |
| AI·랭킹 워커 | Python + Pydantic + OpenAI SDK | Scorer 결정론·grounding 경계 소유 (§3-1) |
| 데이터 저장 (DB) | PostgreSQL + pgvector (Docker Compose → 추후 AWS RDS) | 스키마 SSOT = Prisma. vector DDL=Prisma / DML=Python (§3-2) |
| 크롤링 방식 | httpx 정적 fetch 우선 → 필요 시 Playwright headless | A-1(동적렌더링/anti-bot) 결과에 따라 승격 |
| LLM 제공자 / 모델 | OpenAI (OpenAI SDK). 구체 모델 ID는 7-3 | 캐시 키에 버전 핀 — GS-1 직결 |
| 스코어 캐시 저장소 | Postgres (worker 소유 테이블 + 좁은 JSONB) | 결정론 경계 — GS-1 직결. 별도 Redis 미도입(YAGNI) |
| 패키지 매니저 | pnpm (TS) + uv (Python) | — |
| 테스트 | Vitest (TS unit) · Playwright (e2e) · pytest (Python) | schema-contract test도 pytest (§3-2) |
| Lint / format | Biome (TS) · ruff (Python) | — |
| 배포 / 스케줄러 | web: Vercel(사용자 직접). api/worker/crawler: GitHub Actions. cron: GitHub Actions(매일 오전) | 주기 수집·CI/CD 트리거 |
| 로컬 인프라 | Docker Compose (Postgres+pgvector, LocalStack S3/SQS) | 실물 AWS 이전은 *나중에* (A-INFRA) |
| 인증 | OAuth 소셜 로그인 (GitHub·Google) + httpOnly 쿠키 세션 | ADR-107 확정 — 멀티유저·`user_id` 데이터 격리(M4) |
| 푸시 알림 채널 | 미정 | MVP 후반 결정 — 미해결 |

### 7-0. 운영 기술 사실 (실행 명령·포트·env·디렉터리)
> Living Doc — fork 직후 곧장 검증되는 surface. 셋업 절차 전문은 [STACK_SETUP_PLAN.md](../00-meta/STACK_SETUP_PLAN.md). 통합 `validate` 명령·verify 스크립트는 `/stack-guard`가 생성(아직 미생성 — 아래는 *제안* 기준).

**실행 명령 (스택 자연 런타임 기준 — `/stack-guard` 전 제안값):**
- `podo/` (TS): `pnpm install` → `pnpm dev`(web+api turbo), `pnpm --filter web dev` / `pnpm --filter api dev`(개별), `pnpm test`(Vitest), `pnpm exec playwright test`(e2e), `pnpm exec biome check .`(lint).
- `ai/` (Python): `uv sync` → `uv run pytest`(worker+eval+schema-contract), `uv run ruff check .`(lint), `uv run python -m worker ...`(워커 실행 — 진입점은 구현 시).
- `crawler/` (Python): `uv run python -m crawler ...`(uv workspace 멤버, `ai/core` 공유).
- `infra/`: `docker compose up -d`(Postgres+pgvector, LocalStack S3/SQS).
- Prisma: `pnpm --filter api prisma migrate dev`(DDL SSOT — vector 컬럼·`CREATE EXTENSION vector`·HNSW는 raw SQL 마이그레이션, §3-2).
- 통합 검증: `validate`(이름 고정 — `/stack-guard`가 pnpm/uv 통합 1종으로 생성, GUARDRAILS).

**주요 포트 (개발 기준 — 가정값, 충돌 시 조정):**
- web(Next.js) `3000`, api(NestJS) `3001`(제안 — 구현 시 확정), Postgres `5432`, LocalStack `4566`.
- 스테이징/프로덕션 포트는 Vercel(web)·AWS 이전 시(api/worker) 결정 — *나중에*(A-INFRA).

**환경변수 이름 (값은 비움 — secrets는 `.env`, `.gitignore` 정합, AGENTS.md 민감파일 규율):**
- `DATABASE_URL`(Postgres+pgvector 연결 — Prisma·Worker·Crawler 공유), `OPENAI_API_KEY`(Worker), `OPENAI_MODEL`/`PROMPT_VERSION`(캐시 키 핀 — GS-1), `AWS_*`/`S3_ENDPOINT`(LocalStack → 추후 AWS), `NEXT_PUBLIC_API_BASE_URL`(web→api).
- 구체 목록·기본값은 STACK_SETUP_PLAN.md에서 관리. `.env`는 커밋 금지.

**주요 디렉터리 역할 (핵심):**
- `podo/apps/web` — Feed UI(Next.js→Vercel). `podo/apps/api` — 서빙+user-facing CRUD(NestJS+Prisma=스키마 SSOT).
- `ai/core` — Python 공유 모델·DB 접근(worker·eval·crawler 의존). `ai/worker` — Scorer(결정론·grounding 경계). `ai/eval` — 오프라인 게이트 측정(GS-1·GS-2·GS-3 τ).
- `crawler` — Collector(httpx). `infra` — docker-compose + aws/. `.github/workflows` — deploy-api·deploy-worker·crawl-jobs·schema-contract.

**known gotcha:**
- **폴리글랏 schema drift (R6)** — Prisma 마이그레이션이 Worker 의존 컬럼을 바꾸면 *컴파일 타임에 안 걸리고 런타임에 터진다*. `schema-contract` pytest가 PR에서 잡는 유일한 가드(§3-2). 마이그레이션 시 반드시 통과 확인.
- **vector 스키마 소유권** — Worker가 `ALTER TABLE`로 vector 컬럼 추가 금지(DDL은 Prisma 소유). 검색 쿼리(DML)만 Worker.
- **캐시 키 비결정 입력 혼입** — 시간·랜덤·환경 값이 캐시 키에 섞이면 GS-1 조용히 붕괴(§3-1). `/validate-workitem` 1순위 점검.

<a id="arch-7-1"></a>
## 7-1. API 컨벤션
> NestJS(`podo/apps/api`) ↔ Next.js(`podo/apps/web`) 계약. 런타임 결정은 [ADR-101](../90-decisions/project/ADR-101-stack-selection.md) D-LANG, JSONB pass-through 서빙은 D-CONTRACT 규칙3. API 컨벤션 자체의 SSOT는 본 절(ADR-027 — 인터페이스 컨벤션은 ARCH §7-X에 박음). 단일 사용자 MVP라 최소 컨벤션만 고정 — 과한 표준화는 YAGNI.

- **스타일:** REST/JSON. NestJS controller-service. RPC/GraphQL 미도입(YAGNI — 단일 클라이언트 web 1개).
- **경로:** `/api/v1/<resource>` 복수형 명사 (`/api/v1/postings`, `/api/v1/recommendations`). 버전 프리픽스 `v1` 고정 — breaking 시 `v2` 병행.
- **메서드/상태코드:** 표준 — 조회 GET / 생성 POST(201) / 갱신 PATCH / 삭제 DELETE(204). 클라이언트 오류 4xx, 서버 5xx.
- **에러 바디:** `{ error: { code: string, message: string } }` 단일 형태. NestJS exception filter로 통일. 시스템 경계(외부 입력)에서만 검증 — 내부 호출엔 두지 않음 (AGENTS.md 단순성).
- **입력 검증:** NestJS `ValidationPipe` + `class-validator` DTO. 검증 경계는 controller 진입점 한정.
- **워커 산출물 서빙 (§3-2 계약 핵심):** `ranking_runs.result` 등 JSONB는 **파싱 없이 pass-through**로 응답에 실어 보낸다. NestJS는 그 내부 구조를 알지 못한다 — 응답 DTO는 JSONB를 `unknown`/opaque로 취급.
- **인증:** OAuth 소셜 로그인(GitHub·Google) + httpOnly 쿠키 세션 (ADR-107, M4). 보호 라우트는 인증 가드 + `user_id` 범위 인가(본인 데이터만). 테스트/CI는 인증 우회 경로(ADR-107 D5).
- **페이지네이션:** 피드는 커서 기반 (단일 피드 무한 스크롤 §7-4 가상화와 정합). offset 기반 미사용(증분 수집으로 목록이 변하므로).

<a id="arch-7-3"></a>
## 7-3. 백엔드 결정
> 결정은 [ADR-101](../90-decisions/project/ADR-101-stack-selection.md) (D-DB·D-LLM·D-DEPLOY·D-CONTRACT). 본 프로젝트 고유 백엔드 관심사 = 결정론 캐시 키(GS-1)·주기 수집 스케줄러·JD grounding 검증. 셋업 명령·포트·env는 [STACK_SETUP_PLAN.md](../00-meta/STACK_SETUP_PLAN.md).

**런타임 분담 (서버측):**
- `podo/apps/api` (NestJS+Prisma, TS) — user-facing CRUD + Worker 산출물 서빙. **ranking·fit·score·BT·domain tier 미계산** (§3-2 계약). Prisma가 스키마 SSOT.
- `ai/worker` (Python+Pydantic+OpenAI SDK) — Scorer. 결정론 캐시 경계·JD grounding 경계 소유(§3-1). pgvector 검색(raw SQL DML).
- `crawler` (Python httpx) — Collector. `job_postings` upsert. GitHub Actions 매일 오전 cron 트리거.

**결정론 캐시 키 설계 (GS-1 직결 — Worker 책임):**
- 키 구성: `(이력서 정규화본, JD 정규화본, 모델 ID, 프롬프트 버전, 파라미터)` — 명시적·직렬화 가능. 시간·랜덤·환경 값 혼입 금지(§3-1 / ADR-100 D3).
- 저장: Postgres worker 소유 테이블 + 좁은 JSONB(`ranking_runs.result`). 별도 Redis 없음(ADR-101 D-DB, YAGNI).
- miss 경로: OpenAI 호출을 temperature=0/seed 고정 + 모델/프롬프트 버전 핀. 구체 모델 ID·파라미터는 *미정* — A-12 결정성 테스트 후 핀(§10 / 후속).
- 버전 변경 시 기존 캐시·점수 마이그레이션 정책 *미정*(§10 열린 질문 / F-001 §12).

**주기 수집 스케줄러:**
- GitHub Actions `crawl-jobs` workflow, 매일 오전 cron. 실패율·캡차율 로깅이 운영 1순위(§8 운영성 / A-1). 실패를 조용히 넘기지 않고 CoverageState에 노출(Fail #3 차단).

**JD grounding 검증 (GS-2 직결 — Worker 책임):**
- 모든 근거 문장은 JD 원문 span에 매핑. JD에 없는 요구 생성 경로 금지(§3-1 grounding 규칙).
- `ai/eval`(pytest)이 표본 ≥30에서 hallucinated requirement 비율 ≤2% 측정(GS-2 게이트).

**계약·검증:**
- 폴리글랏 schema-contract test(pytest, `schema-contract` workflow)가 Worker 의존 컬럼·타입 존재를 PR에서 검증(R6 유일 가드 — §3-2).
- 인증: **OAuth(GitHub·Google) + httpOnly 쿠키 세션 (ADR-107, M4)** — `user_id` 데이터 격리·횡단 접근 차단. 계정 PII는 ADR-105 Amend1(스코어링 경로 미유입).

<a id="arch-7-4"></a>
## 7-4. 프론트 결정
> 기술 결정은 [ADR-101](../90-decisions/project/ADR-101-stack-selection.md) (D-LANG·D-DEPLOY). **시각 결정(토큰·컴포넌트·레이아웃 미감)은 본 절이 아니라 `/bootstrap-design`이 [DESIGN.md](DESIGN.md)에 채운다** (ADR-027 — 인터페이스 결정 책임 분배). 본 절은 *구조·기술 축*만.

**런타임·배포:**
- `podo/apps/web` — Next.js + TypeScript + Tailwind. App Router 기준(스택 정합 — 세부 라우팅 구조는 구현 시).
- 배포 = Vercel(사용자가 웹에서 직접 처리, GitHub Actions 아님 — ADR-101 D-DEPLOY).
- API 접근: `podo/apps/api`(NestJS) 경유만. web은 DB 직접 접근 없음(§3-2 매핑표).

**본 프로젝트 고유 프론트 관심사 (구조 축 — 시각 디테일은 `/bootstrap-design`):**
- **단일 피드 가상화** — 통합 피드는 커서 기반 페이지네이션(§7-1) + 리스트 가상화. offset 미사용(증분 수집으로 목록이 변함 — §7-1).
- **5단계 합격가능성 밴드** — 색깔 밴드 표현. cut-off 경계는 *미정*(Charter §10 열린 질문) — 초기 보수적으로 넓게 잡을지 미결.
- **커버리지 투명성 패널** — 현재 수집/미수집 채널 + 마지막 성공 수집 시각 노출(CoverageState §4). Fail #3("거짓 완전성") 차단 — UI 필수 surface.
- **직군 분리 탭** — 백엔드/데이터 추천을 분리 탭으로(직군 미확정 페르소나 §2.1 / Charter §8 흐름 3).
- **점수 근거 펼침** — `ranking_runs.result` JSONB pass-through(§7-1)를 받아 JD 인용 + 이력서↔JD 매핑 렌더. web은 JSONB 내부 구조를 비즈니스 분기에 쓰지 않고 표시만.
- **보류 상태 표현** — LLM miss 실패 시 *가짜 점수 대신* 보류 표시("틀린 것보다 없는 게 낫다" — F-001 Fail #3 / §8-1).

> 위 항목의 *시각 구현*(밴드 색상 토큰, 패널 레이아웃, 탭 컴포넌트, 가상화 라이브러리 선택)은 `/bootstrap-design` R3·R4에서 결정. 본 절은 *무엇이 필요한가*만 박는다.

## 8. 품질 속성
> 본 프로젝트에서 *지배적인* 두 품질 속성은 신뢰성(점수 재현성)과 정확성(근거 사실성)이다 — 둘 다 출시 차단 게이트.

### 성능
- 수집은 주기 배치라 실시간성보다 *완결성*(누락 0)이 우선. 오전 알림 SLA는 "전날~새벽 신규를 오전 첫 진입 전 반영".
- 피드 진입 응답은 저장된 결과 읽기라 LLM 지연과 분리(스코어링은 사전 배치). 구체 목표는 스택 확정 후.

### 보안
- 이력서 = 민감 PII. 저장·전송 보호, 외부 LLM 전송 시 최소 필요 정보 원칙. 마스킹 정책 = [ADR-105](../90-decisions/project/ADR-105-pii-masking-policy.md)(M3 확정 — 직접 식별자 rule-based 마스킹, raw→외부 LLM 금지).
- 외부 사이트 ToS/robots 준수 — 운영 상시 의무(A-1 크롤링 실현성 검증됨 2026-06-04 — 리스크 해소; 준수 자체는 지속 원칙).

### 신뢰성 (지배 속성)
- **GS-1 재현성:** 동일 입력 → 동일 점수. 캐시 hit 변동 0, miss 재계산 top-k 순서 변동 0. 결정론 경계(§3-1)가 구조적 보증.
- 수집 실패·증분 실패는 치명(Fail #1·#2) — 실패를 *조용히* 넘기지 않고 커버리지 패널에 노출.

### 정확성 (지배 속성)
- **GS-2 근거 사실성:** hallucinated requirement ≤2%. JD span grounding 강제(§3-1 grounding 규칙).
- **GS-3 랭킹 타당도:** 출시 후 측정. 출시 전 Kendall τ 프록시로 sanity check(Charter §6).

### 운영성
- 수집 차단/구조변경 조기 감지(A-1) — fetch 실패율·캡차율 로깅이 운영 1순위.
- 캐시 무효화(모델/프롬프트 버전 변경 시) 추적 — 재현성 회귀 방지.

## 9. 리스크
- **R1 (최고) — A-3/GS-3:** LLM 상대 랭킹의 일관·정확성이 출시 전 검증 불가. 깨지면 F5·제품 차별화 붕괴. 완화: Kendall τ 프록시 + 결정론 캐시(GS-1).
- **R2 — A-1 (검증됨 2026-06-04 — 해소):** 토스·당근 크롤링이 anti-bot/동적렌더링 위에서 실제 동작함을 외부에서 직접 확인(차단·캡차 미관측). 파이프라인 입력 확보 → 리스크 해소. ToS 준수는 운영 상시 원칙.
- **R3 — A-12:** LLM 비결정성 위 캐시 결정론이 실제로 변동 0을 보장 못 할 수 있음(캐시 키 설계 결함). 완화: 명시적 직렬화 키 규칙(§3-1) + 100회 반복 결정성 테스트.
- **R4 — A-6:** self-proxy 일반화 실패 시 정확도 완벽해도 시장 부재. 완화: 외부 5~8인 인터뷰(코드 무관, 선행 가능).
- **R5 — 스택 선택 (확정, ADR-101):** GS-1(결정론 캐시 저장소=Postgres)·A-1(크롤링 방식) 기준으로 스택 확정. 잔존 리스크는 폴리글랏 schema drift(R6 — §3-2 schema-contract test로 완화)로 이동.

## 10. 열린 질문
- 크롤링을 정적 fetch로 충분히 처리할 수 있나, headless 브라우저가 필요한가? (A-1 검증됨 — 크롤링 동작 확인. 정적 httpx 우선 → 필요 시 Playwright 승격은 구현 시 확정, ADR-101 D-CRAWL)
- 결정론 캐시의 키 구성에 이력서 정규화를 어느 수준까지 포함할 것인가(과도 정규화 = 캐시 폭증, 과소 = 변동)? (A-12)
- 직군 미확정(백엔드/데이터)에서 단일 스코어링 모델 vs 직군 분기 — 아키텍처상 Scorer 분기 비용은? (Charter §10 / A-7)
- LLM 제공자/모델을 무엇으로 핀할 것이며, 버전 변경 시 기존 캐시·점수 마이그레이션 정책은? (GS-1)
- PII(이력서)를 외부 LLM에 보내는 범위·마스킹 정책은? (보안 §8) → **ADR-105 해소**(M3: rule-based regex 마스킹, 직접 식별자 5종, raw→외부 LLM 전송 금지; 간접 재식별 방어는 M4 연기)
