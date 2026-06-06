# F-010-feed-coverage-ui: 단일 피드 + 적합도 5단계 + 근거 펼침 + 커버리지 패널

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
Next.js(`podo/apps/web`)가 API(F-009)에서 받은 공고를 **단일 중복제거 피드**로 노출한다 — 적합도 5단계 배지(fit_level 직결) + fit 배지로 정렬, 근거 펼침(JD 인용 + 이력서↔JD 매핑), 커버리지 투명성 패널, LLM 보류 상태 표시. DISCOVERY F2 + Charter §8 흐름을 구현하는 M2의 사용자 노출 surface다.
> **근거 insight:** I-3(누락 0 투명성 — 커버리지 패널) · I-1(신뢰 thesis — 보류·근거 표시). (DISCOVERY §15)

## 2. 사용자 가치 (User Story) — Type=feature
- As "유진"(신입/졸업예정 개발자 구직자, Charter §2.1), I want to 흩어진 공고를 단일 피드에서 *적합도 순*으로 보고 근거를 펼쳐 확인하고 싶다, so that 헛지원·과소지원을 줄이고 지원/스킵 결정 비용을 낮춘다. (pain #2·#3)
- As "유진", I want to 무엇이 수집/미수집인지 커버리지 패널로 알고 싶다, so that "전부 수집됐다"는 거짓 완전성에 속지 않는다. (Fail #3 / G3)

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 피드 진입 → 중복제거 공고가 적합도 5단계 + fit 배지와 함께 상위부터 정렬 노출.
2. 상위 공고 펼침 → 근거(JD 인용 + 이력서↔JD 매핑) 확인.
3. 커버리지 패널에서 "수집: 토스·당근 / 마지막 성공 시각" 확인.
### Alternate path
1. 점수 낮은 공고도 근거(부족 요건)를 명시하되 숨기지 않음.
### Fail path
1. 🔴 LLM 보류 공고 → *가짜 점수 대신* 보류 상태 표시("틀린 것보다 없는 게 낫다", §8-1).
2. 🔴 특정 채널 미수집 → 커버리지 패널에 미수집 명시(거짓 완전성 차단).

## 4. 범위
- 단일 피드 페이지(API의 `recommendations` 정렬 목록을 `rank_position` 커서로 무한 스크롤 + 리스트 가상화, §7-4).
- **적합도 5단계 배지**(fit_level 1~5 직결) + fit 배지 — DESIGN `PassBand`/`FitScoreRing` 재사용(아래 §11 cross-check).
- 근거 펼침 — `ranking_runs.result` JSONB(opaque)에서 JD 인용 + 매핑을 `EvidenceBlock`으로 렌더(표시만, 비즈니스 분기 X).
- 커버리지 투명성 패널 — `GET /api/v1/coverage`(F-009) 소비, `coverage.*` 토큰.
- 보류 상태 표현(LLM miss).

## 5. 비범위
- 인증·공개 배포(Vercel) — M2 done-line은 로컬(Charter §5).
- 직군 분리 탭 — **M2 비범위**(A-7 의존, 단일 모델 시작; 후속 확장 후보). [cross-LLM P1 회수 — M2 milestone §4 비목표와 정합]
- 알림 푸시 · 즐겨찾기/지원기록 CRUD.
- 새 디자인 primitive 신설(기존 DESIGN §7 컴포넌트 재사용).

## 6. 요구사항
- 구조: App Router · 커서 페이지네이션(stable key=`rank_position`, API 제공; offset 미사용, §7-1) · 리스트 가상화(§7-4).
- **적합도 = fit_level 직결**, 합격확률·% 표시 금지(M2 명칭 결정 / Charter §5).
- `result` JSONB는 *표시만* — 비즈니스 분기에 쓰지 않음(§7-4 / §3-2 규칙3).
- 색·간격은 DESIGN 토큰 사용, raw hex 직접 박기 금지(DESIGN §2).
- 의미를 색만으로 전달 금지 — 밴드는 텍스트 라벨(+아이콘) 동반(DESIGN §2-5).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** 피드가 중복제거된 공고를 적합도 5단계 + fit 배지와 함께 상위부터 정렬 렌더한다.
- **FAC-2:** 공고 펼침이 `result`의 JD 인용 + 이력서↔JD 매핑을 `EvidenceBlock`으로 표시한다.
- **FAC-3:** 커버리지 패널이 수집/미수집 채널 + 마지막 성공 시각을 표시한다.
- **FAC-4:** LLM 보류 공고가 가짜 점수 없이 보류 상태로 표시된다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 (피드·적합도 5단계 정렬) → T-028:AC-1, T-028:AC-2
- FAC-2 (근거 펼침) → T-029:AC-1
- FAC-3 (커버리지 패널) → T-029:AC-2
- FAC-4 (보류 상태) → T-029:AC-3

## 8. Non-functional Requirements
- 성능: 저장 결과 읽기 + 가상화로 긴 목록 bound. 접근성: DESIGN §2-5(대비 AA)·키보드.
- 보안: web은 API 경유만, DB 직접 접근 없음(§3-2).

## 8-1. UX 흐름 품질
- **primary task:** 공고의 적합도·근거를 신뢰해 지원/스킵 결정.
- **empty / loading / error:** empty="오늘은 적음"(GreetingCard) · loading=JobCard skeleton(§7-4) · error/보류=가짜 점수 대신 보류·미수집 명시.
- **accessibility:** 밴드는 색+텍스트 라벨(+✓/△), 대비 AA(band-*-ink), 키보드 펼침/포커스(§7-4 focus 상태).
- **copy 톤:** 근거는 JD 인용 기반("JD에 X 요구됨"), 단정·과약속 금지(원칙 1 — 엄격한 data).
- **success metric (HEART — Task success):** 추천 상위군 지원 전환율 > 하위군 → 출시 후 실데이터로 DISCOVERY §14 회수(GS-3).

## 9. 엣지 케이스
- 근거 빈약(인턴1·팀플2~3) — 없는 근거 지어내지 않음(보류/축약).
- 적합도 동률 공고 — tie 표시.
- 긴 JD 인용 — 펼침 truncation.
- 보류 다발(LLM 실패 다수) — 패널에 집계.

## 10. 의존성
- **선행:** T-026·T-027(API). DESIGN.md(이미 §7 컴포넌트 설계 완료).
- **블로킹:** 없음(M2 done-line의 종착).

## 11. 관련 문서
- Milestone: [M2-service-wiring](../milestones/M2-service-wiring.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§3.1 시나리오, §8 흐름)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§4 CoverageState)
- Architecture-Iface: [ARCH ## 7-4 프론트](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-4) (단일 피드 가상화·5단계 밴드·커버리지 패널·보류 표현)
- Design: [DESIGN ## 2 Colors](../../20-system/DESIGN.md#design-2-colors) (passband·coverage 토큰) · [## 7 Components](../../20-system/DESIGN.md#design-7-components) (JobCard·FitScoreRing·PassBand·EvidenceBlock — **재사용**, 8-상태 §7-4)
- ADR: [ADR-042](../../90-decisions/boilerplate/ADR-042-ux-flow-quality.md) (UX 흐름 품질) · [ADR-027](../../90-decisions/boilerplate/ADR-027-interface-decision-allocation.md) (DESIGN/ARCH 책임 분배)

## 12. 열린 질문
- **명칭 reconcile:** DESIGN §2/§7은 "합격가능성/PassBand"인데 M2 결정은 **"적합도 5단계"** — 컴포넌트는 재사용하되 라벨을 적합도로. DESIGN(SSOT는 DISCOVERY) 용어 갱신은 후속(`/bootstrap-design` 또는 `/discover-product --update`).
- 리스트 가상화 라이브러리 선택(§7-4 — 구현 시).
> 직군 분리 탭은 **M2 비범위로 확정**(cross-LLM P1 회수 — §5 / M2 milestone §4).
