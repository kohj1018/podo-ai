# T-036-pii-masking-module

## 0. Status
draft

## 0-1. Type
feature

## 1. 작업 목적
T-034가 정의한 `ResumeMasker` port의 stub을 **regex/rule-based 전체 마스킹 구현**으로 교체한다 — 직접 식별자(이름·이메일·전화·주민번호·개인 URL)를 메모리에서 플레이스홀더로 치환하고, 학교·회사·스택·경력기간·수치는 evidence로 보존(과마스킹 방지). **raw PII를 외부 LLM에 보내는 탐지 경로 금지**(M3 안전 불변식). PII 마스킹 정책을 **ADR-105**로 명문화한다. (전 표면 PII Safety Pass literal scan은 신규 **T-040**으로 통합 — repair-plan P1 sizing.)

## 2. 작업 범위
- T-034 `resume-masker.port.ts`의 stub → `RegexResumeMasker` 전체 구현(NestJS TS, 작업가정 — ADR-105 확정).
- 정규식 패턴셋 + 플레이스홀더 치환 + evidence 보존.
- **ADR-105 신설**(PII 정책) + ARCH §10 PII 열린질문 backref.
- (PII Safety Pass fixture + 전 표면 literal scan은 **T-040**으로 분리 — repair-plan P1 sizing.)

## 3. 구현 항목
1. `podo/apps/api/src/resumes/resume-masker.ts`(또는 port 파일 내) — 현재: T-034 `RegexResumeMaskerStub`(이메일만) → 변경: `RegexResumeMasker implements ResumeMasker`로 전체 패턴 구현:
   - 이메일 `/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g` → `[MASKED_EMAIL]`
   - 전화 `/01[0-9][-\s]?\d{3,4}[-\s]?\d{4}/g` → `[MASKED_PHONE]`
   - 주민번호 `/\d{6}[-\s]?\d{7}/g` → `[MASKED_RRN]`
   - 개인 URL: 일반 URL 치환하되 `github.com/<user>` 등 기술 프로필은 선별 보존 → `[MASKED_URL]`
   - 이름 best-effort: 한글 2~4자 성명 패턴 + 영문 이름 패턴(false-positive 최소화) → `[MASKED_NAME]`
   - 반환 `{ masked, placeholders }`(치환 건수). → 확인: 단위 테스트가 각 패턴 치환. (AC-1)
2. `podo/apps/api/src/resumes/resumes.module.ts` — 현재: `useClass: RegexResumeMaskerStub` → 변경: `useClass: RegexResumeMasker`. → 확인: 업로드가 전체 마스킹 사용. (AC-1)
3. `docs/90-decisions/project/ADR-105-pii-masking-policy.md`(신규) + `docs/20-system/ARCHITECTURE_OVERVIEW.md` §10 — 현재: ADR-105 없음 + ARCH §8/§10이 "PII 정책 = ADR로 연기"로 지정 → 변경: ADR-105 신설(대상 직접 식별자·마스킹 방식(regex/rule-based, raw→외부 LLM 탐지 금지)·**마스킹 런타임 위치 확정(NestJS 경계, DB write 전)**·이름 best-effort+preview 보완·간접 재식별=M4 연기·Safety Pass 기준=T-040 6표면 0) + ARCH §10 PII 열린질문에 `→ ADR-105 해소` backref 부착. → 확인: ADR-105 status=accepted + ARCH §10 backref 존재. (AC-3) (P2 doc-link: ARCH write_set 포함)
4. `ai/worker/src/worker/...` parse 경로 보존 점검 — 현재: parse_resume가 스택/학교 헤딩 추출 → 변경: 없음(마스킹은 직접 식별자만; 스택·학교·기간 패턴은 치환 대상 아님). → 확인: 마스킹본을 parse 시 스택(Python/TypeScript 등)·학교명·기간 수치 보존(evidence_count 유지). (AC-2)
> 마스킹 통제 표면 + 파이프라인 하류 표면의 PII literal scan은 **T-040 PII Safety Pass**로 통합(repair-plan P1 sizing).

## 4. 제외 항목
- raw PII를 외부 LLM에 보내는 NER 탐지·로컬 인메모리 NER(M3 비범위, F-014 §5). · 간접 재식별 방어(학교+회사+기간 — M4). · **PII literal scan 일체**(통제+하류 6표면 — **T-040 PII Safety Pass**로 통합, repair-plan P1 sizing). · evidence 행단위 편집 UI. · 스코어링 연결(T-037).

## 4-1. 변경 예정 파일/경로
<!-- 구현 시점에 채운다. -->

## 5. 완료 조건
직접 식별자가 regex로 마스킹되고 evidence(스택·학교·기간)는 보존되며, ADR-105가 PII 정책을 명문화한다(전 표면 PII 0 검증은 T-040).

## 6. Acceptance Criteria
- AC-1 [Given] 이름·이메일·전화·주민번호·개인 URL을 포함한 텍스트 [When] `RegexResumeMasker.mask()` [Then] 각 직접 식별자가 대응 플레이스홀더(`[MASKED_EMAIL]` 등)로 치환되고 `placeholders` 건수가 치환 수와 일치한다.
- AC-2 [Given] 스택(Python/TypeScript)·학교명·경력기간 수치를 포함한 이력서 [When] 마스킹 [Then] 그 evidence 토큰들이 마스킹본에 보존된다(직접 식별자만 치환, 과마스킹 0).
- AC-3 [Given] ARCH §8/§10이 PII 정책을 ADR로 연기 [When] ADR-105 작성 [Then] ADR-105가 대상 식별자·마스킹 방식·런타임 위치·간접 재식별 경계·Safety Pass 기준을 명문화하고 status=accepted이며 ARCH §10에 backref가 부착된다.
> 전 표면(6곳) PII literal scan은 **T-040 PII Safety Pass**가 담당(repair-plan P1 sizing — 본 task에서 분리).

## 6-1. 테스트 시나리오 (TDD Red)
- AC-1 → vitest::podo/apps/api/test/masker.spec.ts::test_AC_1_masks_all_direct_identifiers
- AC-2 → vitest::podo/apps/api/test/masker.spec.ts::test_AC_2_evidence_tokens_preserved
- AC-3 → 문서 점검: ADR-105 존재 + status=accepted + 필수 섹션(대상·방식·위치·경계·기준) + ARCH §10 backref

## 6-2. TDD opt-out
<!-- TDD 적용 — 순수 함수 마스킹(주입 입력 → 출력 단언). AC-2 업로드 표면은 DATABASE_URL 주입 시 통합 검증. -->

## 7. 관련 문서
- Milestone: [M3-resume-upload](../milestones/M3-resume-upload.md) (§5 PII Safety Pass)
- Feature: [F-014-resume-parse-pii](../features/F-014-resume-parse-pii.md)
- Architecture: [ARCHITECTURE_OVERVIEW](../../20-system/ARCHITECTURE_OVERVIEW.md) (§8 보안 PII, §10 열린질문)
- Architecture-Iface: [ARCH ## 7-3 백엔드](../../20-system/ARCHITECTURE_OVERVIEW.md#arch-7-3)
- ADR: ADR-105 (본 task에서 신설)

## 8. 메모
- 해석 확정: 마스킹 런타임 = NestJS 경계 TS(F-014 §12 작업가정) — ADR-105가 본 task에서 이를 *정식 확정*. port 추상화라 추후 위치 변경 시 구현체만 교체.
- ⚠ 외부 docs-check(ADR-040): regex 패턴은 모델 지식으로 충분하나, 한국 주민번호/전화 포맷 edge는 구현 시 실데이터로 검증 권장.
- repair-plan 2026-06-07 [default] P1 Plan-sizing: Adopt — PII scan(통제+하류 전 표면)을 신규 T-040(PII Safety Pass)로 통합 → 본 task=마스킹+ADR-105(4→3 AC). F-014 §7-1: FAC-1 → T-040:AC-1 + T-036:AC-1.
- repair-plan 2026-06-07 [default] P2 Plan-doc-link: Adopt(적용; P2라 §5 미영속) — ARCH §10 backref 위해 ARCHITECTURE_OVERVIEW.md를 write_set+step3에 추가.

## 9. 의존성
- depends_on: [T-034]   # ResumeMasker port + stub을 본 task가 교체
- read_set: ["podo/apps/api/src/resumes/**", "docs/20-system/ARCHITECTURE_OVERVIEW.md", "ai/worker/src/worker/parse_resume.py"]
- write_set: ["podo/apps/api/src/resumes/resume-masker.ts", "podo/apps/api/src/resumes/resumes.module.ts", "podo/apps/api/test/masker.spec.ts", "docs/90-decisions/project/ADR-105-pii-masking-policy.md", "docs/20-system/ARCHITECTURE_OVERVIEW.md"]
- assumptions: ["T-034 업로드 엔드포인트 + ResumeMasker port 존재"]
- verifier: "pnpm --filter @podo/api test"
