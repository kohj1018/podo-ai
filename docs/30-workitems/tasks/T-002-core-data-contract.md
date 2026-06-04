# T-002-core-data-contract

## 0. Status
draft

## 0-1. Type
technical-enabler

## 1. 작업 목적
모든 파이프라인 단계가 의존하는 공유 데이터 계약(Pydantic 모델 + enum/가중치 상수 + clamp/as_list 헬퍼)을 `ai/core`에 이식한다. *가장 먼저* 옮길 자산 (SPEC §3).

## 2. 작업 범위
- SPEC §3-1 enum/분류 상수 전체(EVIDENCE_TYPES, REQ_TYPES, MATCH_LEVELS, PREREQ_STATUSES, REQ_CATEGORIES, CORE_NATURES, ROLE_FAMILY_TO_DOMAINS, DOMAIN_ALIGNMENTS, MATCH_SEVERITY, CONF_RANK, FIT_LABELS 등) + 헬퍼 `clamp`/`as_list`.
- SPEC §3-2 모델: EvidenceItem, Resume, Requirement, JobPosting(+`all_requirements()`), MatchRow, MatchingTable, PairwiseResult, FitResult — `field_validator(mode="before")` clamp 포함.
- **`domain_alignment(role_family, primary, secondary)`** (SPEC §4-3) — worker(스코어링)·crawler(도메인 선택)가 *둘 다* 쓰므로 ai/core에 둔다(crawler→worker import 방향 위반 방지, ARCH §3-1).

## 3. 구현 항목
- `ai/core/models.py` — 상수 + Pydantic v2 모델(SPEC §3 그대로) + `domain_alignment`(SPEC §4-3, `ROLE_FAMILY_TO_DOMAINS`와 같은 파일). 순환 import 방지(모든 공유 스키마/순수 헬퍼 1파일).
- enum 필드는 `clamp`로 허용값 외 입력을 default로 클램프(LLM 오출력 방어). 리스트 필드는 `as_list` 강제.
- `FIT_LABELS`(1~5 한국어 라벨) 보존 — 합격확률/% 금지(Charter §5).

## 4. 제외 항목
- DB 매핑(Prisma 스키마 — `podo/apps/api`) · 알고리즘 로직(compute_fit 등은 T-003~).

## 4-1. 변경 예정 파일/경로
- `ai/core/models.py`, `ai/core/tests/test_models.py`

## 5. 완료 조건
모델이 정상 입력을 검증·직렬화하고, enum 클램프와 리스트 강제가 명세대로 동작한다.

## 6. Acceptance Criteria
- AC-1 [Given] 유효한 dict 입력 [When] 각 모델로 파싱 후 `model_dump()` [Then] 모든 필드가 보존된 round-trip이 성립한다.
- AC-2 [Given] 허용값 밖 enum 값(예: requirement_type="bogus")·콤마 문자열 리스트 [When] 모델 생성 [Then] enum은 default로 클램프되고("required" 등) 리스트 필드는 `List[str]`로 정규화된다.
- AC-3 [Given] requirements=[R1], preferred_requirements=[P1]인 JobPosting [When] `all_requirements()` [Then] R1·P1을 합친 리스트(순서 보존)를 반환한다.
- AC-4 [Given] primary={"frontend","web"}, secondary={"backend"} [When] `domain_alignment(rf, primary, secondary)` [Then] rf="frontend"→"strong", rf="backend"→"adjacent", rf="marketing"→"mismatch", rf="data"→"weak"를 반환한다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/core/tests/test_models.py::test_AC_1_roundtrip
- AC-2 → pytest::ai/core/tests/test_models.py::test_AC_2_enum_clamp_and_list_coercion
- AC-3 → pytest::ai/core/tests/test_models.py::test_AC_3_all_requirements
- AC-4 → pytest::ai/core/tests/test_models.py::test_AC_4_domain_alignment

## 6-2. TDD opt-out
<!-- TDD 적용. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-001-core-value](../features/F-001-core-value.md)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §3](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모

## 9. 의존성
- depends_on: [T-001]
- read_set: ["docs/20-system/SCORING_PIPELINE_SPEC.md"]
- write_set: ["ai/core/models.py", "ai/core/tests/test_models.py"]
- verifier: "uv run pytest ai/core/tests/test_models.py"
