# M2-service-wiring

## 0. Status
draft

## 1. 목적
M1이 "알고리즘 + 오프라인 평가"를 *함수/JSONB 계약 + pytest* 수준으로 이식·검증한 위에서, ARCH §3-2 폴리글랏 물리 배치를 **실체화**해 "수집 → worker 스코어링(캐시 기반 재현) → DB 저장 → API 서빙 → 근거 표시"가 **fresh clone의 로컬 환경에서 재현 가능하게 도는** 상태를 만든다. 새 알고리즘·새 아키텍처 계층은 도입하지 않는다 (architect ADR-006 self-check: 기존 단일-layer + §3-1/§3-2 경계 규칙으로 충분 — M2는 새 layer가 아니라 *물리 매핑 인스턴스화*). 결정론(GS-1)·grounding(GS-2) 게이트는 DB 영속 경로를 통과해도 보존된다. (Charter §6 / ADR-100 D1·D3)

> **명칭·범위 결정 (2026-06-06, 사용자 판단):** 점수 신호는 "합격가능성/합격확률"이 아니라 **"적합도 5단계 / 추천 적합도"**로 노출한다. compute_fit의 `fit_level` 1~5 + `FIT_LABELS`를 그대로 5단계로 렌더링하고, **합격확률·% ·별도 band calibration은 M2 비범위**(Charter §5 "절대 합격확률 % 보장은 비목표" 정합). cut-off 폭 튜닝은 실데이터 축적 후 후속.

## 2. 범위
M1 §3 "분해 범위 경계"가 *비범위로 선고지*한 4개 서비스 와이어링을 닫고, 그 전제인 `podo/` TS 모노레포를 scaffold한다. 알고리즘 본체는 [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) SSOT 불변 — 새 스코어링 로직 0.
- `podo/` 모노레포(Next.js web + NestJS api) scaffold + Docker Compose(Postgres + pgvector) + `.github/workflows` skeleton.
- 최소 DB 스키마(`job_postings` · `crawl_runs`/coverage · `ranking_runs(result JSONB)` · `resumes`) + 폴리글랏 schema-contract test **실가동**(현 `ai/tests/test_schema_contract.py` skipped placeholder 교체).
- worker 영속 read/write 어댑터(기존 `worker/cache.py`의 `CacheAdapter` seam 위) + 실행 진입점(`run_scoring`을 DB I/O로 연결, `__main__`).
- crawler `crawl-jobs` fetch→upsert→diff 영속 + 일일 cron(GitHub Actions). crawl(LLM無)/score(LLM有) 분리.
- NestJS가 worker 산출 `ranking_runs.result` JSONB를 pass-through 서빙.
- Feed + Coverage UI: 단일 중복제거 피드 + **적합도 5단계 배지**(fit_level 직결) + JD 인용 근거 펼침 + 커버리지 투명성 패널.
- worker 경계 하드닝(ADR-103 eval↔worker / ADR-104 shared-util) — M1 위생 부채(REV-M1-001/002/003/007) 회수.
- **이력서 주입:** config/seed **합성** 이력서(SPEC §9-4 USER_DOMAINS 방식). `resumes` 테이블은 두되 UI 업로드 흐름은 비범위.

> **스키마 결정(F-006에서 확정):** 최소 4테이블만. ARCH §3-2가 예시한 `matching_rows`/`pairwise` 별도 정규화 테이블은 JSONB 안에 이미 있으므로 도입하지 않는다(YAGNI) — worker read-의존면을 최소화해 R6 contract test 검사 표면을 좁힌다.

## 3. 포함되는 기능 (F-005 ~ F-011)
> 아래 F-NNN은 `/plan-workitem M2`가 정식 분해한다. 각 항목 끝 `[M1 §3 항목 N]`은 닫는 서비스-와이어링 경계, `=DISCOVERY F`는 상위 feature 매핑.
- **F-005 (monorepo-scaffold)** — `podo/apps/{web,api}` + Docker Compose(PG+pgvector) + CI workflow skeleton. *technical-enabler*, 임계경로 선행. (임계 task = api+Prisma+DB 먼저, web은 F-010까지 지연 가능.)
- **F-006 (db-schema-contract)** — Prisma DDL(=폴리글랏 계약 SSOT) 최소 4테이블 + Python schema-contract test 실측 교체(R6 가드 실가동). [M1 §3 항목1]
- **F-007 (worker-persistence)** — worker 영속 어댑터 + 실행 진입점. = DISCOVERY F4·F5·F6·F7. [항목1·2]
- **F-008 (collector-cron)** — crawler 영속 + `crawl-jobs` 일일 cron. = DISCOVERY F1·F3. [항목2]
- **F-009 (api-serving)** — NestJS JSONB pass-through. feed surface 백엔드. [항목3]
- **F-010 (feed-coverage-ui)** — Next.js 단일 피드 + 적합도 5단계 + 근거 펼침 + 커버리지 패널. = **DISCOVERY F2** + Charter §8 흐름. [항목4]
- **F-011 (worker-boundary-hardening)** — *refactor*. ADR-103/104 구현(eval public-only + `worker.grounding` 모듈 / `_json_util`·`_prompts`·`DOM_RANK` 중앙화). **scaffold 의존 0 → 즉시 병렬 착수**, F-007 전 완료 권장. M1 REV-M1-001/002/003/007 회수.

## 4. 제외되는 기능
- **공개 배포(Vercel) + auth + 멀티유저** — Charter §5 비목표. M2 done-line은 *로컬 E2E*.
- **UI 이력서 업로드 + 실 PII 영속/마스킹** — config/seed 합성 이력서로 대체.
- **합격확률 %·별도 band calibration** — 적합도 5단계(fit_level 직결)로 대체.
- **`matching_rows`/`pairwise` 별도 정규화 테이블** — JSONB 내 보존(YAGNI).
- **7개+ 다채널 풀커버리지** — 토스·당근 유지(Charter §5).
- **직군 분기 스코어링 모델** — A-7 의존, 단일 모델 유지. 직군 분리 *탭*(UI 필터, 모델 분기 아님)은 F-010 plan 시 결정.

## 5. 완료 기준 (graduation checklist)
> sprint contract: 외부 검증 가능한 "done" 기준 (ADR-014).
- [ ] 모든 task status: done
- [ ] 통합 validate Pass (ruff·mypy strict·pytest + Biome/Vitest + schema-contract green)
- [ ] **E2E Pass** — fresh clone → `docker compose up` + `prisma migrate dev` + seed 이력서 주입 + 단일 오케스트레이션 명령으로 crawl→score→feed 완주. **score는 `OPENAI_API_KEY` 없으면 fixture/캐시 경로로 대체(외부 LLM 호출 0 → CI 항상 재현 가능), 있으면 live score까지 수행**(첫 실행 후 `.cache/llm`에 박혀 이후 결정적). `localhost:3000` 피드에 토스·당근 공고가 **중복 제거**되어 적합도 5단계 배지 + 근거(JD 인용) 펼침 + 커버리지 패널("수집: 토스·당근 / 마지막 성공 시각")과 함께 렌더.
- [ ] AC 매핑 100% (validation report 기준)
- [ ] P0 severity finding 0건 (QA_FINDINGS의 M2 헤더 기준)
- [ ] (선택) **GS-1-through-DB:** 동일 (이력서, JD)를 DB 경로로 2회 채점 → 저장된 band/score/evidence 변동 0(캐시 hit). **schema-contract pytest가 갓 마이그레이션한 DB에서 green**(R6 실가동).

## 6. 관련 문서
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§3.1 시나리오, §4 G1~G4, §5 비목표, §8 흐름)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-1 결정론·grounding 경계, §3-2 폴리글랏 매핑·schema-contract, §7-1 API · §7-3 백엔드/cron · §7-4 프론트)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (§3 데이터 계약 → DB 스키마, §8 캐시 키 → 결정론-through-DB, §9-4 이력서 주입, §11 JSONB 산출)
- 선행 마일스톤: [M1-foundation](M1-foundation.md) (§3 분해 범위 경계 = M2 범위 정의)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) (D1 게이트 우선·D3 결정론 캐시) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (폴리글랏 스택·D-CONTRACT) · [ADR-103](../../90-decisions/project/ADR-103-eval-worker-boundary.md) (eval↔worker 경계 — F-011 집행) · [ADR-104](../../90-decisions/project/ADR-104-worker-shared-util-boundary.md) (worker shared-util 경계 — F-011 집행)

## 7. 열린 질문
- 5단계 band cut-off 폭(초기 보수적으로 넓게?) — 현재 fit_level 1:1 직결로 시작, 튜닝은 실데이터 후속 (Charter §10).
- 모델/프롬프트 버전 bump 시 기존 점수·캐시 마이그레이션 정책(SPEC §8-2 / F-001 §12) — M2 차단 아님이나 `ranking_runs`·캐시 키에 `model`/`prompt_version`/`scoring_mode`/`ranking_mode`/`cache_key_version` 버전 필드를 보유해 마이그레이션을 가능케 한다(F-006 plan 반영).
- 직군 분리 탭(UI 필터) M2 포함 여부 — F-010 plan 시 결정(A-7 의존, 모델 분기와 구분).
- "적합도 5단계" 명칭이 Charter §3.1/§4 "합격가능성 밴드" 표현과 divergence — DISCOVERY(SSOT)/Charter 용어 reconcile 후속(`/discover-product --update` 또는 `/bootstrap-project --apply`).

## 8. 회고 (stabilize 자동 채움)
- 목표 달성도: <정량/정성 1줄>
- scope creep 사례: <있으면 1줄, 없으면 "없음">
- 비목표(charter ## 5) 위반 사례: <있으면 1줄>
- 핵심 학습 3개 이내
