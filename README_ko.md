<!-- 구조 변경 시 README.md와 README_ko.md를 동시에 갱신한다. 본문은 짧게, 깊은 정의는 docs/ 링크로 둔다. -->
# podo-ai

**Language: [English](README.md) | 한국어**

여러 채널(우선 회사 공식 채용 페이지)에 흩어진 개발자 채용공고를 자동 수집하고, 사용자 이력서 대비 각 공고의 **fit 적합도**와 **합격 가능성**을 *일관되고 근거에 grounding된* 방식으로 점수화하는 SaaS다. 1순위 사용자는 신입/졸업예정 개발자 구직자.

> **단일 thesis**: "틀린 점수"가 "근거 없는 점수"보다 치명적이다. 점수의 **일관성**과 **근거 사실성**이 모든 기능에 우선하는 신뢰 게이트다. [DISCOVERY.md](docs/10-charter/DISCOVERY.md)(SSOT) · [PROJECT_CHARTER.md](docs/10-charter/PROJECT_CHARTER.md) 참조.

## 문제

신입 개발자 구직자는 (1) 7개+ 채널을 매일 수동 순회하다 신규·마감 공고를 놓치고, (2) "신입/경력무관"에 숨은 경력요구 때문에 합격 가능성을 못 가늠하며, (3) JD 키워드는 겹치나 실제 요구 수준을 못 읽어 fit을 과대평가한다. (Charter §3)

## MVP 범위 (게이트 우선)

- **수집** — 회사 공식 채용 페이지 2곳(토스·당근) 직접 파이프라인 + 커버리지 투명성 패널 + 신규/마감 diff. (F1~F3)
- **점수** — 결정론 캐시 스코어링(temperature=0 / 버전 핀), 상대 랭킹, JD 인용 근거, 이력서↔JD 매핑. (F4~F7)
- 합격 가능성은 정확한 %가 아닌 **5단계 색깔 밴드**로 표현.

비범위 (Charter §5): 다채널 풀커버리지, 이력서/자소서 자동작성, 절대 합격확률 캘리브레이션, 일정·자동지원, 협업.

## 출시 게이트 (Charter §6)

- **GS-1 일관성** (🔴 차단) — 동일 (이력서, JD) 입력 → 캐시 hit 변동 0, 재계산 top-k 순서 변동 0.
- **GS-2 정확도** (🔴 차단) — 표시 근거의 hallucinated requirement 비율 ≤ 2% (표본 ≥30).
- **GS-3 랭킹 타당도** (🟡 출시 후) — 추천 상위군 통과율 > 하위군, 출시 후 측정.

## 상태

초기 bootstrap 단계. **스택 미정** — stack-specific 자동화(hooks/CI/lint/test) 미추가. 발굴 가정(A-1~A-12) 전부 **미검증**(인터뷰·딥리서치 전). [assumption tracker](docs/10-charter/DISCOVERY.md) §12 참조.

## 문서

- [DISCOVERY.md](docs/10-charter/DISCOVERY.md) — 페르소나 / pain / 시나리오 (SSOT)
- [PROJECT_CHARTER.md](docs/10-charter/PROJECT_CHARTER.md) — 범위·목표·비목표·성공 게이트
- [ARCHITECTURE_OVERVIEW.md](docs/20-system/ARCHITECTURE_OVERVIEW.md) — 모듈(Collector/Scorer/Feed) + 의존성 규칙
- [ADR-100](docs/90-decisions/project/ADR-100-initial-project-decisions.md) — 초기 결정(신뢰 게이트, 4-layer 미채택, 결정론 캐시)
- [WORKFLOW.md](docs/00-meta/WORKFLOW.md) · [STRUCTURE.md](docs/00-meta/STRUCTURE.md) — document-first 개발 프로세스(harness 상속)

## 다음 단계

본 프로젝트는 document-first agentic harness에서 bootstrap되었다. 권장 다음 명령: `/bootstrap-stack`으로 스택 확정(결정론 캐시 저장소·크롤링 방식을 GS-1 / A-1 기준으로 선택해야 함) 후 `/plan-workitem M1`.

## 라이선스

MIT
