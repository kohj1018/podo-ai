// 마스킹 경계 인터페이스(port). 전체 regex 구현은 T-036(RegexResumeMasker)이 stub을 교체한다.
// 마스킹 런타임 위치(NestJS 경계 vs ai/core)는 ADR-105가 확정 — port 추상화라 위치가 바뀌어도
// 컨트롤러/서비스 영향은 최소(구현체만 교체).

export interface MaskResult {
  masked: string
  placeholders: number // 치환 건수
}

export abstract class ResumeMasker {
  abstract mask(raw: string): MaskResult
}

// 최소 stub — 이메일만 치환(T-036이 전체 직접식별자 패턴으로 교체).
// raw 자체는 반환값(masked)에만 흐르며 로그·예외에 노출하지 않는다(F-013 §8 NFR).
export class RegexResumeMaskerStub extends ResumeMasker {
  mask(raw: string): MaskResult {
    let placeholders = 0
    const masked = raw.replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, () => {
      placeholders += 1
      return '[MASKED_EMAIL]'
    })
    return { masked, placeholders }
  }
}
