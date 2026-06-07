# ADR-105 — PII 마스킹 정책

## Status
accepted

## Context
M3에서 이력서 업로드 기능(T-034)이 추가되어 사용자 이력서(민감 PII)가 시스템에 유입된다.  
ARCHITECTURE_OVERVIEW §8은 "이력서 = 민감 PII, 저장·전송 보호, 외부 LLM 전송 시 최소 필요 정보 원칙 — 구체 정책은 ADR"로 연기했다.  
본 ADR이 그 정책을 확정한다.

## 결정

### 1. 대상 직접 식별자 (치환 대상)
| 식별자 | 플레이스홀더 |
|--------|------------|
| 이메일 | `[MASKED_EMAIL]` |
| 한국 전화번호 (01x 계열) | `[MASKED_PHONE]` |
| 주민등록번호 (6자리-7자리) | `[MASKED_RRN]` |
| 개인 URL (기술 프로필 제외) | `[MASKED_URL]` |
| 이름 best-effort (레이블 뒤 한글/영문 패턴) | `[MASKED_NAME]` |

### 2. 보존 대상 evidence (치환 제외)
- **스택/기술 토큰**: Python, TypeScript, React, Next.js 등 — 스코어링 근거
- **학교명·학위·전공**: 재식별 간접 지표이나 M3에서는 evidence로 보존. 간접 재식별 방어는 M4 연기.
- **경력기간 수치**: 2년, 3년 6개월 등 숫자+단위 — 스코어링 근거
- **기술 프로필 URL**: github.com / gitlab.com / linkedin.com / leetcode.com 등 — 스코어링 근거

### 3. 마스킹 방식
- **rule-based regex** (NestJS TS, `RegexResumeMasker`) — 외부 LLM 의존 NER 없음.
- **원칙: raw PII를 외부 LLM 탐지 경로에 보내는 것 금지** (M3 안전 불변식).
  - 마스킹 전 raw는 LLM API 호출 파라미터·로그·예외 메시지 어디에도 포함되지 않는다.
  - 마스킹본(masked)만 DB에 저장되고 이후 파이프라인으로 흐른다.

### 4. 마스킹 런타임 위치 (확정)
**NestJS 경계, DB write 전** — `ResumesService.create()` 내에서 `this.masker.mask(raw)` 호출 후  
마스킹본(`masked`)만 `prisma.resume.create(data: { content: masked })` 에 전달한다.  
`ResumeMasker` port 추상화 덕분에 위치 변경 시 구현체만 교체하면 된다(컨트롤러/서비스 무변경).

### 5. 이름 best-effort + preview 보완
- 한글 이름 best-effort는 "레이블(이름:/성명:) 뒤 2~4자 한글" 패턴으로 제한 — false-positive 최소화.
- 레이블 없는 단독 한글 2자(지명·일반명사)는 치환 대상에서 제외.
- 이름 패턴 미탐지(false-negative) 발생 가능성 인지 — 완전 NER 없이 rule-based의 고유 한계.

### 6. 간접 재식별 경계
학교+회사+기간의 조합으로 개인을 역추적(간접 재식별)하는 방어는 **M4**로 연기.  
M3 범위는 직접 식별자(1~5번)만 다룬다.

### 7. PII Safety Pass 기준
전 표면(6곳) PII literal scan 기준 = `T-040 PII Safety Pass` 담당.  
마스킹된 결과물이 통제·하류 표면 6곳 모두에서 raw PII 0건임을 확인하는 것은 T-040이 책임진다.

## 근거
- **단순성 우선 (ADR-006)**: NER·ML 모델 없이 regex rule-based로 M3 직접 식별자 커버 달성 가능 — 추가 의존성 0.
- **포트 추상화 (T-034 설계)**: 런타임 위치 변경에 대비한 port(인터페이스)가 이미 존재 — 구현 교체 비용 최소.
- **M3 안전 불변식**: raw PII → 외부 LLM 전송 경로 금지는 출시 전 비가역적 결정.

<a id="adr-105-amend-1"></a>
## Amendment 1 — 계정 PII (OAuth 멀티유저, M4)

**배경:** [관측됨] M4가 OAuth 멀티유저(ADR-107)를 도입하면서 *계정* PII(이메일·표시이름·provider account id·아바타 URL)가 시스템에 유입된다. 본 amendment가 이력서 PII(원 결정)와 계정 PII의 취급을 구분한다.

**결정 (충돌 없는 확장):**
1. **계정 식별자는 마스킹 대상이 아니다** — 식별이 *목적*이라 이력서 PII(스코어링에 부수적으로 유입되는 민감정보)와 본질이 다르다.
2. **`users`에 최소 식별자만 저장** — provider · provider account id · 이메일 · 표시이름 · 아바타 URL. **OAuth access/refresh 토큰은 영속하지 않는다**(로그인 시점에만 사용).
3. **계정 PII는 스코어링 경로에 절대 유입 금지** — prompt·외부 LLM·`.cache/llm`·`ranking_runs.result`·`recommendations`·애플리케이션 로그 어디에도 계정 식별자가 흐르지 않는다. M3 안전 불변식(이력서 raw PII 미유출)을 *계정 PII로 확장*한다.
4. 이력서 `content`는 기존 결정대로 마스킹본만 저장(원 결정 1~5번 불변).

**§6 정정 (간접 재식별 시점):** 원 §6은 간접 재식별 방어를 "M4 연기"로 두었으나, M4는 *로컬 멀티유저*(공개 미배포)이고 간접 재식별 리스크는 *공개 노출*에서 발현한다 → **간접 재식별 방어 시점을 M6(공개 배포)로 정정**한다(직접 식별자 마스킹은 M3부터 유효).

## 관련 문서
- [ADR-107](ADR-107-oauth-multiuser.md) — OAuth 멀티유저 (Amendment 1 동인)
- [F-016](../../30-workitems/features/F-016-oauth-multiuser.md) — 계정 PII 적용 feature
- [T-036](../../30-workitems/tasks/T-036-pii-masking-module.md) — 본 ADR을 구현하는 task
- [T-040](../../30-workitems/tasks/T-040-pii-safety-pass.md) — 전 표면 PII literal scan (Safety Pass)
- [F-014](../../30-workitems/features/F-014-resume-parse-pii.md) — 이력서 파싱·PII feature
- [ARCHITECTURE_OVERVIEW §8, §10](../../20-system/ARCHITECTURE_OVERVIEW.md) — 보안·열린질문 backref
