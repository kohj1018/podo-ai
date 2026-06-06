# T-040-pii-safety-pass

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
milestone §5 **PII Safety Pass(졸업 게이트)**를 단일 task로 집행한다 — 알려진 PII를 포함한 fixture 이력서를 업로드→마스킹(T-036)→채점(T-037)한 뒤, raw PII가 **전 표면 6곳**(`resumes.content`·`ranking_runs.result`·`recommendations`·애플리케이션 로그·`.cache/llm`·커밋 웜캐시 `ai/worker/fixtures/llm_cache`)에 0건임을 literal scan으로 검증한다. (repair-plan: 기존 T-036 controlled-surface scan + T-037 downstream scan을 본 task로 통합 — PII 안전 게이트를 한 곳에서 일관 집행하고 T-036 sizing 해소.)

## 2. 작업 범위
- 알려진 PII fixture 이력서(이름·이메일·전화·주민번호·개인 URL).
- 업로드(T-034)→마스킹(T-036)→채점(T-037) 파이프라인 구동 후 6표면 literal scan = 0 검증.
- 커밋 웜캐시는 마스킹 fixture로만 생성(실 PII 금지) 불변식 점검.

## 3. 구현 항목
1. `ai/tests/fixtures/pii_resume.txt`(또는 JSON) — 현재: 없음 → 변경: 알려진 PII 값(이름 "홍길동"·email "hong@example.com"·phone "010-1234-5678"·주민번호 "900101-1234567"·개인 URL) + 스택/학교/기간 evidence를 포함한 fixture. → 확인: fixture 로드. (AC-1)
2. `ai/tests/test_pii_safety.py`(신규) — 현재: 없음 → 변경: fixture를 (a) T-034 업로드로 마스킹 저장 → (b) T-037 `run(resume_id)` 채점 → (c) 6표면 literal scan:
   - `resumes.content`(DB) · `ranking_runs.result`(JSONB 전문) · `recommendations`(스칼라 — parity scan) · 애플리케이션 로그(캡처) · `.cache/llm` 파일 내용 · 커밋 웜캐시 `ai/worker/fixtures/llm_cache/*.json` 내용.
   - 각 표면에서 fixture PII 값(이름·email·phone·주민번호·URL) 0건 assert. → 확인: 6표면 모두 0. (AC-1)
3. 커밋 웜캐시 생성 불변식 — 현재: M2 웜캐시는 seed 기반 → 변경: 본 scan용 캐시는 마스킹 fixture로 생성(실 PII 금지)임을 테스트 주석·docstring에 명시(stabilize가 `pnpm e2e:warm` 재생성 시 동일 원칙). → 확인: 커밋 웜캐시 표면 scan 0(=실 PII 미혼입). (AC-1)

## 4. 제외 항목
- 마스킹 로직 구현(T-036). · 스코어링 연결(T-037). · 업로드 엔드포인트(T-034). · `scripts/e2e.mjs` 재배선·웜캐시 *재생성* 자체(stabilize-milestone M3 — feature 비범위; 본 task는 *검증*만). · 간접 재식별(M4).

## 4-1. 변경 예정 파일/경로
<!-- 구현 시점에 채운다. -->

## 5. 완료 조건
알려진 PII fixture를 업로드→마스킹→채점한 뒤 6개 표면 어디에도 raw PII가 0건이고, 커밋 웜캐시가 실 PII로 오염되지 않았음이 검증된다.

## 6. Acceptance Criteria
- AC-1 [Given] 알려진 PII(이름·이메일·전화·주민번호·개인 URL)를 포함한 fixture 이력서 [When] 업로드(T-034)→마스킹(T-036)→채점(T-037) 후 milestone §5 전 표면(`resumes.content`·`ranking_runs.result`·`recommendations`·애플리케이션 로그·`.cache/llm`·커밋 웜캐시 `ai/worker/fixtures/llm_cache`)을 literal scan [Then] fixture PII 값이 6표면 모두에서 0건이다.

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → pytest::ai/tests/test_pii_safety.py::test_AC_1_all_surfaces_literal_scan_zero

## 6-2. TDD opt-out
<!-- TDD 적용 — fixture PII는 마스킹 전 표면에 존재(red), 마스킹/채점 파이프 통과 후 0(green). DATABASE_URL 주입 통합. -->

## 7. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md) (§5 PII Safety Pass — 졸업 게이트)
- Feature: [F-014-resume-parse-pii](../features/F-014-resume-parse-pii.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§8 보안 PII)
- ADR: ADR-105 (T-036 신설 — 마스킹 정책·Safety Pass 기준)

## 8. 메모
- 해석 확정(PII Safety 통합): milestone §5 6표면 scan을 본 단일 task가 집행(repair-plan 2026-06-07 — 기존 T-036:AC-2 controlled + T-037:AC-2 downstream 통합). F-014 §7-1: FAC-1 → T-040:AC-1(+ T-036:AC-1 마스킹 제거가 이를 뒷받침).
- 커밋 웜캐시 *재생성*(seed→마스킹 fixture)은 stabilize-milestone M3 책임(M2 패턴); 본 task는 그 결과를 *검증*만(실 PII 0).

## 9. 의존성
- depends_on: [T-034, T-036, T-037]   # 업로드+마스킹+채점이 다 돌아야 6표면이 채워짐
- read_set: ["podo/apps/api/src/resumes/**", "ai/worker/src/worker/**"]
- write_set: ["ai/tests/test_pii_safety.py", "ai/tests/fixtures/pii_resume.txt"]
- assumptions: ["T-034 업로드·T-036 마스킹·T-037 채점 가능", "DATABASE_URL 주입"]
- verifier: "uv run pytest ai/tests/test_pii_safety.py"
