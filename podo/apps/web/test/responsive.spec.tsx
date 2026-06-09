import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// jsdom은 레이아웃/미디어쿼리를 계산하지 않으므로 CSS·layout 계약을 정적으로 감사(design_tokens.spec 패턴).
const CSS = readFileSync(join(__dirname, '..', 'app', 'globals.css'), 'utf-8')
const LAYOUT = readFileSync(join(__dirname, '..', 'app', 'layout.tsx'), 'utf-8')

// T-101 AC-1 — 데스크톱(≥1024px)에서 단일 중앙 컬럼 유지(과도 확장 없이, 멀티컬럼 미사용).
describe('desktop single column responsive (AC-1)', () => {
  it('test_AC_1_desktop_single_column', () => {
    // 중앙 컬럼 폭 토큰 정의
    expect(CSS).toMatch(/--app-max-width\s*:/)
    // 데스크톱 미디어쿼리(단일 컬럼 유지 + 폭 소폭 증가)
    expect(CSS).toMatch(/@media\s*\(min-width:\s*1024px\)/)
    // .app-shell = 중앙 정렬(margin 0 auto) + max-width 토큰(과도 확장 차단)
    const shell = CSS.match(/\.app-shell\s*\{[^}]*\}/)?.[0] ?? ''
    expect(shell).toMatch(/margin:\s*0 auto/)
    expect(shell).toMatch(/max-width:\s*var\(--app-max-width\)/)
    // 멀티컬럼 미사용 — 단일 중앙 컬럼(DESIGN §4)
    expect(CSS).not.toMatch(/grid-template-columns/)
    // layout이 단일 컬럼 셸로 감쌈
    expect(LAYOUT).toContain('app-shell')
  })
})
