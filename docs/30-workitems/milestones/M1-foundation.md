# M1-foundation

## 0. Status
draft

## 1. 목적
신뢰 게이트(GS-1 재현성 · GS-2 근거 사실성)를 *실증할 수 있는* 최소 end-to-end 골격을 세운다. "수집 → 결정론 스코어링 → 근거 표시"가 한 줄로 동작하고, 그 위에서 게이트를 측정할 수 있는 상태가 M1의 done이다. (Charter §6 / ADR-100 D1)

## 2. 범위
토스·당근 2곳 수집 골격 + 결정론 캐시 스코어링 + JD grounding 근거 + 커버리지 투명성 패널 + 최소 피드. 게이트 측정 경로(test-retest·근거 사실성 라벨링)를 함께 세운다.

> **선행 의존 (해소):** 스택 확정(ADR-101)·design 확정(DESIGN.md)·A-1 검증(크롤링 실증, 2026-06-04) 완료 → 분해 착수 가능.
>
> **A-3 시퀀싱 (재해석 명시):** 마일스톤 원안은 "A-3(상대 랭킹 Kendall τ) 검증을 첫 task로". 그러나 A-3 τ 프록시는 *모델 랭킹 vs 창업자 수기 랭킹*을 비교하므로 **랭커가 선재해야 측정 가능**하다(닭-달걀). 본 분해는 스코어링 알고리즘 본체가 외부에서 충분히 검증된 자산임을 전제로, **알고리즘(상대 랭킹 포함)을 먼저 이식 → 평가 하니스(골든 페어 = τ 프록시)로 A-3를 조기 측정**한다. `τ<0.6`(또는 자명 페어 위반율 >5%)이면 **F5 *제품화* 범위를 재검토**(코드 이식 자체를 차단하는 것이 아님)한다 (Charter §6 Discovery exit check / §9 A-3 No-go). 알고리즘 명세 SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md).

## 3. 포함되는 기능
> 본 마일스톤의 알고리즘 본체(Scorer/Collector/Eval)는 [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md)를 SSOT로 이식한다. 아래 workitem feature 문서(F-NNN)는 DISCOVERY feature(F1~F7)에 매핑된다.
- **F-001 (core-value)** — 결정론 *쌍 단위* 스코어링 + JD grounding 근거 + cap (게이트 핵심). = DISCOVERY F4·F6·F7. 데이터 계약·추출·매칭·검증·compute_fit·캐시·프롬프트·LLM 게이트웨이.
- **F-002 (collector)** — 토스·당근 수집 골격 + 도메인 인지 선택 + 신규/마감 diff. = DISCOVERY F1·F3. `crawler`.
- **F-003 (relative-ranking)** — listwise + pairwise + Bradley-Terry + 랭킹 모드(domain_fit_bt) + 도메인 우선순위 가드. = DISCOVERY F5 (A-3 시퀀싱은 §2 참조 — 이식 후 τ 측정).
- **F-004 (eval-harness)** — 불변식 회귀(GS-1) + 멀티-페르소나 진단 + 골든 페어 정확도(GS-2·GS-3 τ 프록시). technical-enabler — 게이트 측정 경로. `ai/eval`.
- (별도 분해 — 본 알고리즘 포트 비범위) F2 커버리지 투명성 패널 + 최소 피드(단일 리스트 + 밴드) — Feed UI surface(Next.js), `/plan-workitem`에서 별 feature로 분해.

> **분해 범위 경계 (정직 고지):** 현재 태스크 셋 **T-001~T-017**은 "**알고리즘 + 오프라인 평가**"까지를 *함수/JSONB 계약 + pytest 검증* 수준으로 이식한다(= 게이트 측정 가능한 코어). M1 §1의 "수집→스코어링→근거 표시가 *한 줄로 동작*"하는 **돌아가는 서비스**가 되려면 아래 *서비스 와이어링*이 추가로 필요하며, 이는 본 알고리즘 포트의 비범위로 후속 분해 대상이다:
> - **DB 스키마/영속** — `job_postings`·`ranking_runs.result`(JSONB) 등 Prisma 마이그레이션(`podo/apps/api`, TS) + worker의 실제 read/write 어댑터(현재 T-004/T-011은 dict/JSONB 계약까지).
> - **워커 엔트리 + 크론 트리거** — `ai/worker` 실행 진입점 + crawler `crawl-jobs` 매일 cron(GitHub Actions, ARCH §7-3). 현재 T-012는 fetch+upsert+diff *함수*까지, 스케줄 트리거 없음.
> - **API 서빙** — NestJS가 worker 산출 JSONB를 pass-through 서빙(ARCH §7-1). 비범위.
> - **Feed/커버리지 UI** — 위 F2/피드.
>
> 즉 T-001~T-017 완료 = "알고리즘·플로우·평가·프롬프트·캐시·수집·도메인선택이 빠짐없이, 캘리브레이션까지 보존된 채 검증됨". 제품 end-to-end는 위 와이어링 후속을 거쳐 완성된다.

## 4. 제외되는 기능
- 다채널 풀커버리지(7개+) — Charter §5 비목표.
- 자소서/이력서 자동작성·첨삭 — 비목표.
- 무응답 피드백 루프 자동화 / 절대 합격확률 % — 비목표.
- 일정·자동지원·협업 — 비목표.
- 직군 분기 스코어링 모델 — A-7 결과 의존, M1은 단일 모델로 시작(열린 질문).

## 5. 완료 기준 (graduation checklist)
> sprint contract: 본 마일스톤이 "done"이라고 합의되는 외부 검증 가능한 기준 (ADR-014).
- [ ] 모든 task status: done
- [ ] 통합 validate Pass
- [ ] E2E Pass (스택에 정의된 경우)
- [ ] AC 매핑 100% (validation report 기준)
- [ ] P0 severity finding 0건 (QA_FINDINGS의 본 마일스톤 헤더 기준)
- [ ] (선택) **게이트 실증:** 동일 (이력서, JD) 입력 N=10회 재채점 시 캐시 hit 변동 0 (GS-1) + 표본 ≥30 근거의 hallucinated requirement ≤2% (GS-2) 측정 경로가 동작한다.

## 6. 관련 문서
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§4 목표, §6 성공 기준)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§3 모듈, §3-1 의존성 규칙, §3-2 폴리글랏 매핑)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (Scorer·Collector·Eval 알고리즘 본체 — 이식 SSOT)
- Features: [F-001](../features/F-001-core-value.md) · [F-002](../features/F-002-collector.md) · [F-003](../features/F-003-relative-ranking.md) · [F-004](../features/F-004-eval-harness.md)
- ADR: [ADR-100](../../90-decisions/project/ADR-100-initial-project-decisions.md) (D1 게이트 우선, D3 결정론 캐시)

## 7. 열린 질문
- 스택 확정(ADR-101)·A-1 검증(크롤링 동작 확인, 2026-06-04) 완료 → task 분해 가능. 크롤링 방식(정적 httpx 우선 → 필요 시 headless)은 구현 시 확정.
- **A-1은 검증됨(2026-06-04 — 크롤링 실증).** 남은 A-3(상대 랭킹 τ)이 M1 구현 착수 전 선검증되어야 게이트 실증이 의미를 가짐 (DISCOVERY §12 / Charter §6 Discovery exit check). A-3 τ<0.6이면 F5(상대 랭킹) 범위 재검토.
- M1에 상대 랭킹(F5)을 포함할지 — A-3 τ<0.6이면 범위 재검토(ADR-100 D1 / Charter §9 A-3 No-go).
- 5단계 밴드 cut-off 미정(Charter §10) — 최소 피드의 밴드 표시 폭에 영향.

## 8. 회고 (stabilize 자동 채움)
> /stabilize-milestone M1 (2026-06-05). 졸업 가능 = YES. 본 단락은 회고 본문만 — status(## 0)는 변경 안 함(ADR-014: status 전이는 본 skill 책임 아님).
- 목표 달성도: **달성(졸업 가능 YES)**. T-001~T-017 done(17/17), 통합 validate exit 0(ruff·mypy strict·pytest 103 pass/1 skip), AC 매핑 52/52(100%), Evidence Bundle 신뢰도 High 17/17, P0 0. "수집→결정론 스코어링→근거" 코어 + 게이트 *측정 경로*(GS-1/GS-2/GS-3, T-014/016/017)가 캘리브레이션 보존 채로 이식·검증됨. 미완: *실데이터 게이트 수치*(실 LLM·창업자 라벨·100회 반복)와 서비스 와이어링(DB 영속·워커 엔트리·cron·API·Feed UI) — §3 분해 경계대로 후속 분해 대상.
- scope creep 사례: **없음.** T-001~T-017이 "알고리즘 + 오프라인 평가"(함수/JSONB 계약 + pytest) 경계를 벗어나지 않음. 서비스 와이어링·Feed UI는 §3에 비범위로 선고지된 대로 미착수.
- 비목표(charter §5) 위반 사례: **없음.** 다채널 풀커버리지(2곳 유지)·자소서 자동작성·절대 합격확률 %·직군 분기 모델·일정/자동지원 모두 미구현(밴드·상대 강도로 대체, 단일 모델 시작).
- 핵심 학습 (≤3):
  1. **게이트는 "측정 경로"와 "측정 수치"가 분리된다.** 경로는 LLM 없이 결정적으로 박을 수 있으나(GS-1/GS-2/GS-3 하니스), GS-2 `_is_grounded` 토큰 휴리스틱·GS2_MIN_SAMPLE 비강제·τ-a vs τ-b 같은 *oracle gap*은 실데이터 + 강제 로직으로만 닫힌다 — M2 최고 레버리지 후속(QA-M1-001/002/003, T-016/T-017).
  2. **검증된-포트의 1순위 silent-regression 위험은 흩어진 캘리브레이션 상수/함수다.** DOM_RANK·레벨 경계·BT prior·_extract_json·_load_prompt가 중복·무주석 상태 — GS-1 게이트가 못 잡는 무음 drift 표면. 상수/util SSOT 단일화 + WHY 주석이 가장 값싼 보강(REV-M1-001~007).
  3. **read-only 측정 레이어(eval)가 worker private 심볼에 고정 의존**하면 경계가 주석으로만 강제된다 — 공개 alias + 경계 ADR 필요(REV-M1-003). 더불어 위임 운영상: 광범위 qa 위임은 output-first 예산 제약이 없으면 finding 미출력으로 실패(본 라운드 instruction 개선 후보).
