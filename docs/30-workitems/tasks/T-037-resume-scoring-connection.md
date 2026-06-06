# T-037-resume-scoring-connection

## 0. Status
done

## 0-1. Type
feature

## 1. 작업 목적
업로드·마스킹된 이력서(`resumes` 행, `resume_id`)를 기존 `parse_resume` → 스코어링 루프에 연결한다 — worker가 config 합성 seed가 아니라 **DB의 대상 이력서를 읽어** evidence 추출·채점하고 `ranking_runs`/`recommendations`를 그 `resume_id`로 영속하게 한다. 알고리즘 본체는 불변(SPEC §9-4 parse_resume 경로, 입력 소스만 교체). UI "분석 시작"이 기동할 **스코어링 트리거 엔드포인트**(`POST /api/v1/resumes/:id/score`)도 본 task가 정의한다(repair-plan P1 — T-039 ambiguity 해소). (전 표면 PII Safety scan은 신규 **T-040**으로 통합.)

## 2. 작업 범위
- `ai/worker/src/worker/__main__.py` `run()`이 선택적 `resume_id`로 DB 이력서를 채점하도록 확장(부재 시 기존 seed 경로 — keyless E2E 보존).
- DB `resumes.content`(마스킹본) → `Resume` 빌드 → `run_scoring` → `persist_run`.
- **스코어링 트리거 엔드포인트** `POST /api/v1/resumes/:id/score`(NestJS) — resume_id로 worker 채점 기동(M3 로컬: `python -m worker --resume-id N` subprocess). (전 표면 PII scan은 T-040.)

## 3. 구현 항목
1. `ai/worker/src/worker/persistence.py` 부근(또는 신규 `load_resume`) — 현재: `load_jobs`만 DB read, resume는 config seed → 변경: `load_resume(conn, resume_id) -> Resume`: `SELECT content FROM resumes WHERE id=%s` → `Resume(raw_text=content, primary_domains=..., secondary_domains=...)`. 도메인은 config USER_DOMAINS 기본(§8 열린질문). → 확인: 주어진 resume_id의 마스킹본 로드. (AC-1)
2. `ai/worker/src/worker/__main__.py:42` `run()` — 현재: `resume = config.load_seed_resume()` 고정 → 변경: `def run(conn, *, resume_id=None, ...)`: `resume_id`면 `load_resume(conn, resume_id)` + 그 id 사용, 아니면 기존 `_ensure_seed_resume`(seed). `main()`은 `--resume-id` argv/env 수용. → 확인: `python -m worker --resume-id N`이 N번 이력서로 `ranking_runs`(resume_id=N) 영속. (AC-1)
3. parse 연결 검증 — 현재: `run_scoring`이 `parse_resume.extract_evidence`(LLM) + `extract_skills_evidence` 호출 → 변경: 없음(마스킹본도 동일 경로). → 확인: 마스킹본 입력 시 `evidence_count > 0`(스택/학교 보존 — T-036 AC-3 정합). (AC-1)
4. `podo/apps/api/src/resumes/resumes.controller.ts` + `resumes.service.ts`(T-034 산출 확장) — 현재: 업로드만 → 변경: `POST /api/v1/resumes/:id/score` 추가 — resume_id로 worker 채점 기동. M3 로컬: NestJS `child_process`로 `python -m worker --resume-id N` 실행 후 완료 시 200(에러는 §7-1 envelope). → 확인: 엔드포인트 호출 → 해당 resume_id의 `ranking_runs` 생성. (AC-2) **⚠ NestJS→Python 프로세스 경계 = architect 호출 권장**(§8).

## 4. 제외 항목
- 마스킹 로직(T-036). · 업로드 엔드포인트(T-034). · UI "분석 시작" onClick·feed 렌더(T-039 — 본 task는 트리거 *엔드포인트*까지). · 하류 PII scan(T-040). · 알고리즘/캐시 키 재설계(SPEC 불변). · 도메인 자동분류 모델(§8 — M3는 config 기본).

## 4-1. 변경 예정 파일/경로
- `ai/worker/src/worker/persistence.py` — `load_resume(conn, resume_id)` 추가(마스킹본 → Resume) + Resume import
- `ai/worker/src/worker/__main__.py` — `run(resume_id=None)` 분기(부재=seed 경로 보존) + `main()` `--resume-id` argv/env 파싱
- `ai/worker/tests/test_main.py` (신규) — AC-1: DB 마스킹 이력서 채점 + evidence>0 + ranking_runs(resume_id)
- `podo/apps/api/src/resumes/worker-runner.port.ts` (신규, write_set 이탈) — WorkerRunner port + SubprocessWorkerRunner(`uv run python -m worker --resume-id`)
- `podo/apps/api/src/resumes/resumes.service.ts` — `score(resumeId)` + WorkerRunner 주입
- `podo/apps/api/src/resumes/resumes.controller.ts` — `POST /api/v1/resumes/:id/score`
- `podo/apps/api/src/resumes/resumes.module.ts` (write_set 이탈) — WorkerRunner provider 배선
- `podo/apps/api/test/resumes.spec.ts` (§6-1 지정, write_set 이탈) — AC-2 트리거 + 404; T-034 AC-1 생성자 3인자화

## 5. 완료 조건
worker가 DB의 마스킹 이력서(resume_id)를 읽어 채점하고 그 resume_id로 결과를 영속하며, 채점 후 하류 표면 어디에도 PII가 남지 않는다.

## 6. Acceptance Criteria
- AC-1 [Given] `resumes`에 마스킹본 이력서 행(resume_id=N) [When] `run(conn, resume_id=N)` 채점 [Then] 그 이력서로 `parse_resume`가 `evidence_count > 0`을 추출하고 `ranking_runs`(resume_id=N) + `recommendations`가 영속된다(seed 경로는 resume_id 미지정 시 보존).
- AC-2 [Given] `resumes`에 이력서 행 [When] `POST /api/v1/resumes/:id/score` 호출 [Then] 해당 resume_id로 worker 채점이 기동되어 `ranking_runs`(resume_id) + `recommendations`가 생성되고 200을 응답한다(M3 로컬: NestJS→`python -m worker --resume-id` subprocess).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/worker/tests/test_main.py::test_AC_1_scores_db_resume_by_id_evidence_present
- AC-2 → vitest::podo/apps/api/test/resumes.spec.ts::test_AC_2_score_endpoint_triggers_ranking_run

## 6-2. TDD opt-out
<!-- TDD 적용 — fake call_fn 주입(무키)으로 결정적 채점(M2 패턴). DB 표면 scan은 DATABASE_URL 주입 통합. -->

## 7. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md) (§5 E2E·PII Safety Pass)
- Feature: [F-014-resume-parse-pii](../features/F-014-resume-parse-pii.md)
- Algorithm SSOT: [SCORING_PIPELINE_SPEC](../../20-system/SCORING_PIPELINE_SPEC.md) (§9-4 parse_resume 경로 — 입력 소스만 교체)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: ADR-105 (T-036 신설 — 마스킹 불변식)

## 8. 메모
- 해석 확정: worker `run()`에 `resume_id` 선택 인자 추가(부재 시 seed — M2 keyless E2E `python -m worker` 보존). 업로드 이력서 채점 = resume_id 경유.
- 해석 확정(스코어링 트리거 — repair-plan P1): `POST /api/v1/resumes/:id/score`(NestJS) → `python -m worker --resume-id N` subprocess(M3 로컬 단일사용자 최소안). 큐/폴링은 M4 배포 시 재검토.
- 해석 확정(PII Safety 통합): 하류 scan은 본 task에서 분리 → 신규 T-040(PII Safety Pass)이 전 6표면 일괄 검증. F-014 §7-1: FAC-1 → T-040:AC-1 + T-036:AC-1; FAC-3 → 본 task AC-1.
- 열린 질문(도메인): 업로드 이력서의 primary/secondary domains — M3는 config USER_DOMAINS 기본값 사용(자동 분류 비범위). ADR-105 또는 후속 재검토.
- repair-plan 2026-06-07 [default] P1 Plan-ambiguity(T-039:AC-1): Adopt — 스코어링 트리거를 본 task에 확정(엔드포인트 + worker resume_id); 기존 하류 scan AC-2를 트리거 AC로 교체, scan은 T-040 이관.
- architect 호출 권장: NestJS→Python subprocess(새 프로세스 경계, cross-stack — ADR-007 자동호출 X, 텍스트 제안만).
- 구현 결정(2026-06-07): 경계 설계를 메인 세션에서 분석(별도 architect agent 미호출 — plan이 sync subprocess+완료 시 200을 이미 확정, scripts/e2e.mjs phase4 `uv run python -m worker`가 검증된 호출 템플릿). **3계층 검증**: AC-1(Python `run(resume_id)`)이 ranking_run 생성을, AC-2(TS, fake WorkerRunner)가 엔드포인트 트리거 계약을, stabilize E2E가 실 subprocess를 실증. WorkerRunner port(DI)로 테스트 주입 가능하게 함.
- write_set 이탈(필요 산출): `worker-runner.port.ts`(신규 port)·`resumes.module.ts`(provider 배선)·`resumes.spec.ts`(§6-1 AC-2 지정). plan §9 write_set이 이들을 누락 — 트리거 구현·DI·테스트에 기계적으로 필요. 상위 문서 후행 갱신 필요(WORKFLOW 4-A): ARCH §7-3에 NestJS→Python worker 트리거 subprocess 패턴 미기재 → P1 [Arch-iface-7-3] 후속(§7-3 본문 또는 ADR; T-034 §7-1 sync와 함께 stabilize-M3 doc-sync로 회수).

## 9. 의존성
- depends_on: [T-036, T-034]   # 마스킹 구현 + 업로드로 resumes에 마스킹본; 트리거 엔드포인트는 T-034 ResumesModule 확장(cross-stack)
- read_set: ["ai/worker/src/worker/pipeline.py", "ai/worker/src/worker/parse_resume.py", "docs/20-system/SCORING_PIPELINE_SPEC.md"]
- write_set: ["ai/worker/src/worker/__main__.py", "ai/worker/src/worker/persistence.py", "ai/worker/tests/test_main.py", "podo/apps/api/src/resumes/resumes.controller.ts", "podo/apps/api/src/resumes/resumes.service.ts"]
- assumptions: ["T-036 마스킹 + T-034 업로드로 resumes에 마스킹 이력서 존재"]
- verifier: "uv run pytest ai/worker/tests/ && pnpm --filter @podo/api test"
