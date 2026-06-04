# T-005-prompts-and-parse

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
7개 LLM 프롬프트(verbatim)와 입력 구조화 단계(이력서 evidence 추출 + 결정적 Skills 보강, JD 요구사항 구조화 with prerequisite vs product_duty)를 `ai/worker`에 이식한다 (SPEC §7-1·§7-2 / 부록 A).

## 2. 작업 범위
- 프롬프트 7종 작성(`resume_extract`, `jd_extract`, `requirement_evidence_match`, `rematch_evidence`, `match_verifier`, `listwise_rerank`, `pairwise_compare`) — SPEC 부록 A 계약을 글자 그대로 충족.
- `parse_resume`: LLM 추출 + 결정적 Skills evidence 보강(헤딩 파싱, verbatim 불릿 → exact_quote).
- `parse_job`: LLM 구조화 + prerequisite_status default 규칙 + id 유일성.

## 3. 구현 항목
- `ai/worker/prompts/*.md` 7종 — **SPEC 부록 A의 각 ````text 펜스 본문을 글자 그대로 복사**(`{{VAR}}` 플레이스홀더 포함). 패러프레이즈 금지(LLM IP). 스냅샷 테스트(AC-2)가 부록 A ↔ 파일 정규화 동일성을 강제.
- `ai/worker/parse_resume.py` — `extract_evidence`(프롬프트 `resume_extract`) + `extract_skills_evidence`(결정적, Skills 헤딩 → 토큰) + id 충돌 `_x` suffix + `skills_debug`.
- `ai/worker/parse_job.py` — `structure_job`(프롬프트 `jd_extract`) + `_requirements`(prerequisite default: behavioral→behavioral_preference, else prerequisite).

## 4. 제외 항목
- 매칭/rematch(T-006) · 검증(T-007) · listwise/pairwise 호출(T-009·T-010 — 프롬프트만 본 task가 작성).

## 4-1. 변경 예정 파일/경로
- `ai/worker/prompts/` (7 파일), `ai/worker/parse_resume.py`, `ai/worker/parse_job.py`, `ai/worker/tests/test_parse.py`

## 5. 완료 조건
프롬프트 7종이 존재하고, 이력서의 Skills 항목이 결정적으로 보강되며, JD가 prerequisite/product_duty로 분류된다.

## 6. Acceptance Criteria
- AC-1 [Given] Skills 헤딩 + 불릿이 있는 이력서 텍스트 [When] `extract_skills_evidence` [Then] evidence_type="skills"·exact_quote=verbatim 불릿·skills=분해 토큰인 항목이 (LLM과 무관하게) 추가된다.
- AC-2 [Given] 7개 프롬프트 파일 + SCORING_PIPELINE_SPEC.md 부록 A [When] 스냅샷 테스트가 부록 A의 각 `### A-N. \`<name>.md\`` ````text 펜스 본문을 추출해 `ai/worker/prompts/<name>.md`와 비교 [Then] 줄 단위 정규화(trailing whitespace·말미 개행 제거) 후 **글자 단위로 동일**하다(패러프레이즈/누락/순서변경 0 — verbatim 강제).
- AC-3 [Given] behavioral nature인데 prerequisite_status 누락한 JD 요구 [When] `structure_job` 파싱 [Then] 해당 요구는 `behavioral_preference`로, 그 외 누락은 `prerequisite`로 default된다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_parse.py::test_AC_1_skills_evidence_deterministic
- AC-2 → pytest::ai/worker/tests/test_parse.py::test_AC_2_prompts_verbatim_match_spec_appendix_a
- AC-3 → pytest::ai/worker/tests/test_parse.py::test_AC_3_prerequisite_status_default

## 6-2. TDD opt-out
<!-- TDD 적용 — LLM 단계는 fake 주입, Skills 보강·default 규칙은 순수 결정적. -->

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md)
- Feature: [F-001-core-value](../features/F-001-core-value.md)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §7-1·§7-2 / 부록 A](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
프롬프트는 검증된 IP — AC-2가 SPEC 부록 A와 **verbatim 동일성을 강제**(스냅샷 테스트). SPEC 부록 A가 단일 출처이므로, 프롬프트를 바꾸려면 부록 A를 먼저 고친다.

## 9. 의존성
- depends_on: [T-002, T-004]
- read_set: ["ai/core/models.py", "ai/worker/llm.py", "docs/20-system/SCORING_PIPELINE_SPEC.md"]
- write_set: ["ai/worker/prompts/**", "ai/worker/parse_resume.py", "ai/worker/parse_job.py", "ai/worker/tests/test_parse.py"]
- verifier: "uv run pytest ai/worker/tests/test_parse.py"
