import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthGate } from '../components/AuthGate'
import { CoveragePanel } from '../components/CoveragePanel'
import { SessionProvider } from '../components/SessionProvider'

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }))
vi.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }))

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  replace.mockClear()
})

// fetch가 영원히 pending → 로딩 상태 유지
function pendingFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => new Promise(() => {})),
  )
}

// T-098 AC-1 — 주요 로딩 지점에 skeleton 로딩 UI + 가짜 점수/preview 미표시.
describe('loading UX skeletons (AC-1)', () => {
  it('test_AC_1_loading_indicators_no_fake_score', () => {
    // (1) AuthGate 세션 체크 로딩 → skeleton(shimmer) + aria-busy, 보호 내용·가짜 점수 미표시
    pendingFetch()
    const { unmount } = render(
      <SessionProvider>
        <AuthGate>
          <div>보호된 내용</div>
        </AuthGate>
      </SessionProvider>,
    )
    const gate = screen.getByTestId('authgate-loading')
    expect(gate.getAttribute('aria-busy')).toBe('true')
    expect(gate.querySelectorAll('.shimmer').length).toBeGreaterThan(0)
    expect(screen.queryByText('보호된 내용')).toBeNull()
    expect(gate.textContent ?? '').not.toMatch(/적합도|점수|%/) // 가짜 점수 없음
    unmount()
    vi.unstubAllGlobals()

    // (2) CoveragePanel 로딩 → compact strip skeleton(shimmer) + aria-busy
    pendingFetch()
    render(<CoveragePanel />)
    const panel = screen.getByTestId('coverage-panel')
    expect(panel.getAttribute('data-state')).toBe('loading')
    expect(panel.getAttribute('aria-busy')).toBe('true')
    expect(panel.querySelectorAll('.shimmer').length).toBeGreaterThan(0)
  })
})

// T-098 AC-2 — 로딩 모션이 reduced-motion에서 정적 분기.
describe('loading reduced-motion (AC-2)', () => {
  it('test_AC_2_reduced_motion', () => {
    const css = readFileSync(join(__dirname, '..', 'app', 'globals.css'), 'utf-8')
    // reduced-motion 미디어쿼리 + shimmer 애니메이션 정적(animation: none)
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/)
    expect(css).toMatch(/\.shimmer\s*\{\s*animation:\s*none/)
  })
})
