import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CoveragePanel } from '../components/CoveragePanel'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// T-090 AC-3 — 기본 1줄 compact strip, 클릭 시 채널 상세, degraded 시 자동 펼침 + 경고.
describe('CoveragePanel compact strip (AC-3)', () => {
  it('test_AC_3_compact_strip_and_expand — 기본 접힘, 토글 시 상세', async () => {
    const cov = {
      channels: [
        { name: 'toss', tier: '1', status: 'active', last_success_at: '2026-06-10T01:23:00.000Z' },
        {
          name: 'daangn',
          tier: '3',
          status: 'active',
          last_success_at: '2026-06-10T00:10:00.000Z',
        },
      ],
      uncollected: [],
      degraded: false,
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => cov }))

    render(<CoveragePanel />)
    await waitFor(() =>
      expect(screen.getByTestId('coverage-panel').getAttribute('data-state')).toBe('ready'),
    )

    // 기본 = compact strip(요약 1줄), 채널 상세는 접힘
    expect(screen.getByTestId('coverage-panel').textContent).toContain('2/2 소스 수집 중')
    expect(screen.queryByTestId('coverage-detail')).toBeNull()

    const toggle = screen.getByTestId('coverage-toggle')
    expect(toggle.getAttribute('aria-expanded')).toBe('false')

    // 클릭 → 펼침 → 채널 상세 노출
    fireEvent.click(toggle)
    expect(screen.getByTestId('coverage-toggle').getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByTestId('coverage-detail')).toBeTruthy()
    expect(screen.getByTestId('coverage-detail').textContent).toContain('daangn')
  })

  it('test_AC_3_compact_strip_and_expand — degraded 자동 펼침 + 경고', async () => {
    const cov = {
      channels: [
        { name: 'toss', tier: '1', status: 'active', last_success_at: '2026-06-10T01:00:00.000Z' },
        { name: 'kb-bank', tier: '5', status: 'login-required', last_success_at: null },
      ],
      uncollected: ['kb-bank'],
      degraded: true,
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => cov }))

    render(<CoveragePanel />)
    await waitFor(() =>
      expect(screen.getByTestId('coverage-panel').getAttribute('data-state')).toBe('degraded'),
    )

    const panel = screen.getByTestId('coverage-panel')
    // 자동 펼침(토글 없이 상세 노출) + 경고
    expect(panel.getAttribute('role')).toBe('alert')
    expect(panel.textContent).toContain('수집 실패')
    expect(screen.getByTestId('coverage-detail')).toBeTruthy()
    expect(screen.getByTestId('coverage-detail').textContent).toContain('로그인 필요')
  })
})
