# ADR-103: eval↔worker 의존 경계 — eval은 worker 공개 심볼만 의존

> scope: project
> area: dev

## Status
accepted

## 배경
> evidence label (ADR-022): **[관측됨]** — M1 `/stabilize-milestone` reviewer REV-M1-003 (2026-06-05).

`ai/eval`(read-only 게이트 측정 레이어)이 `ai/worker`의 **private 심볼**을 직접 import한다:

- `ai/eval/src/eval/regression.py`, `eval_resumes.py` ← `worker.verify_matches._build_haystack` / `_is_extractive`.

`verify_matches`에는 "T-014가 재사용 — 공개 유지" 주석만 있고 계약이 *주석으로만* 강제된다(취약). ARCH §3-2상 `eval → worker` **의존 방향 자체는 허용**이나, private(`_` 접두) 심볼 직접 노출은 worker 내부 리팩토링 시 eval을 **무음으로 깨뜨린다**. ARCH §3-1은 결정론·grounding 2개 경계만 1급으로 명시하고 private-symbol 접근 세칙은 부재 — 본 ADR이 그 세칙을 박는다.

## 결정

### D1. eval은 worker **공개 심볼만** import한다
private(`_` 접두) 심볼이 필요하면 worker가 **공개 API를 제공**한다. eval이 worker private에 직접 의존하는 것을 금지한다.

### D2. grounding 원시 연산을 공개 모듈 `worker/grounding.py`로 승격
- 신규 `ai/worker/src/worker/grounding.py`에 `build_haystack`, `is_extractive`를 **공개**로 둔다.
- `verify_matches`는 이 모듈을 내부 사용한다(기존 `_build_haystack`/`_is_extractive`는 여기로 이전 또는 re-export).
- eval(`regression.py`·`eval_resumes.py`)은 `worker.grounding`만 의존한다.

### D3. 단순 public alias는 채택하지 않는다
`build_haystack = _build_haystack` 식의 별명만 다는 방식은 기각 — "private인데 별명만 단" 모호함이 잔존한다. grounding은 GS-2 계약의 1급 개념이므로 **모듈로 승격**해 의존의 의미를 명시한다.

## 근거
- 이 2개 심볼은 단순 내부 헬퍼가 아니라 **GS-2 grounding 계약 그 자체**다(표시된 근거가 JD 원문에 실재하는지 판정). read-only 측정 레이어(eval)의 의존을 *명명된 게이트 개념*(`worker.grounding`)에 붙이면 worker 내부 리팩토링이 eval을 무음으로 깨지 못한다 — ARCH §3-1이 결정론·grounding 2개 경계만 1급으로 명시한 것과 동일 논리.
- **대안 — 단순 public alias:** 기각(위 D3, 모호함 잔존).
- **대안 — eval이 grounding 로직 자체 복제:** 기각. SSOT 위배 + GS-2 알고리즘 fork는 M1 이식 감사가 가장 경계한 무음 drift 원천.

## 결과
- 신규 `ai/worker/src/worker/grounding.py` — `build_haystack` / `is_extractive` 공개.
- `verify_matches.py`는 grounding을 import(또는 re-export). eval 2파일은 `worker.verify_matches._*` → `worker.grounding.*`로 교체.
- **behavior-preserving** (외부 동작 불변, 구조만 개선). 구현은 M2 **F-011(worker-boundary-hardening)**이 집행 — M1 REV-M1-003 회수.
- 본 ADR의 Surfaces 역참조(`ADR-103` 주석)는 F-011 구현 시 각 파일에 부착한다.

## Surfaces
> 본 ADR이 동기 반영되는 파일. 변경 시 함께 갱신.
- [ai/worker/src/worker/grounding.py](../../../ai/worker/src/worker/grounding.py) — 신규 공개 모듈.
- [ai/worker/src/worker/verify_matches.py](../../../ai/worker/src/worker/verify_matches.py) — grounding 사용처.
- [ai/eval/src/eval/regression.py](../../../ai/eval/src/eval/regression.py) · [eval_resumes.py](../../../ai/eval/src/eval/eval_resumes.py) — import 교체.
- [ARCHITECTURE_OVERVIEW.md](../../20-system/ARCHITECTURE_OVERVIEW.md) §3-2 — "eval은 worker 공개 심볼만 의존" 세칙(F-011 시 1줄 명문화).
- [project/README.md](README.md) — ADR 인덱스 행.

<!-- 관련: ADR-006(단순성·아키텍처 — 의존성 규칙은 ADR 대상), ADR-100(D1 게이트 우선 — GS-2 grounding), ADR-104(worker shared-util 경계 — 동반 M1 위생). 구현: M2 F-011. -->
