import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// 컴포넌트 .tsx 전수 토큰 계약 감사(F-018 FAC-7, T-049 AC-2).
const COMPONENTS_DIR = join(__dirname, '..', 'components')
const HEX = /#[0-9a-fA-F]{3,6}/

function componentFiles(): string[] {
  return readdirSync(COMPONENTS_DIR).filter((f) => f.endsWith('.tsx'))
}

describe('design tokens audit (AC-2)', () => {
  it('test_AC_2_no_raw_hex_and_fenced_gradient_whitelist', () => {
    const hexOffenders: string[] = []
    const gradientFiles: string[] = []

    for (const f of componentFiles()) {
      const src = readFileSync(join(COMPONENTS_DIR, f), 'utf-8')
      if (HEX.test(src)) hexOffenders.push(f)
      if (src.includes('--brand-gradient')) gradientFiles.push(f)
    }

    // raw hex 0 — 색은 DESIGN §2 토큰(var(--...))만 (globals.css 토큰 정의에만 hex 허용)
    expect(hexOffenders).toEqual([])

    // fenced 그라데이션(brand-gradient) 사용처 ≤3 (§2-4 화이트리스트: 로고·fit 링 arc·인사 strip)
    expect(gradientFiles.length).toBeLessThanOrEqual(3)
  })
})
