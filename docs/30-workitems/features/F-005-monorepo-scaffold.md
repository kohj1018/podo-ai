# F-005-monorepo-scaffold: podo TS 모노레포 + 로컬 인프라 scaffold

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 요약
M2 서비스 와이어링의 물리 기반을 세운다 — `podo/` TS 모노레포(Next.js web + NestJS api)를 Turborepo+pnpm으로 scaffold하고, 로컬 인프라(Docker Compose: Postgres+pgvector)와 `.github/workflows` skeleton을 둔다. 알고리즘·스키마·UI 로직은 비범위이며, *그것들이 올라설 골격*만 만든다. (ARCH §3-2 물리 배치표 인스턴스화)

## 2. 사용자 가치 (User Story) — Type=technical-enabler 이므로 기술적 근거
- **무엇/왜:** `podo/`가 아직 미존재(`ai/`·`crawler` Python만 있음) → DB·API·UI 전 체인이 착수 불가. M2 임계경로의 *유일한 선행 enabler*다. 순수 셋업이라 알고리즘 리스크 0 → 일정 조기 de-risk.
- **서비스하는 결정/가정:** ADR-101 D-MONO(Turborepo는 `podo/`만, `ai/`·`crawler`는 uv workspace 분리) · ARCH §3-2 실행단위 매핑표 · 가정 A-INFRA(MVP는 로컬 Docker Compose).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. `pnpm install` → `pnpm dev`로 web(:3000)·api(:3001) 동시 기동.
2. `docker compose up -d`로 Postgres+pgvector(:5432) 기동, `CREATE EXTENSION vector` 가용.
3. 통합 `validate`(Biome + Vitest placeholder + 기존 ruff/mypy/pytest)가 exit 0.
### Alternate path
1. `pnpm --filter web dev` / `pnpm --filter api dev`로 개별 기동.
### Fail path
1. 🟡 포트 충돌(3000/3001/5432 점유) → 명시적 에러로 안내(조용한 실패 금지).
2. 🟡 pgvector 미설치 이미지 → extension 생성 실패를 기동 단계에서 표면화.

## 4. 범위
- `podo/`: Turborepo + pnpm workspace, `podo/apps/web`(Next.js+TS+Tailwind, App Router skeleton), `podo/apps/api`(NestJS+TS skeleton), Biome 설정.
- `infra/docker-compose.yml`: Postgres+pgvector 서비스, `.env.example`(`DATABASE_URL` 등 이름만).
- `.github/workflows` skeleton: `deploy-api`·`deploy-worker`·`crawl-jobs`·`schema-contract` placeholder(no-op 또는 lint-only).
- 루트 통합 `validate` 명령에 TS(Biome/Vitest) 합류.

## 5. 비범위
- 실제 Prisma 스키마·마이그레이션(F-006).
- 실제 endpoint·UI 로직(F-009·F-010).
- Vercel 공개 배포 — M2 done-line은 *로컬 E2E*(Charter §5).
- 인증(미정, ARCH §7-1).

## 6. 요구사항
- 스택은 ARCH §7 / ADR-101 확정값대로(Next.js·NestJS·Turborepo·pnpm·Biome·Postgres+pgvector).
- `ai/`·`crawler`(uv workspace)는 turbo가 묶지 않는다(ADR-101 D-MONO) — 의도적 분리 유지.
- 포트: web `3000`, api `3001`, Postgres `5432`(ARCH §7-0 가정값, 충돌 시 조정).
- `.env`는 커밋 금지(`.env.example`만, AGENTS.md 민감파일 규율).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** `pnpm install` 후 단일 명령으로 web·api가 각각 기동되고 헬스 경로가 응답한다.
- **FAC-2:** `docker compose up -d`로 Postgres+pgvector가 기동되고 `CREATE EXTENSION vector`가 성공한다.
- **FAC-3:** 통합 `validate`가 TS(Biome + Vitest placeholder) 포함 exit 0이다.
- **FAC-4:** `.github/workflows`에 4개 skeleton workflow가 존재하고 YAML이 유효(CI lint pass)하다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 (web·api 기동) → T-018:AC-1
- FAC-2 (PG+pgvector 기동) → T-019:AC-1
- FAC-3 (통합 validate green) → T-018:AC-2
- FAC-4 (CI skeleton 유효) → T-019:AC-2

## 8. Non-functional Requirements
- 빌드 재현성: `pnpm install --frozen-lockfile`로 결정적 설치. 로컬/CI 동일 동작.
- 보안: secrets는 `.env`(gitignore)·GH secrets. 레포 커밋 금지.

## 8-1. UX 흐름 품질
(해당 없음 — 비-UI enabler. 사용자 노출 surface는 F-010.)

## 9. 엣지 케이스
- 포트 충돌(이미 점유) — 조정 가능하게 env로.
- pgvector 이미지 태그 선택(예: `pgvector/pgvector:pg16`) — extension 포함 이미지 확인.
- Windows/WSL Docker Desktop 경로·볼륨 마운트 차이.

## 10. 의존성
- **선행:** 없음(M2 첫 enabler — 임계경로 출발점).
- **블로킹:** F-006·F-009·F-010이 본 scaffold에 의존.

## 11. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§7 제약 — 스택)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 실행단위 매핑, §7 기술선택, §7-0 운영 기술 사실)
- ADR: [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-LANG·D-MONO·D-DEPLOY) · [ADR-039](../../90-decisions/boilerplate/ADR-039-workitem-type.md) (technical-enabler)

## 12. 열린 질문
- api 포트 3001 확정? (ARCH §7-0 제안값)
- pgvector Docker 이미지 선택(`pgvector/pgvector` vs `ankane/postgres`)?
- CI workflow를 M2에서 실제 동작까지 채울지, skeleton(placeholder)만 둘지 — 본 feature는 skeleton, 실동작은 F-008(crawl-jobs)·F-006(schema-contract)이 채움.
