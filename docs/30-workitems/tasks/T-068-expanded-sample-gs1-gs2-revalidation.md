# T-068-expanded-sample-gs1-gs2-revalidation

## 0. Status
done

## 0-1. Type
research-spike

## 1. 작업 목적
F-020(커버리지 확대)·F-021(벡터/비용)·F-022(도메인 분류)로 확대된 입력(다종 회사 JD × 다종 이력서) 위에서 **GS-1(결정성)·GS-2(근거 사실성 ≤2%) 게이트가 보존되는지 재실측**하고, **도메인 분류 정확도(F-022)**를 다종 직군 이력서 표본으로 측정한다. JD 종류 폭증은 hallucination 표면을 키우며 F-021 비용 최적화가 결정성을 흔들 수 있으므로 *회귀 가드*가 필요하다(F-023 §2 기술 근거).

## 2. 작업 범위
- **확대 표본 구성**: 다종 이력서(프론트/백엔드/데이터/풀스택 ≥4종) × 다종 JD(네카라쿠배·외국계·스타트업·기존 토스/당근 포함 ≥5개사 출처)로 평가 fixture 구성.
- **GS-1 재측정 하니스 확장**: 기존 `ai/eval/src/eval/gates.py`의 `GS1Gate`를 확대 표본에 대해 실행(N=10회 반복 hit/miss, 동일 입력 변동 0 판정). **F-021(벡터 선별) 도입 이후에도 결정성 보존 확인 포함.**
- **GS-2 재측정 하니스 확장**: 기존 `GS2Gate`를 확대 JD 표본(≥30개 근거 항목)에 대해 실행(hallucinated requirement 비율 측정·≤2% 판정).
- **도메인 분류 정확도 측정**: 다종 직군 이력서 fixture에 대해 T-066 `classify_domains()` 결과 vs 수기 라벨 비교(정확도 %).
- 측정 결과를 `ai/eval/reports/m5_gs_revalidation.json` 산출(DISCOVERY §14 Evidence Log 회수 대상 명시).

## 3. 구현 항목
1. `ai/eval/fixtures/m5_expanded/` 디렉토리 — 신설. 서브디렉토리:
   - `resumes/`: 프론트·백엔드·데이터·풀스택 각 이력서 JSON fixture(저장 산출물 형식, T-016 패턴 준용).
   - `jds/`: ≥5개사 출처 JD fixture(제목·role_family·tech_stack·raw_text 포함). → 확인: 디렉토리 존재 + 파일 수 assert (AC-1)
2. `ai/eval/src/eval/gates.py` — 기존 `GS1Gate`·`GS2Gate`에 `fixture_dir` 파라미터 추가(기존 기본 fixture 유지). → 확인: 기존 테스트 회귀 없음 (AC-1)
3. `ai/eval/src/eval/m5_validation.py` — 신설. `run_m5_gs_validation(fixture_dir) -> M5GsReport`:
   - `GS1Gate(fixture_dir=m5_expanded).measure()` → `gs1_result`.
   - `GS2Gate(fixture_dir=m5_expanded, min_sample=30).measure()` → `gs2_result`.
   - `domain_accuracy = compute_domain_accuracy(resumes_fixture, labels)` → `domain_result`.
   - 결과 serialize → `ai/eval/reports/m5_gs_revalidation.json`.
4. `ai/eval/src/eval/m5_validation.py` — `compute_domain_accuracy(resumes, labels: dict) -> float`: `classify_domains()` 결과 vs 수기 라벨(직군 매핑 파일 `labels.json`).
5. 수기 라벨 파일 `ai/eval/fixtures/m5_expanded/domain_labels.json` — `{resume_id: "backend"|"frontend"|"data"|"fullstack"}` 형식. 사용자/창업자 입력 필요(placeholder 포함, builder가 사용자 라벨 입력 안내 텍스트 README 추가).
6. `ai/eval/tests/test_m5_validation.py` — 신설. AC-1~AC-3 커버(fixture 기반, GS 판정 함수 단위, domain_accuracy 계산). → 확인: pytest pass (AC-1, AC-2, AC-3)

## 4. 제외 항목
- 비용 최적화 전/후 비교 측정 — T-069.
- A-3 τ 실데이터 — T-069.
- GS-3 실데이터(실 서류통과 결과) — M6 배포 후.
- 표본 자동 라벨링 — Charter §5 비목표.

## 4-1. 변경 예정 파일/경로
- `ai/eval/fixtures/m5_expanded/` (신설 디렉토리)
- `ai/eval/src/eval/gates.py` (fixture_dir 파라미터 추가)
- `ai/eval/src/eval/m5_validation.py` (신설)
- `ai/eval/reports/m5_gs_revalidation.json` (산출 — gitignore 여부 확인)
- `ai/eval/tests/test_m5_validation.py` (신설)

## 5. 완료 조건
확대 표본에서 GS-1(변동 0)·GS-2(hallucination ≤2%)가 재측정·판정되고, 도메인 분류 정확도가 다종 직군 이력서 표본에서 산출된다. 결과는 `m5_gs_revalidation.json`에 기록된다.

## 6. Acceptance Criteria
- AC-1 [Given] 확대 fixture(다종 이력서 ≥4종 × JD ≥5개사) [When] `GS1Gate` 실행 [Then] 동일 입력 N=10회 결과 변동 0이 확인되고 gate_pass 판정이 기록된다(F-021 벡터 선별 포함 이후에도 결정성 보존).
- AC-2 [Given] 확대 JD 표본(근거 항목 ≥30개, 사람 라벨) [When] `GS2Gate` 실행 [Then] hallucinated requirement 비율이 산출되고 ≤2% 충족 여부 gate_pass/gate_fail 판정이 기록된다.
- AC-3 [Given] 다종 직군 이력서 fixture + 수기 도메인 라벨 [When] `compute_domain_accuracy()` 실행 [Then] 분류 정확도(%)가 산출되고 `m5_gs_revalidation.json`에 기록된다.
- AC-4 [Given] 동일 이력서를 백엔드 vs 데이터로 분류한 두 경우 + 동일 JD 집합 [When] 채점(`domain_alignment`→fit) [Then] 분류에 따라 `domain_alignment`/fit_level/상대 랭킹이 달라진다(도메인 분류가 *실제 fit/랭킹*에 반영됨을 회귀로 확인 — F-022 FAC-2, 분류 output만이 아니라 downstream 효과).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/eval/tests/test_m5_validation.py::test_AC_1_gs1_expanded_fixture_determinism
- AC-2 → pytest::ai/eval/tests/test_m5_validation.py::test_AC_2_gs2_expanded_hallucination_gate
- AC-3 → pytest::ai/eval/tests/test_m5_validation.py::test_AC_3_domain_accuracy_computation
- AC-4 → pytest::ai/eval/tests/test_m5_validation.py::test_AC_4_domain_classification_changes_ranking

## 6-2. TDD opt-out
- 사유: 탐색적 측정 spike(확대 표본 fixture 구성 + 실 측정 결과 의존). 하니스 함수 단위(GS 판정·domain_accuracy 계산)는 합성 fixture로 TDD 적용. 실 fixture 기반 full run은 사용자 라벨 입력 후 1회 실행.
- Follow-up task: GS-2 gate_fail 또는 도메인 분류 정확도 낮음 → F-021/F-022 보강 후 재측정(T-069 또는 차기 라운드 생성).

## 7. 관련 문서
- Milestone: [M5-coverage-and-algorithm](../milestones/M5-coverage-and-algorithm.md)
- Feature: [F-023-expanded-fit-validation](../features/F-023-expanded-fit-validation.md)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§6 GS-1/GS-2)
- Discovery: [DISCOVERY](../../10-charter/DISCOVERY.md) (§12 A-9·A-12, §14 Evidence Log)

## 8. 메모
- `ai/eval/reports/` gitignore 여부 — 기존 M1/M3 패턴 확인 후 동일 처리(산출 리포트는 DISCOVERY §14로 회수 권장).
- GS-2 표본 ≥30 근거 항목 확보 — 확대 JD × 다종 이력서 조합으로 자연 달성 가능하나, 부족 시 추가 JD fixture 필요(사용자 안내).
- 열린 질문: 도메인 분류 정확도 기준(합격 임계값 미정 — 이번 측정이 베이스라인 수립, No-go 임계값은 T-069 이후 설정).

## 9. 의존성
- depends_on: [T-064, T-065, T-066]  # T-063(소스 확대)은 선행 불요 — 확대 표본은 `ai/eval/fixtures/m5_expanded/`의 *큐레이션 수기 fixture*(라이브 collector 출력 아님), 결정적 측정 위해 독립.
- read_set: ["ai/eval/src/eval/gates.py", "ai/eval/src/eval/golden_pairs.py", "ai/worker/src/worker/domain_classifier.py"]
- write_set: ["ai/eval/fixtures/m5_expanded/**", "ai/eval/src/eval/gates.py", "ai/eval/src/eval/m5_validation.py", "ai/eval/tests/test_m5_validation.py"]
- assumptions: ["T-064·T-065·T-066 완료(벡터 선별·도메인 분류 구현됨)", "사용자가 domain_labels.json 수기 라벨 입력 가능"]
- verifier: "uv run pytest ai/eval/tests/test_m5_validation.py"
