// 마스킹 경계 인터페이스(port). 마스킹 런타임 위치는 ADR-105가 확정(NestJS 경계, DB write 전).
// port 추상화라 위치가 바뀌어도 컨트롤러/서비스 영향은 최소(구현체만 교체).

export interface MaskResult {
  masked: string
  placeholders: number // 치환 건수
}

export abstract class ResumeMasker {
  abstract mask(raw: string): MaskResult
}

// 기술 프로필 도메인 — URL 치환 대상에서 제외(과마스킹 방지, AC-2).
// github.com / gitlab.com / linkedin.com / leetcode.com 등 개발자 식별용 프로필은 증거로 보존.
const TECH_PROFILE_DOMAINS = /(?:github|gitlab|linkedin|leetcode|stackoverflow|hackerrank)\.com/i

// 직접 식별자 패턴(ADR-105 §3 기준 — 순서가 치환 우선순위).
// 1. 주민번호: 앞자리 6자리 + 구분자 + 뒷자리 7자리 (이메일보다 먼저 — 숫자 연속 패턴이 이메일에 묻힐 수 있음).
const RRN_RE = /\d{6}[-\s]?\d{7}/g
// 2. 이메일
const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g
// 3. 한국 전화번호 — 01x 계열 (010/011/016/017/018/019)
const PHONE_RE = /01[016789][-\s]?\d{3,4}[-\s]?\d{4}/g
// 4. 개인 URL — 기술 프로필 도메인은 TECH_PROFILE_DOMAINS로 선별 보존
const URL_RE = /https?:\/\/[^\s,)'"]+/g
// 5. 한글 이름 best-effort — 2~4자 한글(한자성 1자 + 이름 1~3자).
//    false-positive 최소화를 위해 "이름:" / "성명:" 레이블 뒤 패턴 우선.
//    레이블 없는 단독 한글 2자는 지명·일반명사와 겹쳐 치환 범위에서 제외.
const KOREAN_NAME_LABELED_RE = /(?:이름|성명|name)\s*[:：]\s*([가-힣]{2,4})/gi
// 영문 이름(First Last 또는 Last, First) — 레이블 뒤 또는 이력서 첫 줄 단독
const ENG_NAME_LABELED_RE = /(?:name)\s*[:：]\s*([A-Z][a-z]+ [A-Z][a-z]+)/g

// raw 자체는 반환값(masked)에만 흐르며 로그·예외에 노출하지 않는다(ADR-105 §5 NFR).
export class RegexResumeMasker extends ResumeMasker {
  mask(raw: string): MaskResult {
    let placeholders = 0

    // 단계별 치환 — 앞 단계 치환 결과가 뒤 단계 패턴과 충돌하지 않도록 순서 고정.
    let text = raw

    // 1. 주민번호
    text = text.replace(RRN_RE, () => {
      placeholders += 1
      return '[MASKED_RRN]'
    })

    // 2. 이메일
    text = text.replace(EMAIL_RE, () => {
      placeholders += 1
      return '[MASKED_EMAIL]'
    })

    // 3. 전화
    text = text.replace(PHONE_RE, () => {
      placeholders += 1
      return '[MASKED_PHONE]'
    })

    // 4. URL — 기술 프로필 도메인은 보존
    text = text.replace(URL_RE, (url) => {
      if (TECH_PROFILE_DOMAINS.test(url)) return url
      placeholders += 1
      return '[MASKED_URL]'
    })

    // 5. 한글 이름 (레이블 뒤 패턴)
    text = text.replace(KOREAN_NAME_LABELED_RE, (_match, _label) => {
      placeholders += 1
      // 레이블은 유지하고 이름 값만 치환
      return _match.replace(/[가-힣]{2,4}$/, '[MASKED_NAME]')
    })

    // 6. 영문 이름 (레이블 뒤 패턴)
    text = text.replace(ENG_NAME_LABELED_RE, (_match) => {
      placeholders += 1
      return _match.replace(/[A-Z][a-z]+ [A-Z][a-z]+$/, '[MASKED_NAME]')
    })

    return { masked: text, placeholders }
  }
}

// 구 stub — resumes.module.ts가 RegexResumeMasker로 교체됨(T-036).
// 기존 resumes.spec.ts DB 테스트 호환을 위해 export 유지.
export class RegexResumeMaskerStub extends ResumeMasker {
  mask(raw: string): MaskResult {
    let placeholders = 0
    const masked = raw.replace(EMAIL_RE, () => {
      placeholders += 1
      return '[MASKED_EMAIL]'
    })
    return { masked, placeholders }
  }
}
