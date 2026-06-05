# T-017-a3-tau-proxy

## 0. Status
draft

## 0-1. Type
research-spike

## 1. 작업 목적
Charter §6 Discovery exit check를 1회 실행한다: 개발 JD 8~10개에 대한 창업자 수기 상대 랭킹 vs 모델 랭킹의 Kendall τ(또는 자명 페어 위반율)를 측정해 A-3(상대 랭킹 타당도)을 판정한다. 이식된 랭커(F-001+F-003) + 골든 페어 지표(T-016)를 사용 (Charter §9 A-3 / M1 §2 A-3 시퀀싱).

## 2. 작업 범위
- 개발 JD 8~10개 수집(T-012/T-013) → 모델 랭킹 산출(T-011) → 창업자 수기 상대 랭킹 라벨링(골든 페어 패킷, T-016 `propose_pairs`/`load_pairs`) → Kendall τ(또는 pairwise agreement) + 자명 페어 위반율 산출.
- 판정: `τ≥0.7` 진행 / `0.6≤τ<0.7` 조건부+재실험 / `τ<0.6`(또는 자명 페어 위반율 >5%) → **F5 제품화 범위 재검토**(F-003 §12 / Charter §9 No-go).

## 3. 구현 항목
- `ai/eval/src/eval/a3_tau.py` — τ 계산(pairwise 라벨 → Kendall τ) + 자명 페어 위반율 + 판정 리포트.
- 리포트 산출(`ai/eval` read-only) — 결과를 DISCOVERY §14 Evidence Log 회수 대상으로 명시(plan은 DISCOVERY 직접 수정 X — `/discover-product --update` 경로).

## 3-T. 트러블슈팅 (Type=bugfix 일 때만 — 삭제)

## 4. 제외 항목
- 골든셋 대규모 확장(후속) · dedup 승격 · F5 제품 노출 결정(τ 결과 후 별도 판단).

## 4-1. 변경 예정 파일/경로
- `ai/eval/src/eval/a3_tau.py`, `ai/eval/tests/test_a3_tau.py`

## 5. 완료 조건
8~10개 개발 JD에 대해 모델 랭킹 vs 수기 랭킹 τ가 1회 산출되고, 임계값(τ≥0.6 또는 자명 페어 위반율 ≤5%) 충족 여부가 판정·기록된다.

## 6. Acceptance Criteria
- AC-1 [Given] 수기 라벨된 개발 JD 쌍 + 모델 랭킹 [When] `a3_tau` 실행 [Then] Kendall τ와 자명 페어 위반율을 산출하고 (진행/조건부/No-go) 판정 라벨을 리포트로 남긴다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/eval/tests/test_a3_tau.py::test_AC_1_tau_computation_and_verdict (τ 계산 함수는 합성 라벨로 단위 검증)

## 6-2. TDD opt-out
- 사유: 탐색적 측정 spike(1회 실데이터 판정 — 창업자 수기 라벨 필요, 결과 데이터 의존). τ *계산 함수*는 합성 입력으로 단위 테스트(AC-1)하되, 실데이터 1회 실행·판정은 탐색.
- Follow-up task: τ<0.6 또는 조건부 시 F5 범위 재검토 + 골든셋 확장 follow-up task(차기 라운드 `/plan-workitem`에서 생성).

## 7. 관련 문서
- Milestone: [M1-foundation](../milestones/M1-foundation.md) (§2 A-3 시퀀싱, §7 열린 질문)
- Feature: [F-004-eval-harness](../features/F-004-eval-harness.md) (+ [F-003](../features/F-003-relative-ranking.md) 측정 대상)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§6 Discovery exit check, §9 A-3 No-go)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC §10-3](../../20-system/SCORING_PIPELINE_SPEC.md)

## 8. 메모
산출은 리서치 노트/판정 리포트(ADR-040 정신). 결과는 DISCOVERY Evidence Log로 회수 권장(`/discover-product --update`). M1 §2 재해석: 코드 이식은 선행, τ는 *제품화* 게이트.

## 9. 의존성
- depends_on: [T-016]
- read_set: ["ai/eval/src/eval/golden_pairs.py", "ai/worker/**"]
- write_set: ["ai/eval/src/eval/a3_tau.py", "ai/eval/tests/test_a3_tau.py"]
- verifier: "uv run pytest ai/eval/tests/test_a3_tau.py"
