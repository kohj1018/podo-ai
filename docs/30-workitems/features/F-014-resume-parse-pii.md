# F-014-resume-parse-pii: 직접 식별자 마스킹 + 기존 parse_resume 연결

## 0. Status
draft

## 0-1. Type
feature

## 1. 요약
업로드된 이력서 원문(raw text)에서 **직접 식별자(이름·이메일·전화·생년·주소·개인 URL)**를 *메모리에서* 제거(마스킹)한 뒤, 마스킹본만 기존 `parse_resume` 경로로 파싱·저장·LLM에 전송한다. **raw PII가 DB(`resumes.content`)·`ranking_runs.result`·`recommendations`·애플리케이션 로그·LLM cache(`.cache/llm`·커밋 웜캐시) 어디에도 흐르지 않는다** — M3 핵심 안전 불변식. 마스킹은 regex/rule-based만. raw PII를 외부(스코어링) LLM에 보내는 탐지 경로는 금지. ADR-105(PII 정책) 신설.

근거 insight: I-1 (DISCOVERY §15)

## 2. 사용자 가치 (User Story)
- As a **유진(신입/졸업예정 개발자 구직자)**, I want my resume to be anonymized before it is stored or analyzed, so that my personal identifiers (name, email, phone, etc.) are never persisted or sent to external services.

## 3. 핵심 시나리오 (Feature-level)
### Happy path
1. 업로드 원문 텍스트가 NestJS ResumesService 내 마스킹 단계로 진입(작업 가정: NestJS TS regex — `resumes.content` DB write 전 메모리에서 마스킹; 최종 런타임 위치는 ADR-105 확정).
2. 정규식 패턴셋으로 이메일·전화·주민번호 패턴·URL(개인) 제거 → 플레이스홀더(`[MASKED_EMAIL]` 등) 치환.
3. 이름은 regex 한계상 best-effort 제거(영문 이름 패턴, 한글 2~4자 패턴) → preview에서 사용자 확인으로 보완.
4. 학교·회사·프로젝트·스택·경력기간·성과 수치는 *evidence로 유지*(과마스킹 방지).
5. 마스킹본을 `resumes.content`에 저장 → `parse_resume` 파이프로 전달 → evidence 추출 → 스코어링 루프 연결.
### Alternate path
1. 마스킹 후 evidence 개수가 0 → "이력서에서 기술/경력 정보를 추출하지 못했습니다. 다시 업로드하세요." 400 반환.
### Fail path
1. 🔴 raw PII가 마스킹 전에 DB·로그·LLM cache에 흘러나감 → PII Safety Pass 실패(치명). M3 안전 불변식 위반.
2. 🔴 학교·스택·경력기간이 마스킹으로 제거됨 → evidence 급감 → GS-2 grounding 약화.

## 4. 범위
- **마스킹 모듈** (작업 가정: NestJS 경계 TS regex — raw가 `resumes.content` DB write 전 메모리에서 마스킹돼야 함, §12·F-013 §12와 정합; 최종 런타임 위치(NestJS TS vs ai/core Python)·모듈 경로는 ADR-105에서 확정): regex 패턴셋 — 이메일(`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]{2,}`), 전화(`01[0-9]-\d{4}-\d{4}` 등), 주민번호 패턴, 개인 URL(`github.com/<user>` 제외 일반 URL은 선별), 이름(best-effort 패턴). 플레이스홀더 치환.
- **`parse_resume` 연결** — SCORING_PIPELINE_SPEC §9-4 `parse_resume` 경로에 마스킹본을 입력으로 주입. 알고리즘 본체 불변.
- **ADR-105 신설** — PII 마스킹 정책(대상 식별자·마스킹 방식·경계·책임 분배·간접 재식별 방어 한계 명문화).
- **PII Safety Pass 검증 fixture** — 알려진 PII 값(이름·email·phone 등)을 포함한 test fixture → 마스킹 후 milestone §5 PII Safety Pass의 전 표면(`resumes.content`·`ranking_runs.result`·`recommendations`·애플리케이션 로그·`.cache/llm`·커밋 웜캐시 `ai/worker/fixtures/llm_cache`)을 literal scan으로 0건 확인하는 pytest.

## 5. 비범위
- raw PII를 외부 LLM에 보내는 NER 탐지.
- 로컬 인메모리 NER 모델 (M3 비범위, 필요 시 M4).
- 간접 재식별 방어 (학교+회사+재직기간 조합) — M4(공개 배포 시) 재검토.
- 이력서 evidence 행단위 편집 UI.

## 6. 요구사항
- 마스킹 후 email/phone/주민번호/개인 URL이 **FAC-1 전 표면**(`resumes.content`·`ranking_runs.result`·`recommendations`·로그·`.cache/llm`·커밋 웜캐시)에 잔존하지 않음(fixture scan 0건).
- 이름은 best-effort — fixture scan 0건 목표이나, 자연어 문맥 내 이름은 false-negative 가능(preview 보완).
- 학교·회사명·스택(Python, Java 등)·경력 기간·수치는 보존.
- 마스킹본이 `resumes.content`에만 저장 (raw 컬럼 없음).
- ADR-105 신설: 마스킹 대상·방식·책임 경계 명문화.
- schema-contract 테스트 영향 없음 (이미 F-013이 컬럼 추가 — F-014는 데이터 흐름만).

## 7. Feature-level Acceptance Criteria
- **FAC-1:** 알려진 PII(이름·이메일·전화·주민번호 형식·개인 URL)를 포함한 fixture 이력서를 마스킹 후 milestone §5 PII Safety Pass의 **전 표면**을 literal scan했을 때 fixture PII 값 0건: `resumes.content` / **`ranking_runs.result`(opaque JSONB — resume evidence 인용이 실리는 주 누출 표면)** / `recommendations`(scalar projection) / 애플리케이션 로그 / LLM cache(`.cache/llm` + 커밋 웜캐시 `ai/worker/fixtures/llm_cache`). 커밋 웜캐시는 마스킹 fixture로만 생성(실 PII 금지).
- **FAC-2:** 학교명·스택 기술어(Python, TypeScript 등)·경력 기간 수치가 마스킹 후에도 마스킹본에 보존된다.
- **FAC-3:** 마스킹본이 `parse_resume` 경로로 정상 파싱되어 evidence_count > 0이다(빈 이력서 fixture 제외).
- **FAC-4:** ADR-105 문서가 생성되어 PII 마스킹 정책을 명문화한다.

## 7-1. FAC ↔ AC 매핑표 (subsection of ## 7)
- FAC-1 → T-040:AC-1(전 6표면 literal scan: resumes.content·ranking_runs.result·recommendations·로그·.cache/llm·커밋 웜캐시) + T-036:AC-1(마스킹 제거가 이를 뒷받침)
- FAC-2 → T-036:AC-2(evidence 보존)
- FAC-3 → T-037:AC-1(parse 연결 evidence_count>0)
- FAC-4 → T-036:AC-3(ADR-105)
> repair-plan 2026-06-07: PII Safety scan을 T-036/T-037에서 신규 T-040으로 통합(P1 sizing).

## 8. Non-functional Requirements
- 마스킹은 메모리에서만 수행. 임시 파일·로그에 raw PII 기록 금지.
- 마스킹 처리 시간: 100KB 텍스트 기준 ≤500ms (로컬 기준, 네트워크 호출 없음).

## 8-1. UX 흐름 품질
(해당 없음) — 백엔드 처리 레이어, F-015에서 UI 표현 담당.

## 9. 엣지 케이스
- 마스킹 후 빈 텍스트가 되는 경우 → 400 + `RESUME_EMPTY_AFTER_MASKING`.
- 이름 regex가 회사명·프레임워크명과 충돌해 evidence가 과마스킹되는 경우 → 패턴 정밀도 조정, preview에서 사용자 확인.
- 이메일 주소가 기술 스택 예시로 등장하는 경우(e.g., `user@example.com`) → 마스킹 허용(안전 우선).

## 10. 의존성
- F-013(resume-upload-api) — API 엔드포인트 계약이 마스킹 인터페이스를 사전 정의한 후 F-014 구현. T-036은 T-034 이후.
- SCORING_PIPELINE_SPEC §9-4 `parse_resume` — 알고리즘 본체 불변, 입력 경로만 교체.

## 11. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md)
- Charter: [PROJECT_CHARTER](../../10-charter/PROJECT_CHARTER.md) (§4 G4, §7 보안 PII)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§2 신뢰 경계, §8 보안)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: ADR-105 (본 feature에서 신설)

## 12. 열린 질문
- 마스킹 모듈의 런타임 위치: NestJS(TS regex) vs ai/core(Python regex) → M3에서는 `parse_resume`가 Python Worker에 있으므로 **ai/core/pii_masker.py** 쪽이 자연스럽지만, NestJS가 DB에 쓰기 전에 마스킹해야 하므로 NestJS → Worker 경계를 어디서 끊을지 결정 필요. (가정: NestJS 내 TS regex 마스킹 → 마스킹본만 Worker로 전달 → parse_resume — ADR-105에서 명문화.)
- 이름 best-effort 허용선 — fixture scan 0건이 목표이지만 자연어 이름은 false-negative 내재. PII Safety Pass 기준을 "알려진 fixture PII 0건" + "preview 사용자 확인"으로 한정할지 확인.
