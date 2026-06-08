# M5 확대 표본 fixture (T-068)

GS-1(결정성)·GS-2(근거 사실성)·도메인 분류 정확도 재측정용 *큐레이션 합성* 표본.
라이브 collector 출력이 아니라 결정적 측정을 위한 수기 fixture다(독립성 — T-068 §9).

## 구성
- `resumes/` — 직군별 합성 이력서(backend/frontend/data/fullstack). `resume.evidence[].domain`이 1차 분류 신호.
- `jds/` — ≥5개사 출처 JD(role_family + raw_text + `requirements[]`). requirements 합계 ≥30(GS-2 표본).
- `domain_labels.json` — `{resume_id: 직군}` 수기 라벨. 합성 fixture는 저자가 확정함.

## 실 이력서 추가 시 (사용자/창업자 입력)
1. `resumes/<id>.json`에 이력서 fixture 추가(위 형식; `resume.evidence`에 domain/skills 채움).
2. `domain_labels.json`에 `"<resume_id>": "backend|frontend|data|fullstack"` 수기 라벨 추가.
3. `uv run python -m eval.m5_validation` 또는 `run_m5_gs_validation()` 실행 → `ai/eval/reports/m5_gs_revalidation.json` 산출.

분류 정확도 *합격 임계값*은 미정(이번 측정이 베이스라인 — No-go 임계는 T-069 이후 설정).
