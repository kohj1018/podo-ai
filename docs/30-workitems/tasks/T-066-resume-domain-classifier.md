# T-066-resume-domain-classifier

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
`worker/persistence.load_resume`이 모든 업로드 이력서를 `primary=frontend/secondary=backend`로 하드코딩해 백엔드·데이터 이력서가 오정렬된다(T-037 §8 감사 확인). 본 task가 **evidence(`EvidenceItem.domain`) 집계 + 결정적 스킬→직군 규칙 사전**으로 도메인을 자동 분류하고 하드코딩을 제거한다. LLM 호출 0(이미 추출된 evidence 재사용), 결정적, 버전 핀(GS-1 정합 — ADR-108 D6 연장). T-067(직군 탭 UI)의 선행 enabler.

## 2. 작업 범위
- `ai/worker/src/worker/domain_classifier.py` — 신설. `classify_domains(evidence_items: list[EvidenceItem]) -> DomainResult(primary_domains: list[str], secondary_domains: list[str], confidence: str)`.
  - **Step 1**: `EvidenceItem.domain` 값 빈도 집계 → 최다 도메인 primary, 차다 secondary.
  - **Step 2**: 빈도 스킬 신호 빈약 시 결정적 규칙 사전 보강(값=기존 `ROLE_FAMILY_TO_DOMAINS` 토큰만, 새 어휘 X — §8 확정본):
    - frontend: react/next.js/vue/angular/svelte/tailwind/redux/webpack
    - backend: spring/django/fastapi/flask/express/nestjs/rails/laravel/grpc
    - data: pandas/numpy/spark/airflow/dbt/kafka/hadoop/bigquery/etl
    - ml_ai: pytorch/tensorflow/scikit-learn/hugging face/llm/nlp/mlops/keras
    - mobile: android·jetpack compose→android · swift·swiftui·uikit·objective-c→ios · flutter·react native→mobile
    - devops/cloud/infra: docker·kubernetes·terraform·ansible·ci/cd·jenkins·github actions·prometheus→devops · aws·gcp·azure→cloud · nginx·linux→infra
    - security: owasp/penetration testing/siem/cryptography
    - **다의어(python/java/typescript/go/sql)·kotlin 제외**(문맥 의존 → evidence.domain이 처리). `SKILL_DOMAIN_RULES: dict[str, str]` 상수로 버전 핀(`CLASSIFIER_VERSION`).
  - 다중 도메인(신호 혼재): `primary_domains`에 복수.
  - 신호 빈약(evidence 없음 or 규칙 미매칭): `confidence="low"` + `primary_domains=["unknown"]`.
  - `CLASSIFIER_VERSION = "v1"` 상수(변경 시 GS-1 무효화).
- `ai/worker/src/worker/persistence.py` — `load_resume` 하드코딩(`primary=frontend/secondary=backend`) 제거 → `classify_domains(resume.evidence_items)` 결과로 교체. `Resume.primary_domains`, `Resume.secondary_domains` 채움.
- **분류 결과 영속 계약(P0 — T-067 직군 탭 UI가 confidence/domains를 소비하려면 필요):** **worker 소유 `resume_domains` 테이블**(DDL=Prisma `podo/apps/api/prisma`, DML=Python worker — ARCH §3-2 분석 산출 테이블)에 `(resume_id INTEGER PK/FK→resumes(id)` [Resume.id=Int], `primary_domains text[], secondary_domains text[], confidence text, classifier_version text)`를 upsert. NestJS api(feed/resume)가 이를 **read-only** 서빙(직군 탭이 읽음). worker는 자기 소유 테이블만 write(단일 writer).
- 단위 테스트: 프론트엔드·백엔드·데이터 각 이력서 fixture로 분류 정확성 검증 + 영속/서빙 계약.

## 3. 구현 항목
1. `ai/worker/src/worker/domain_classifier.py` — 신설. `SKILL_DOMAIN_RULES: dict[str, str]` 상수(스킬→직군 매핑, 초기 목록 §2 참조). `CLASSIFIER_VERSION = "v1"`. `classify_domains(evidence_items) -> DomainResult`. → 확인: 단위 테스트 (AC-1, AC-4)
2. `ai/worker/src/worker/persistence.py` — 기존 `load_resume` 함수:
   - 현재: `resume.primary_domains = ["frontend"]; resume.secondary_domains = ["backend"]` 하드코딩 2줄.
   - 변경: `result = classify_domains(resume.evidence_items); resume.primary_domains = result.primary_domains; resume.secondary_domains = result.secondary_domains`.
   - → 확인: 기존 `test_persistence.py` 회귀 없음 + 신규 분류 테스트 (AC-1)
3. `ai/worker/tests/test_domain_classifier.py` — 신설. fixture:
   - `frontend_resume`: EvidenceItem.domain="frontend" 다수 + React/Next.js 스킬 → primary=["frontend"] assert.
   - `backend_resume`: EvidenceItem.domain="backend" 다수 + Spring/Django 스킬 → primary=["backend"] assert.
   - `data_resume`: EvidenceItem.domain="data" 다수 + pandas/ML 스킬 → primary=["data"] assert.
   - `fullstack_resume`: frontend+backend 동수 → primary_domains 길이 ≥2 또는 confidence="low" assert.
   - `empty_resume`: evidence 없음 → confidence="low" + primary_domains=["unknown"] assert.
   → 확인: pytest pass (AC-1, AC-4)
4. `ai/worker/tests/test_domain_classifier.py` — AC-4 결정성 테스트: 동일 fixture 2회 호출 → 동일 결과 assert.
5. **`resume_domains` 영속 계약(AC-5):** (a) `podo/apps/api/prisma/` migration — `resume_domains`(resume_id INTEGER PK/FK→resumes(id), primary_domains text[], secondary_domains text[], confidence text, classifier_version text); (b) worker `persistence.py`(또는 분류 단계)가 분류 결과를 `resume_domains` upsert(worker 소유 DML); (c) NestJS feed/resume 모듈이 `resume_domains` read-only 서빙(T-067 탭 소비); (d) `ai/tests/test_schema_contract.py`에 `resume_domains` 테이블 assert. → 확인: schema-contract green + api 응답에 domains/confidence 포함. (AC-5)

## 4. 제외 항목
- LLM 기반 도메인 분류기 신설 — 비범위(F-022 §5 확정).
- 직군 분리 탭 UI — T-067.
- 비개발 직군 분류(디자인·마케팅 등) — Charter §5 비목표.
- 직군별 분기 스코어링 모델 — 단일 모델 유지(A-7 별도 결정).

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/domain_classifier.py` (신설)
- `ai/worker/src/worker/persistence.py` (load_resume 하드코딩 2줄 교체 + `resume_domains` upsert)
- `podo/apps/api/prisma/` (resume_domains 테이블 migration) + api read-only 서빙(feed/resume 모듈)
- `ai/worker/tests/test_domain_classifier.py` (신설) · `ai/tests/test_schema_contract.py`(resume_domains 검증)

## 5. 완료 조건
`load_resume` 하드코딩이 제거되고, 백엔드/데이터/프론트엔드 이력서 fixture 각각에서 올바른 primary/secondary 도메인이 분류된다. 동일 이력서는 항상 동일 도메인을 반환한다.

## 6. Acceptance Criteria
- AC-1 [Given] 백엔드·데이터·프론트엔드 각 이력서 fixture(evidence domain 집계 + 스킬 신호 포함) [When] `classify_domains()` 호출 [Then] 각각 올바른 primary_domains(backend/data/frontend)가 반환되고 `load_resume` 하드코딩이 코드에 존재하지 않는다.
- AC-2 [Given] 신호 빈약 이력서(evidence 없음 or 규칙 미매칭) [When] `classify_domains()` 호출 [Then] `confidence="low"`, `primary_domains=["unknown"]`을 반환하고 오류 없이 처리된다.
- AC-3 [Given] 풀스택 이력서(frontend+backend 동수 신호) [When] `classify_domains()` 호출 [Then] primary_domains에 복수 도메인이 포함되거나 confidence에 혼재 신호가 명시된다.
- AC-4 [Given] 동일 이력서 fixture [When] `classify_domains()` 2회 호출 [Then] 동일 DomainResult 반환(결정적, GS-1 정합 — CLASSIFIER_VERSION 핀).
- AC-5 [Given] 분류된 이력서 [When] 채점/분류 후 `resume_domains` upsert + `GET /api/v1/feed`(또는 resume) 조회 [Then] `resume_domains`에 (primary_domains·secondary_domains·confidence·classifier_version) 행이 존재하고 api가 이를 read-only로 서빙한다(T-067 탭이 소비할 계약). schema-contract가 `resume_domains` 테이블을 검증한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_domain_classifier.py::test_AC_1_domain_classification_per_type
- AC-2 → pytest::ai/worker/tests/test_domain_classifier.py::test_AC_2_low_confidence_sparse_resume
- AC-3 → pytest::ai/worker/tests/test_domain_classifier.py::test_AC_3_fullstack_multi_domain
- AC-4 → pytest::ai/worker/tests/test_domain_classifier.py::test_AC_4_deterministic_output
- AC-5 → pytest::ai/tests/test_schema_contract.py::test_AC_5_resume_domains_table + vitest::podo/apps/api/test/resume_domains.spec.ts

## 6-2. TDD opt-out

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-022-resume-domain-classification](../features/F-022-resume-domain-classification.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§7-4 직군 분리 탭)
- Architecture-Iface: [ARCH ## 7-1 API](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-1) (`resume_domains` read-only 서빙 계약 — T-067 탭이 소비)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (도메인 정렬)
- ADR: [ADR-108](../../90-decisions/project/ADR-108-scoring-candidate-prefilter.md) (D6 결정성·버전 핀)

## 8. 메모 — 결정 확정 (2026-06-08, 사용자 승인)
- **도메인 어휘**: 기존 `core/models.py`의 `ROLE_FAMILY_TO_DOMAINS` 토큰 재사용(frontend·web·backend·fullstack·mobile·android·ios·data·ml_ai·ai·devops·cloud·infra·security). **새 어휘 신설 금지** — T-065 매칭(resume.domains ↔ JD.role_family→`ROLE_FAMILY_TO_DOMAINS`) 정합 필수. 비개발(product/marketing/design)은 분류 대상 외(Charter §5).
- **분류 방식**: 결정적(LLM 아님, F-022 §5) = evidence.domain 집계(1차) + `SKILL_DOMAIN_RULES`(보강). `fullstack`은 frontend+backend 동시 신호 시 추론(사전에 없음). `web`은 frontend로 흡수.
- **SKILL_DOMAIN_RULES 확정본**: §2 Step-2. 다의어(python/java/typescript/go/sql)·kotlin 제외. `CLASSIFIER_VERSION="v1"` — 사전 변경 시 bump + 재분류(GS-1).
- **TODO(후속, M5 초기 미포함)**: ① kafka 등 다도메인 스킬 → `dict[str, list[str]]`로 multi-domain(backend+data) 지원. ② linux/nginx 등 약신호 → strong/weak 가중 분리.
- `load_resume` 변경은 수술적 2줄 교체(ADR-006 YAGNI — 인접 코드 미개선).

## 9. 의존성
- depends_on: []
- read_set: ["ai/worker/src/worker/persistence.py", "ai/core/src/core/models.py", "podo/apps/api/prisma/schema.prisma"]
- write_set: ["ai/worker/src/worker/domain_classifier.py", "ai/worker/src/worker/persistence.py", "ai/worker/tests/test_domain_classifier.py", "podo/apps/api/prisma/migrations/**", "podo/apps/api/prisma/schema.prisma", "podo/apps/api/src/feed/**", "ai/tests/test_schema_contract.py"]
- assumptions: ["EvidenceItem.domain 필드가 core/models.py에 이미 존재", "Resume.primary_domains / secondary_domains가 list 타입으로 이미 정의됨"]
- verifier: "uv run pytest ai/worker/tests/test_domain_classifier.py ai/tests/test_schema_contract.py && pnpm --filter @podo/api test"
