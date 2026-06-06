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

**M1(알고리즘 이식)**·**M2(서비스 와이어링)** 구현 완료: 검증된 fit 랭킹 알고리즘이 이제 서비스로 end-to-end 동작한다 — 수집 → worker 스코어링(결정론·캐시) → Postgres → API 서빙 → 적합도 5단계 배지·JD 인용 근거·커버리지 패널 피드 UI. 전체 파이프라인은 `pnpm e2e`로 로컬에서 **오프라인/무키** 재현 가능(아래 참조). 스택([ADR-101](docs/90-decisions/project/ADR-101-stack-selection.md))·디자인 시스템([DESIGN.md](docs/20-system/DESIGN.md), concept "포도 친구") 확정. **A-1(크롤링 실현성) 검증됨**(2026-06-04). 그 외 발굴 가정(A-2~A-12)은 **미검증**(인터뷰 전). [assumption tracker](docs/10-charter/DISCOVERY.md) §12 참조.

## 로컬 E2E (오프라인·무키)

단일 명령으로 커밋된 fixture 기반 전체 파이프라인을 **외부 LLM 호출 0회**로 돌린다(결정론 LLM 응답은 커밋된 웜캐시에서 재생):

```bash
pnpm e2e        # docker compose up → prisma migrate → crawl(fixture) → score(웜캐시) → 서빙 → feed/coverage assert
```

전제: Docker, Node ≥18(`pnpm install`), `uv`(Python). crawl은 라이브 토스·당근 API 대신 `crawler/fixtures/seed_jobs.txt`를, score는 `ai/worker/fixtures/llm_cache`를 재생하므로 네트워크·`OPENAI_API_KEY` 불요.

**웜캐시 1회 시드(키 보유자):** 커밋된 웜캐시는 키 보유자가 1회 생성한다. `OPENAI_API_KEY`를 설정한 뒤 `pnpm e2e:warm`을 돌리고 생성된 `ai/worker/fixtures/llm_cache/*.json`을 커밋하면, 이후 `pnpm e2e`와 `e2e-smoke` CI 게이트가 무키로 통과한다. 키 유무와 무관하게 동일 코드 경로(캐시 hit/miss만 차이).

## 문서

- [DISCOVERY.md](docs/10-charter/DISCOVERY.md) — 페르소나 / pain / 시나리오 (SSOT)
- [PROJECT_CHARTER.md](docs/10-charter/PROJECT_CHARTER.md) — 범위·목표·비목표·성공 게이트
- [ARCHITECTURE_OVERVIEW.md](docs/20-system/ARCHITECTURE_OVERVIEW.md) — 모듈(Collector/Scorer/Feed) + 의존성 규칙
- [ADR-100](docs/90-decisions/project/ADR-100-initial-project-decisions.md) — 초기 결정(신뢰 게이트, 4-layer 미채택, 결정론 캐시) · [ADR-101](docs/90-decisions/project/ADR-101-stack-selection.md) — 스택 선택
- [DESIGN.md](docs/20-system/DESIGN.md) — UI 디자인 시스템 SSOT(토큰/컴포넌트/모션)
- [WORKFLOW.md](docs/00-meta/WORKFLOW.md) · [STRUCTURE.md](docs/00-meta/STRUCTURE.md) — document-first 개발 프로세스(harness 상속)

## 다음 단계

M1·M2 구현 완료. 로컬 실행은 `pnpm e2e`(위 [로컬 E2E](#로컬-e2e-오프라인무키) 참조). 다음 마일스톤(M3)은 아직 미정의 — [DISCOVERY](docs/10-charter/DISCOVERY.md) §13 기회 백로그에서 범위를 정의(`/discover-product --update`)한 뒤 **`/plan-workitem M3`**로 분해.

## 라이선스

MIT
