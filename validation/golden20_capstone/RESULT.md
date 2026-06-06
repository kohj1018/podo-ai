# 20-pair golden eval (capstone) — podo-ai LIVE

**Result: 19/20 strict, 20/20 tie-aware** (prototype baseline 16/20). All 20 scored, 0 unavailable, 0 pending.

| persona | strict |
|---|---|
| junior_frontend | 5/6 |
| devops_infra_security | 6/6 |
| ai_ml_application | 4/4 |
| backend_platform | 4/4 |
| **STRICT total** | **19/20 (0.95)** |
| tie-aware total | 20/20 |

Artifacts in this dir: `runner.py` (harness), `detail.json` (per-pair), `result.txt` (full report).

## 재현 (결정적, ~무료 — 캐시 히트)

```
# 레포 루트에서:
python validation/golden20_capstone/runner.py
```
첫 실행만 LLM 라이브(`.cache/llm`에 박힘), 이후는 캐시 히트로 결정적. 프로토타입 레포 경로는
`PROTOTYPE_ROOT` env로 override (기본 = dev-practice/podo-algorithm-test).

## 메트릭 정합성 — 4 체크포인트 (runner.py 기준)

1. **METRIC 동일** — podo-ai `eval.golden_pairs.load_pairs` + `evaluate_pairs`를 그대로 사용
   (runner `import` + `evaluate_pairs(...)` 호출). strict = A_better/B_better를 **rank**로 판정,
   tie-aware = `fit_level` 동일. 프로토타입 이식본과 같은 정의(eval/golden_pairs.py L238–317).
2. **LIVE** — `worker.pipeline.run_scoring(resume, jobs, ranking_mode="domain_fit_bt")` 실호출.
   오프라인 `rescore_persona`(캐시 산출물 재계산=프로토타입 숫자 베끼기) **아님**.
3. **MAPPING** — 쌍을 `persona`별로 그룹화(`by_persona`)해 각 쌍을 **자기 persona 랭킹**으로 채점.
4. **NO LEAK / 전수** — `expected_winner`는 `label`로 채점에만 사용, `run_scoring` 입력은 resume+jobs뿐.
   20쌍 전부 집계, `unavailable`/`pending` 명시(이번엔 0).

## 정직한 해석 (over-claim 금지)

- 이건 **단일 frozen draw 점추정**입니다. "포트가 16→19로 더 좋아졌다"는 주장이 아닙니다 —
  19 vs 16 차이엔 샘플링 노이즈 + 충실성 수정(M2·max_tokens·JSON_SYSTEM 복원) + 모델 시점이 섞임.
  정확한 읽기: **"동일한 높은 밴드 — 저하 없음"**, 잔여(H4·M3) 무해 실증.
- 유일한 strict 오답 `prop-junior_frontend-05`: daangn-7689088003 vs 6692173003 — **둘 다 fit 3 / strong
  도메인**(동률 밴드). tie-aware로는 정답(그래서 20/20). 실패 유형 `same_domain_close`는
  PORTING_GUIDE가 기록한 프로토타입 오류 4건의 유형과 동일 → **새 실패 모드 아님**.
- 19/20은 15~17 밴드를 상회 → 종결(추가 draw 불필요). 만약 ≤13이었다면 `LLM_CACHE_REFRESH=1`로
  2~3 draw 더 떠 분포 확인 후 H4/M3 판단했을 것.

입력 데이터(인간 라벨/이력서/raw JD)는 프로토타입 레포(podo-algorithm-test) 소유 —
이 capstone은 일회성 충실성 검증이며, podo-ai의 영구 골든셋은 별도 구축 대상(PORTING_GUIDE §6).
