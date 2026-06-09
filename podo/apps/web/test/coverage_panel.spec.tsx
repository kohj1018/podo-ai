import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CoveragePanel } from '../components/CoveragePanel'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// 친근한 수집 footer — 활성 채널 chip + "그 외 채널 미수집"(알람 X) + "미수집은 추천 제외" 정직 고지(Fail#3 유지).
describe('CoveragePanel friendly footer (AC-3)', () => {
  it('test_AC_3_partial_failure_compact_honest', async () => {
    const cov = {
      channels: [
        {
          name: 'daangn',
          tier: '3',
          status: 'active',
          last_success_at: '2026-06-07T01:00:00.000Z',
        },
        { name: 'kb-bank', tier: '5', status: 'login-required', last_success_at: null },
        { name: 'samsung-sds', tier: '4', status: 'blocked', last_success_at: null },
      ],
      uncollected: ['kb-bank', 'samsung-sds'],
      degraded: true,
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => cov }))

    render(<CoveragePanel />)
    await waitFor(() =>
      expect(screen.getByTestId('coverage-panel').getAttribute('data-state')).toBe('degraded'),
    )
    const panel = screen.getByTestId('coverage-panel')

    // 알람 아님 — role=alert·"수집 실패"·차단 나열 없음(UX 보호)
    expect(panel.getAttribute('role')).not.toBe('alert')
    expect(panel.textContent).not.toContain('수집 실패')
    expect(panel.textContent).not.toContain('차단')

    // 활성 채널 chip(당근) + "그 외 채널 미수집" + 정직 고지(Fail#3)
    expect(screen.getAllByTestId('coverage-chip-active').length).toBe(1)
    expect(panel.textContent).toContain('당근')
    expect(screen.getByTestId('coverage-uncollected')).toBeTruthy()
    expect(panel.textContent).toContain('미수집 채널은 추천에 포함되지 않아요')
  })

  it('test_AC_3_all_active_no_uncollected_chip', async () => {
    const cov = {
      channels: [
        { name: 'toss', tier: '1', status: 'active', last_success_at: '2026-06-07T01:00:00.000Z' },
        {
          name: 'daangn',
          tier: '3',
          status: 'active',
          last_success_at: '2026-06-07T02:00:00.000Z',
        },
      ],
      uncollected: [],
      degraded: false,
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => cov }))

    render(<CoveragePanel />)
    await waitFor(() => expect(screen.getByRole('region', { name: '수집 현황' })).toBeTruthy())
    // 전부 활성 → active chip 2개, "그 외 채널 미수집" 없음
    expect(screen.getAllByTestId('coverage-chip-active').length).toBe(2)
    expect(screen.queryByTestId('coverage-uncollected')).toBeNull()
  })
})
