# F-021-jd-vectorization-and-cost: 후보 K개 사전필터로 비용 구조 전환 (N→K)

## 0. Status
draft

> **잠정 (M5).** A~D + 2 가드레일 확정(사용자 2026-06-07). **본 feature의 목표는 "새 알고리즘 추가"가 아니라 비용 구조를 *N개 전체 깊은 분석 → 후보 K개 깊은 분석*으로 바꾸는 것.** 구현 판단은 이 목표에 종속. 출력 계약(fit_level·evidence·recommendations·result shape)은 M4 동결.

## 0-1. Type
technical-enabler

## 2. 기술적 근거 (Technical rationale)
**무엇을:** 현 채점은 (코드 감사) 공고 N개에 대해 매칭(step4)+검증(step5)을 **2N회 LLM 호출**하고 listwise 프롬프트에 N개를 다 넣는다 → F-020으로 JD가 수백 개가 되면 비용·지연이 N에 비례해 폭증한다. 본 feature는 **벡터+하이브리드 후보 선별로 "깊게 볼" JD를 K개로 한정**해 비용을 N이 아니라 K에 비례시킨다.
**비용 레버에 필요한 최소만 도입:** JD 임베딩 영속 + 후보 사전필터(K-batch) + coarse/deep 분리 + (측정 후) 모델 티어링. **구조화 JD 정규화 테이블(`job_requirements`)은 만들지 않고**(YAGNI), 구조화 JD JSONB 영속도 **M5 미신설(raw_text 키워드 기반 — 현 schema에 `tech_stack` 컬럼 없음 확정), F-023 후 재검토**(ADR-108 D1 — 디스크 캐시는 SSOT 아님). **per-JD 단건 증분은 M5 필수 아님 — 후속**(ADR-108 D5).
**서비스하는 가정:** A-12(결정성 비용 보존)·GS-1. 상위: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md)(스코어링 비용 구조 — 벡터+하이브리드 후보 사전필터).

## 1. 요약
JD를 1회 임베딩해 **`job_embeddings`(vector)** 에 영속(재사용)하고, 채점 시 **resume↔JD 유사도 벡터검색 + 도메인/role_family + 스킬/키워드 매칭의 *합집합*(recall 우선)** 으로 후보 K개를 사전선별한다. **매칭·검증·compute_fit·listwise·pairwise는 K개에만** 돌려 비용을 N→K로 전환한다. 후보 밖 공고는 *coarse*(fit_level 없음, 유사도 정렬 힌트)로만 피드에 노출 — **임베딩 유사도·후보선별 점수는 적합도 5단계로 절대 표시하지 않는다.** 결정론(GS-1)·출력 계약은 불변(임베딩/후보선별 버전 캐시 키 핀).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 크롤로 새 JD → 1회 임베딩 → `job_embeddings` 영속(이후 채점은 재임베딩 없이 재사용).
2. 사용자 채점 → resume 임베딩 ↔ JD 임베딩 벡터검색 + 도메인 + 스킬 매칭 합집합 → 후보 K개(상한 K_max).
3. K개만 매칭·검증·compute_fit·listwise·pairwise → `recommendations`에 fit_level(deep).
4. 후보 밖 공고 → 피드 "아직 깊이 분석 안 한 공고" 섹션에 유사도 정렬로만(배지 없음).
### Alternate path
1. **M5 필수 경로 = 다음 채점 run의 K-batch로 새 JD 반영**(공고 추가돼도 batch 선별로 흡수). *per-JD 단건 즉시 증분 deep(그 JD만 매칭+fit, top 변동 시 LLM 재랭킹)은 후속 — M5 필수 아님(ADR-108 D5).*
2. 캐시 hit → 동일 입력 동일 결과(GS-1).
### Fail path
1. 🔴 임베딩/후보선별 버전 변경 → `cache_key_version` bump로 결정적 무효화(조용한 점수 변동 금지).
2. 🔴 후보선별이 적합 JD 누락 → 합집합(recall 우선) + F-023 "놓친 적합 JD" 회귀로 가드.

## 4. 범위
- **`job_embeddings` 테이블**(worker 소유, ARCH §3-2): job_posting_id FK + vector 컬럼(DDL=Prisma raw SQL + HNSW 인덱스, DML=Python 검색) + embedding_version. JD별 1회 임베딩·재사용.
- **resume 임베딩 영속**(`resume_embeddings` — masked content + version 키, 재사용; OpenAI 임베딩 호출 비결정성 차단 → GS-1, T-064 확정).
- **후보 선별(하이브리드 합집합)**: 벡터 top-K_v ∪ 도메인/role_family 매칭 ∪ 스킬/키워드 매칭 → 상한 K_max cap, 결정적 tie-break(유사도 desc, job_id asc).
- **매칭~랭킹을 후보 K개에만 한정** (기존 `run_scoring`을 후보 집합으로 호출 — 파이프라인 본체 불변, 입력 공고집합만 K로 축소). **= M5 필수 비용 레버.**
- **coarse/deep 분리**: deep만 `recommendations`(fit_level). **coarse 후보는 worker가 (채점 시 이미 계산한 유사도로) worker-소유 projection에 materialize**(job_id + 유사도 rank, **fit_level 없음**) → **api는 read-only 서빙**. vector 검색 DML은 worker 소속이라(ARCH §3-2/§7-3) **api/feed가 직접 vector 쿼리 수행 금지** — "피드 시 즉석 쿼리" 아님. coarse는 deep과 **별도 cursor·무배지**. ⚠ *ADR-108 D3의 "피드 시 즉석 쿼리" 문구도 worker-materialize로 정합 필요(repair-plan 범위 밖 — 메인세션 별도).*
- **(후속, M5 필수 아님) per-JD 증분 트리거**: 새 JD만 deep(결정적 fit_level 즉시) + top 변동 시 LLM 재랭킹. `run_scoring` 단건 refactor라 F-023 이후 후속(ADR-108 D5). M5는 새 JD를 다음 채점 run에서 K 후보로 반영하면 충분.
- **모델 티어링**(추출=저가/게이트=고가) — **F-023 측정 후** 적용(GS-2 미하락 확인 전 미적용).
- 캐시 키: 임베딩 모델·버전 + 후보선별 버전 + K를 `cache_key_version`에 반영.
- 피드 coarse 섹션 UI = **기존 JobCard를 FitScoreRing/PassBand(적합도 배지) 없이 재사용**(신규 컴포넌트 X) + 유사도순 목록 (DESIGN §7-3 CoarseSection 반영됨).

## 5. 비범위
- **구조화 JD 정규화 테이블(`job_requirements`)** — 미신설(YAGNI). JSONB 영속도 **M5 미신설(raw_text 기반), F-023 후 재검토**(ADR-108 D1 — 디스크 캐시는 SSOT 아님).
- **per-JD 단건 증분 deep scoring** — M5 필수 아님. 목표 구조이되 F-023 이후 후속 최적화(ADR-108 D5). M5 필수는 K-batch.
- **임베딩 유사도/후보선별 점수를 적합도 5단계로 표시** — 금지(Guardrail 1). fit_level은 deep 통과 공고에만.
- 출력 계약(fit_level·evidence·recommendations·result shape) 변경 — M4 동결.
- LLM 기반 후보선별/재순위 모델 신설 — 결정적 하이브리드만.
- 실 배포 인프라(공유 캐시·RDS) — M6(F-024/F-027).
- 커버리지 확대 자체 — F-020.

## 6. 요구사항
- 비용이 N(총 공고)이 아니라 K(후보)에 비례 — *실측*(보강 전/후 토큰·호출 수).
- **Guardrail 1 (하드):** coarse(유사도) 점수는 `recommendations`·fit_level·5단계 배지 어디에도 안 들어간다. fit_level은 matching/verify/compute_fit 통과 deep 공고 전용.
- **Guardrail 2 (recall 우선):** 후보선별은 벡터+도메인+스킬 *합집합*. 적합 JD 누락 최소화(F-023 측정).
- GS-1: 임베딩·후보선별 결정적 + 버전 핀. 동일 입력 동일 K·동일 결과.
- pgvector DDL=Prisma / DML=Python(ARCH §3-2). `run_scoring`/`recommendations`/복합 unique 구조 불변.

## 7. Feature-level Acceptance Criteria
- **FAC-1:** JD가 1회 임베딩되어 `job_embeddings`에 영속되고, 재채점 시 재임베딩 없이 재사용된다.
- **FAC-2:** 채점이 후보 K개(K_max 이하)에만 deep 분석을 수행해 LLM 매칭/검증 호출이 N이 아니라 K에 비례한다(비용 실측).
- **FAC-3:** 후보 밖 공고는 `recommendations`에 행이 없고 fit_level·적합도 배지가 부여되지 않으며, 피드 coarse 섹션에 유사도 정렬로만 노출된다(Guardrail 1).
- **FAC-4:** 후보 선별이 벡터+도메인+스킬 합집합으로 동작하고 동일 입력에 동일 후보 집합을 반환한다(결정적 tie-break, recall 우선).
- **FAC-5:** 동일 (이력서, 공고집합) 2회 채점 시 저장 결과 변동 0(GS-1 — 임베딩/후보선별/모델 버전 핀 포함).
- **FAC-6:** 새 JD가 수집되면 다음 채점 run의 K 후보 선별에 포함되어(진입 시) deep 분석된다. *(per-JD 단건 증분 deep은 M5 필수 아님 — 후속, ADR-108 D5.)*

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-064:AC-1, T-064:AC-2
- FAC-2 → T-065:AC-2, T-069:AC-1
- FAC-3 → T-065:AC-3
- FAC-4 → T-065:AC-1
- FAC-5 → T-065:AC-4
- FAC-6 → T-064:AC-1, T-065:AC-2

## 8. Non-functional Requirements
- 성능: 채점 지연·비용이 후보 K에 비례(총 공고 무관).
- 신뢰성: GS-1 결정론 보존(버전 핀). schema-contract(`job_embeddings`·vector).
- 비용: LLM 호출/토큰 절감 측정 가능(F-023 연동).

## 8-1. UX 흐름 품질
- **primary task:** (변화 없음) 상위 추천 스캔. coarse 섹션은 *부차*("더 보기").
- **empty/loading/error:** 기존 피드 상태(F-018) 재사용. coarse 섹션은 배지 없이 유사도순 목록.
- **copy 톤:** coarse 섹션은 "아직 깊이 안 본 공고예요 — 원하면 분석할게요"(포도) — *fit 점수처럼 보이지 않게*.
- **success metric:** Efficiency → 채점 LLM 비용/공고 ↓(보강 전후 비교).

## 9. 엣지 케이스
- 적합 JD가 K_max 미만 → 전수 deep(소규모 fallback).
- 영어 JD ↔ 한국어 이력서 → 임베딩 다국어(F-023 검증).
- 임베딩 모델 변경 → 전 JD 재임베딩 + 캐시 키 bump 마이그레이션.
- coarse 공고를 사용자가 "분석" 요청 → on-demand로 deep 승격(후보에 강제 포함).
- 합집합이 K_max 초과 → 유사도·도메인 우선 cap(결정적).

## 10. 의존성
- 신설: `job_embeddings`(Prisma DDL + Python DML). 교체 없음(파이프라인 본체 불변, 입력 공고집합만 K로).
- 연계: F-020(많아진 JD)·F-022(도메인 매칭이 후보선별 입력)·F-023(비용·recall·게이트 회귀)·F-018(coarse 섹션 UI).
- 상위: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md) · ARCH §3-2 pgvector 경계.

## 11. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-2 pgvector DDL/DML, §7-3 캐시 키)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (§7-4 후보집합 — 기존 fine-rank cap과 구분)
- Design: [DESIGN ## 7 Components](../../20-system/DESIGN.md#design-7-components) (coarse 섹션 — 배지 없음)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md) · [ADR-101](../../90-decisions/project/ADR-101-stack-selection.md) (D-DB)

## 12. 열린 질문 (확정값 — plan에서 미세조정)
- **임베딩 대상**: JD = 정규화 텍스트(title+role_family+requirements/skills 요약), resume = evidence 요약. (raw 전체보다 boilerplate 적어 매칭 품질↑.) 모델·차원·HNSW 파라미터는 plan에서 핀.
- **K**: recall 우선 — 초기 **K_v≈50 / K_max≈80**으로 넓게 시작 → F-023 recall·비용 측정 후 축소(예: 30/50). 누락 위험 먼저 보고 줄임.
- **저장**: `job_embeddings`(JD) + **`resume_embeddings`(resume 임베딩 영속 확정 — GS-1, T-064)**. **구조화 JD JSONB는 M5 미신설**(raw_text 키워드 — `tech_stack` 컬럼 없음 확정), F-023 후 재검토(ADR-108 D1).
- **재랭킹 트리거**: M5 필수=resume 채점 시 K 후보 deep batch 1회 / resume 교체=전체. per-JD 증분은 후속(ADR-108 D5).
- 모델 티어링은 F-023에서 GS-2 미하락 확인 *후* 적용.
