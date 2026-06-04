# T-013-domain-aware-selection

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
비싼 LLM 단계 전, 값싼 휴리스틱으로 사용자 도메인 기준 균형 후보를 선별한다(`crawler`): 제목 기반 role_family 분류 + tier + `select_balanced`(50%/30%/20%) + 선택 리포트 (SPEC §9-3·§9-4).

## 2. 작업 범위
- `ROLE_PATTERNS`(제목 키워드 → role_family, 순서대로 첫 매치 승) + `classify_role_family`.
- tier 매핑(`ai/core`의 `domain_alignment` 재사용 → primary/adjacent/weak/mismatch) + 풀 구성(`--pool-size` 50, 회사 round-robin).
- `select_balanced(pool, limit)`: q_primary=round(limit*0.5), q_adjacent=round(limit*0.3), q_contrast=나머지, 정원 미달 priority backfill. limit=10 → 5/3/2.
- 선택 리포트(`fetch_selection_report` 동등: tier/role_family 분포, selected/skipped).

## 3. 구현 항목
- `crawler/selection.py` — `ROLE_PATTERNS`/`classify_role_family`/`role_tier`/`build_pool`/`select_balanced`/선택 리포트.
- `USER_PRIMARY/SECONDARY_DOMAINS`는 설정값(MVP 단일 사용자; 후속 후보별). **`domain_alignment`은 `ai/core`(T-002)에서 import** — crawler가 ai/worker를 import하지 않는다(의존 방향 정합, ARCH §3-1).

## 4. 제외 항목
- fetch/upsert(T-012) · LLM role_family 확정(F-001 jd_extract가 최종 권위) · 후보별 도메인 프로파일(후속).

## 4-1. 변경 예정 파일/경로
- `crawler/selection.py`, `crawler/tests/test_selection.py`

## 5. 완료 조건
제목으로 role_family를 분류하고, pool에서 도메인 균형으로 limit만큼 선택하며, 선택 내역을 리포트로 남긴다.

## 6. Acceptance Criteria
- AC-1 [Given] 다양한 제목("Frontend Developer", "콘텐츠 마케터", "Android Engineer", "DevOps SRE") [When] `classify_role_family` [Then] 각각 frontend/marketing/android/devops_infra로 분류되고(순서 우선), 미매칭은 "other"다.
- AC-2 [Given] pool=50개(tier 혼합), limit=10 [When] `select_balanced` [Then] primary 5 + adjacent 3 + contrast 2(정원 미달 시 priority backfill)로 선택되고 selected_count==min(10, pool)이다.
- AC-3 [Given] 선택 실행 [When] 리포트 생성 [Then] selected/skipped 각각 tier·role_family 분포와 함께 기록되고, 주력 도메인 0건이면 명시된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::crawler/tests/test_selection.py::test_AC_1_role_family_classification
- AC-2 → pytest::crawler/tests/test_selection.py::test_AC_2_select_balanced_quota
- AC-3 → pytest::crawler/tests/test_selection.py::test_AC_3_selection_report

## 6-2. TDD opt-out
<!-- TDD 적용 — 순수 결정적 휴리스틱. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-002-collector](../features/F-002-collector.md)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §9-3·§9-4](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
제목 휴리스틱 role_family는 *선택용 임시값* — LLM jd_extract가 최종 권위(SPEC §9-3).

## 9. 의존성
- depends_on: [T-002, T-012]  # domain_alignment은 ai/core(T-002); compute_fit(T-003) 불필요
- read_set: ["ai/core/models.py", "crawler/fetch_jobs.py"]
- write_set: ["crawler/selection.py", "crawler/tests/test_selection.py"]
- verifier: "uv run pytest crawler/tests/test_selection.py"
