# F-011-worker-boundary-hardening: ADR-103/104 집행 (worker 경계 위생)

## 0. Status
draft

## 0-1. Type
refactor

## 1. 요약
M1 stabilize가 surface한 worker 경계 부채(REV-M1-001/002/003/007)를 ADR-103·ADR-104대로 집행한다 — eval의 worker private 의존을 공개 `worker.grounding` 모듈로 정리하고, 중복 util(`_extract_json`·`_load_prompt`/`_render`)을 leaf 모듈(`_json_util`·`_prompts`)로 중앙화한다. **외부 행동 불변**(behavior-preserving), 구조만 개선. scaffold 의존 0 → M2 착수 즉시 병렬 가능.

## 2. 사용자 가치 (User Story) — Type=refactor 이므로 기술적 근거
- **무엇/왜 (외부 행동 불변):** 게이트 관련 코드의 *무음 drift 표면* 제거. `extract_json`(GS-1 결정성 입력 경로)·`DOM_RANK`(정렬 키 캘리브레이션) 중복은 한 곳 drift 시 GS-1이 못 잡는 silent regression. eval의 worker private 의존은 worker 리팩토링 시 eval 무음 브레이킹.
- **서비스하는 결정/가정:** [ADR-103](../../90-decisions/project/ADR-103-eval-worker-boundary.md)(eval public-only + `worker.grounding`) · [ADR-104](../../90-decisions/project/ADR-104-worker-shared-util-boundary.md)(util leaf 중앙화) · ADR-006(rule-of-3·surgical).

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. `_json_util.py`·`_prompts.py`·`grounding.py` 신설 + 중복 제거/import 교체.
2. 전체 `validate`(ruff·mypy strict·pytest) green — **모든 기존 테스트 동작 동일**.
### Fail path
1. 🔴 순환 import 발생 → leaf 모듈 규칙 위반(차단). 2. 🔴 행동 변경(테스트 회귀) → refactor 실패.

## 4. 범위
- ADR-104: `worker/_json_util.py`(단일 `extract_json`)·`worker/_prompts.py`(`load_prompt`/`render`) 신설 + 사용처 import 교체(`compare_pairwise`·`llm`·`rerank_listwise` / `parse_resume`·`parse_job`·`verify_matches`·`matching`). `DOM_RANK` 단일 출처 규칙 명문화(이미 정합).
- ADR-103: `worker/grounding.py`(공개 `build_haystack`·`is_extractive`) 신설 + `verify_matches` 내부 사용 + eval(`regression.py`·`eval_resumes.py`) import을 `worker.grounding`으로 교체.
- ADR-103/104 역참조 주석(`per ADR-103`/`per ADR-104`)을 변경 파일에 부착.

## 5. 비범위
- 새 기능·동작 변경(refactor — 외부 행동 불변).
- `DOM_RANK` *값* 변경(이미 단일 출처 — 규칙 명문화만).
- 알고리즘 로직 수정(SPEC SSOT 불변).

## 6. 요구사항
- **behavior-preserving:** 모든 기존 테스트가 변경 없이 green(행동 동일 + 구조 개선 측정).
- 순환 import 없음(`_json_util`·`_prompts`·`grounding`은 leaf — worker 내부 import 0).
- eval은 worker private(`_`) 심볼 import 0(ADR-103).
- 통합 `validate` exit 0 유지.
- surgical: 범위 밖 코드 변경 금지(ADR-006 — 인접 개선·무관 포맷팅 금지).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** `extract_json`·`load_prompt`/`render` 정의가 각 단일 모듈에만 존재(중복 0)하고, 전체 pytest가 행동 동일하게 green이다.
- **FAC-2:** `ai/eval`이 worker private(`_` 접두) 심볼을 import하지 않고 `worker.grounding` 공개 API만 의존한다.
- **FAC-3:** 통합 `validate`(ruff·mypy strict·pytest)가 exit 0이다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 (util 중복 0 + 행동 동일) → T-030:AC-1, T-030:AC-2
- FAC-2 (eval public-only) → T-031:AC-1
- FAC-3 (validate green) → T-030:AC-3, T-031:AC-2

## 8. Non-functional Requirements
- 지배: 회귀 안전(GS-1 무음 drift 가드). 변경 전후 동일 입력 동일 출력.

## 8-1. UX 흐름 품질
(해당 없음 — 비-UI.)

## 9. 엣지 케이스
- `_extract_json_raw`(rerank) 변형이 단일 `extract_json`으로 흡수되며 동일 동작 유지.
- `verify_matches.py`를 T-030(prompts)·T-031(grounding) 둘 다 건드림 → write 충돌 회피 위해 T-031을 T-030 후행(§10).

## 10. 의존성
- **선행:** 없음(scaffold 의존 0 — M2 착수 즉시 병렬 가능, F-007 전 완료 권장).
- **내부 순서:** T-031 depends_on T-030(`verify_matches.py` write_set 교집합 — 같은 wave 금지).

## 11. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3-1 grounding 경계, §3-2 모듈 경계)
- ADR: [ADR-103](../../90-decisions/project/ADR-103-eval-worker-boundary.md) · [ADR-104](../../90-decisions/project/ADR-104-worker-shared-util-boundary.md) · [ADR-006](../../90-decisions/boilerplate/ADR-006-simplicity-and-architecture.md) (surgical·rule-of-3)
- 부채 출처: [IMPROVEMENT_GUIDE §2·§4](../../40-validation/IMPROVEMENT_GUIDE.md) (REV-M1-001/002/003/007)

## 12. 열린 질문
- **결정(cross-LLM P1 회수):** `grounding.py`는 `build_haystack`/`is_extractive`를 **이전(migrate)** 한다 — re-export 아님(ADR-103 D2 alias-only 기각). `verify_matches`가 `grounding`을 import해 사용(T-031 §8 해석 확정과 정합).
