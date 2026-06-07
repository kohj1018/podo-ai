# ADR-108 — 스코어링 비용 구조: 벡터+하이브리드 후보 사전필터 (N→K)

## Status
accepted

> **외부 리뷰 반영 (2026-06-07):** 방향·핵심 결정 유지. 문구·범위 보완 — D1(디스크 캐시는 SSOT 아님 → 구조화 JD JSONB 영속은 F-021 재검토), D3(coarse 별도 cursor·무배지 명시), D5(M5 필수=K-batch, per-JD 증분=후속), D6(임베딩 결정성=영속 벡터 재사용).

## Context
[관측됨 — 코드 감사 2026-06-07] 현 스코어링은 공고 N개에 대해 매칭(step4)+검증(step5)을 **2N회 LLM 호출**하고, listwise 프롬프트에 N개를 모두 넣으며(`job_set_hash`가 전체 공고로 키잉), pgvector는 extension만 설치되고 **컬럼·코드가 0**이다(`ai/`·`crawler` grep 0건). 즉 비용·지연이 공고 수 N에 선형 비례한다.

M5는 커버리지를 토스·당근 2곳 → 다수 공식 채용 페이지로 확대(F-020)하므로 N이 수백으로 커진다 → 현 구조로는 비용 폭증. **M5의 핵심은 "새 스코어링 알고리즘 추가"가 아니라 비용 구조를 *N개 전체 깊은 분석 → 후보 K개 깊은 분석*으로 바꾸는 것**이다(사용자 판단 2026-06-07). 본 ADR이 그 구조를 확정한다. 검증된 알고리즘 본체([SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md))는 SSOT 불변 — 본 결정은 *파이프라인 입력 공고집합을 K로 좁히는 상류 선별 단계*를 추가할 뿐이다.

## 결정

### D1. JD 임베딩 영속 (`job_embeddings`) — 정규화 테이블 미신설, 구조화 JD JSONB 영속은 F-021 재검토
- **`job_embeddings`** 테이블 신설(worker 소유 — ARCH §3-2): `job_posting_id` FK + `embedding`(vector) + `embedding_version`. JD별 **1회 임베딩 → 영속·재사용**. vector 컬럼·`CREATE EXTENSION vector`·HNSW 인덱스 **DDL은 Prisma raw SQL**, 검색 **DML은 Python worker**(ARCH §3-2 경계 — pgvector를 *실제로 사용*하게 된다).
- **`job_requirements` 같은 정규화 테이블은 만들지 않는다**(YAGNI, ADR-006).
- **단, 구조화 JD를 DB에 JSONB로 영속할지(예: `job_postings.structured_json` 또는 `job_embeddings`에 동봉)는 F-021에서 재검토한다 — "디스크 캐시에만 둔다"고 못 박지 않는다.** 디스크 LLM 캐시는 *실행 최적화*이지 제품 데이터의 SSOT가 아니다(삭제 가능·배포 시 인스턴스별 상이·CI/로컬/운영 경로 분기). 특히 **D2의 스킬/키워드 매칭(raw_text 기반 — tech_stack 컬럼 없음)이 구조화 JD 산출물을 *후보 선별 시점*에 요구할 수 있으며**(현재 구조화는 채점 시점 step2), JD 변경 감지·버전별 비교·디버깅도 구조화 JD를 필요로 할 수 있다 → F-021에서 *선별이 raw_text 키워드로 충분한지 vs 구조화 JSONB 영속이 필요한지* 결정.

### D2. 후보 선별 = 하이브리드 합집합 (recall 우선)
채점 시 후보를 다음 *합집합*으로 선별한다(교집합 아님 — recall 우선):
```
candidates = 벡터 top-K_v(resume↔JD 임베딩 유사도)
           ∪ 도메인/role_family 매칭(resume primary/secondary_domains ↔ JD role_family)
           ∪ 스킬/키워드 매칭(resume 스킬 ↔ JD raw_text 키워드 — 현 schema에 tech_stack 컬럼 없음)
```
- 상한 **K_max**로 cap, **결정적 tie-break**(유사도 desc, job_id asc).
- 잠정 기본값: **recall 우선이라 초기엔 넓게**(예: K_v≈50 / K_max≈80) 시작 → F-023 recall·비용 측정 후 축소(예: 30/50). *누락 위험을 먼저 보고 줄이는* 순서(처음부터 좁히면 놓친 적합 JD를 평가하기 어려움).
- 기존 `TOP_K_PAIRWISE=5`·`MAX_PAIRWISE_CANDIDATES=8`(pipeline.py)은 *후보 내부의 fine-rank cap*으로 **불변** — 본 K(상류 deep-analysis 예산)와 다른 층이다.

### D3. coarse/deep 물리 분리 (사용자 Guardrail 1 — 하드)
- **Deep**: 후보 K개만 매칭·검증·`compute_fit`·listwise·pairwise 통과 → `recommendations`에 `fit_level` 부여(status=scored|held). **출력 계약 불변(M4 동결).**
- **Coarse**: 후보 밖 공고는 **`fit_level`을 부여하지 않는다.** **worker가 (채점 시 계산한 유사도로) coarse 후보를 worker-소유 projection에 materialize**(job_id + 유사도 rank, fit_level 없음) → **api는 read-only로 서빙**한다. **vector 검색 DML은 worker 소속(ARCH §3-2/§7-3) — api/feed가 직접 vector 쿼리를 수행하지 않는다**(즉석 쿼리 아님). `recommendations`에는 행을 만들지 않고, *"아직 깊이 분석 안 한 공고"* 별도 섹션에만 노출한다.
- **임베딩 유사도·후보선별 점수는 "적합도 5단계"로 절대 표시하지 않는다** — DB(recommendations)·UI(배지) 양쪽에서 coarse와 deep을 분리한다. ("틀린 점수가 근거 없는 점수보다 치명" thesis 보호 — 깊이 분석 안 한 것에 fit 숫자를 붙이지 않는다.)
- **coarse 섹션은 deep 피드와 별도 pagination/cursor를 가진다** — coarse 결과는 `fit_level`·`rank_position`·추천 배지를 갖지 않는다(유사도 정렬만). 두 섹션의 정렬·커서가 분리되어 coarse가 deep 랭킹으로 오해되지 않는다.

### D4. 파이프라인 본체 불변 — 입력 공고집합만 K로
`run_scoring`(SPEC step1~12)은 그대로 두고, **입력 jobs를 후보 K개로 좁혀 호출**한다. 알고리즘(매칭·검증·compute_fit·BT·랭킹)·캐시 키·`ranking_runs` 복합 unique는 불변. 선별은 그 *앞단*의 새 단계다.

### D5. 증분 트리거 — M5 필수는 K-batch, per-JD 증분은 목표 구조(후속)
- **M5 필수 범위 = 후보 K개 batch scoring.** 비용 N→K 전환은 *이것만으로 달성*된다. 새 JD가 들어와도 다음 scoring run에서 K 후보로 반영하면 충분하다.
- **per-JD 증분 deep scoring**(새 JD 1개만 매칭+`compute_fit` → 피드 거친 위치 즉시 + LLM 재랭킹은 top 후보 ≤8 변동 시만)은 **목표 구조이되 M5 필수 아님**: 현 `run_scoring(resume, jobs)`는 후보 집합을 한 번에 받아 `ranking_runs.result`를 조립하므로 단건 증분은 별도 refactor다. **F-023(비용·recall 측정) 이후 후속 최적화로 허용**한다(강하게 박으면 위험 — 사용자 "비용 전환이 핵심, 새 알고리즘 추가 아님" 프레이밍 정합).
- resume 교체 → 전체 재채점(캐시가 (evidence, JD) 매칭 재사용).

### D6. 결정성 (GS-1) 보존
- **임베딩은 모델·버전·입력 해시로 키잉해 1회 생성 후 `job_embeddings`에 영속**한다. 재채점은 **저장된 벡터를 재사용**하며 외부 embedding API를 재호출하지 않는다 — GS-1 결정성은 "동일 입력 → 동일 벡터 *재생성*"이 아니라 *생성된 벡터의 영속·재사용*으로 보장한다(외부 API의 byte-identical 결정성에 의존하지 않음). 임베딩 모델·버전은 `cache_key_version`에 핀.
- 후보 선별 결과는 **결정적**(영속된 임베딩 + 결정적 tie-break job_id) — 동일 (resume, 공고집합, 버전) → 동일 K 후보 → 동일 deep 결과.
- 후보선별 버전·K도 캐시 키 버전에 반영(변경 시 결정적 무효화).

### D7. 모델 티어링은 측정 후
추출(저가)/게이트 직결 단계(고가) 모델 티어링은 **F-023에서 GS-2(근거 사실성 ≤2%) 미하락을 확인한 뒤** 적용한다(미확인 상태 선적용 금지).

## 근거
- **비용이 N이 아니라 K에 비례**: 공고가 1000개여도 deep 분석은 K개 고정 → 매칭/검증 LLM 호출 상한이 2K. M5 커버리지 확대(F-020)를 받아내는 유일한 구조적 레버.
- **recall 우선 합집합**: 벡터 단독은 표현이 다른 적합 JD를 놓칠 수 있다(예: 같은 직군 다른 용어). 도메인·스킬을 합쳐 누락 위험을 낮춘다 — F-023이 "놓친 적합 JD" 회귀로 측정.
- **coarse/deep 분리**: 깊이 분석 안 한 공고에 fit 숫자를 붙이면 "틀린 점수"(치명 fail)다. 유사도는 *정렬 힌트*일 뿐 적합도가 아니다 — DB·UI에서 물리적으로 분리해 혼동을 구조적으로 차단.
- **새 알고리즘 추가 아님**: 검증된 파이프라인 본체·캐시·출력 계약을 건드리지 않고 *입력 집합만* 좁힌다 — 위험·범위 최소(ADR-006 단순성, 사용자 프레이밍).
- **대안 비교**: ① *구조화 JD 정규화 테이블(`job_requirements`)* — 비용 레버 아님 → 미신설(YAGNI). 단 JSONB 영속 여부는 F-021 재검토(디스크 캐시는 SSOT 아님 — D1). ② *벡터 단독 후보선별* — recall 부족 → 하이브리드 채택. ③ *전 공고에 임베딩 유사도 기반 밴드 부여* — "틀린 점수" 위반 → coarse는 무배지.

## 결과
- pgvector가 실제로 사용된다(`job_embeddings` — DDL=Prisma, DML=Python). schema-contract test에 `job_embeddings`·vector 컬럼 추가.
- 피드에 coarse 섹션(무배지) 추가(F-018 피드 확장 — 출력 계약 불변이라 M4 동결과 충돌 없음).
- 채점 비용이 후보 K에 비례(F-023 실측).

## Surfaces
- [ARCHITECTURE_OVERVIEW §3-2](../../20-system/ARCHITECTURE_OVERVIEW.md) (pgvector DDL/DML 경계 — `job_embeddings`로 실체화 시 `per ADR-108`).
- [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (후보 사전필터 = 파이프라인 *상류* 단계 — 본체 불변; 필요 시 pre-stage 문서화).
- `ai/worker`(임베딩·후보선별), `podo/apps/api`·`web`(coarse 섹션 서빙·표시).

## 후속 작업
- **F-021 (jd-vectorization-and-cost)** 이 본 ADR을 구현한다.
- **F-023 (expanded-fit-validation)** 이 recall(놓친 적합 JD)·비용 절감·모델 티어링 GS-2를 측정한다(D7).
- 임베딩 모델·차원·HNSW 파라미터·K 최종값은 F-021 plan에서 핀.

## 관련 문서
- [M5-coverage-and-algorithm](../../30-workitems/milestones/M5-coverage-and-algorithm.md) (§1 비용 구조 전환, §2 벡터 사전필터)
- [F-021](../../30-workitems/features/F-021-jd-vectorization-and-cost.md) · [F-023](../../30-workitems/features/F-023-expanded-fit-validation.md) · [F-022](../../30-workitems/features/F-022-resume-domain-classification.md)(도메인 매칭이 후보선별 입력)
- [ARCHITECTURE_OVERVIEW §3-2](../../20-system/ARCHITECTURE_OVERVIEW.md) · [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md)
- [ADR-101](ADR-101-stack-selection.md) (D-DB pgvector) · [ADR-100](ADR-100-initial-project-decisions.md) (D1 게이트 우선 — coarse/deep 분리 근거)
