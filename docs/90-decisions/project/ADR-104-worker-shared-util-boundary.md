# ADR-104: worker 공통 util 경계 — cross-module util은 leaf 모듈로 중앙화

> scope: project
> area: dev

## Status
accepted

## 배경
> evidence label (ADR-022): **[관측됨]** — M1 `/stabilize-milestone` reviewer REV-M1-001/002/007 (2026-06-05).

`ai/worker` 내 cross-module 공통 util이 복제되어 있다:

- **`_extract_json`** ("code-fence 제거 → greedy shrink") — 3곳 복제: `compare_pairwise.py`, `llm.py`, `rerank_listwise.py`(`_extract_json_raw` 변형). 주석이 스스로 "동일 로직"을 시인.
- **`_load_prompt` / `_render`** — 4곳 복제: `parse_resume.py`, `parse_job.py`, `verify_matches.py`, `matching.py`.
- **`DOM_RANK`** 캘리브레이션 상수 — `rank_aggregate.py`(정의) + `rerank_listwise.py`. *(2026-06-06 부분 해소: rerank가 이미 `rank_aggregate.DOM_RANK`를 import. 본 ADR이 이 단일-출처 상태를 정식 규칙화한다.)*

공통 위험: rule-of-3 위반 + **GS-1 게이트가 못 잡는 무음 parsing/calibration drift 표면** — 한 곳만 고치면 나머지가 무음 방치된다.

## 결정

### D1. cross-module 공통 util은 leaf 모듈로 **중앙화**한다 (로컬 복사 금지)
worker 내 2개 이상 모듈이 공유하는 util은 아무것도 worker 내부에서 import하지 않는 *leaf 모듈*에 단일 정의하고 상위 모듈이 하향 import한다.

### D2. JSON 추출 → `worker/_json_util.py`
단일 `extract_json()`로 통합. `compare_pairwise`·`llm`·`rerank_listwise`가 import(`_extract_json_raw` 변형 흡수).

### D3. 프롬프트 로딩/렌더 → `worker/_prompts.py`
`_load_prompt` / `_render`를 단일 정의. `parse_resume`·`parse_job`·`verify_matches`·`matching`이 import.

### D4. 캘리브레이션 상수는 *정의 모듈* 단일 공개 (복제 금지)
`DOM_RANK`의 SSOT는 `rank_aggregate.DOM_RANK`다(`pipeline`·`rerank_listwise`·`eval`이 거기서 import — 2026-06-06 이미 정합). 같은 값을 다른 모듈에 재선언하지 않는다.

> **순환 import 없음:** `_json_util`·`_prompts`는 leaf(worker 내부 의존 0). 상위 parse/verify/llm/rerank/compare가 단방향 하향 의존.

## 근거
- **rule-of-3 충족** (3·4·2 복제) — premature abstraction이 아니라 실측 중복 회수.
- **게이트 관련성:** `extract_json`은 LLM 응답 파싱(GS-1 결정성 입력 경로), `DOM_RANK`는 정렬 키 캘리브레이션 — 한 곳 drift 시 listwise 삽입 순서 ↔ BT-aggregate 정렬 키가 *무음*으로 어긋난다(GS-1이 못 잡는 silent regression). SSOT 단일화가 가장 값싼 회귀 가드.
- **대안 — 로컬 복사 유지(순환 회피 명목):** 기각. leaf util이라 순환이 애초에 없고, 게이트 관련 코드의 silent-drift 위험이 복사의 미미한 편의를 압도.

## 결과
- 신규 `ai/worker/src/worker/_json_util.py`, `ai/worker/src/worker/_prompts.py`.
- 7개 파일(위 D2·D3 대상) import 교체 — **behavior-preserving**.
- `DOM_RANK`는 추가 작업 없음(이미 단일 출처) — 규칙 명문화로 향후 재복제 차단.
- 구현은 M2 **F-011(worker-boundary-hardening)**이 집행 — M1 REV-M1-001/002/007 회수.
- 본 ADR의 Surfaces 역참조(`ADR-104` 주석)는 F-011 구현 시 각 파일에 부착한다.

## Surfaces
> 본 ADR이 동기 반영되는 파일. 변경 시 함께 갱신.
- [ai/worker/src/worker/_json_util.py](../../../ai/worker/src/worker/_json_util.py) · [_prompts.py](../../../ai/worker/src/worker/_prompts.py) — 신규 leaf util.
- JSON 사용처: [compare_pairwise.py](../../../ai/worker/src/worker/compare_pairwise.py) · [llm.py](../../../ai/worker/src/worker/llm.py) · [rerank_listwise.py](../../../ai/worker/src/worker/rerank_listwise.py).
- 프롬프트 사용처: [parse_resume.py](../../../ai/worker/src/worker/parse_resume.py) · [parse_job.py](../../../ai/worker/src/worker/parse_job.py) · [verify_matches.py](../../../ai/worker/src/worker/verify_matches.py) · [matching.py](../../../ai/worker/src/worker/matching.py).
- [rank_aggregate.py](../../../ai/worker/src/worker/rank_aggregate.py) — `DOM_RANK` SSOT.
- [project/README.md](README.md) — ADR 인덱스 행.

<!-- 관련: ADR-006(단순성·rule-of-3·surgical changes), ADR-100(D3 결정론 — GS-1 silent-drift 가드), ADR-103(eval↔worker 경계 — 동반 M1 위생). 구현: M2 F-011. -->
