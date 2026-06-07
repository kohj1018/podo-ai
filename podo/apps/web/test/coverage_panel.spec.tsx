import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CoveragePanel } from '../components/CoveragePanel'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// T-063 AC-3: 소스 혼합 상태(일부 blocked·login-required)가 사유별 status로 명시되고
// "N/M 소스 수집 중" 요약이 표시되며 "전부 수집" 거짓 인상이 없다(Fail #3).
describe('CoveragePanel partial-failure display (AC-3)', () => {
  it('test_AC_3_coverage_panel_partial_failure_display', async () => {
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
    // degraded → role=alert(투명 경고)
    expect(panel.getAttribute('role')).toBe('alert')
    // 사유별 status 명시
    expect(panel.textContent).toContain('로그인 필요')
    expect(panel.textContent).toContain('차단')
    // "N/M 소스 수집 중" 요약(active 1 / 전체 3)
    expect(panel.textContent).toContain('1/3 소스 수집 중')
    // 거짓 완전성 0 — "전부" 인상 금지
    expect(panel.textContent).not.toContain('전부')
    // 수집된 소스도 마지막 성공 시각 노출
    expect(panel.textContent).toContain('마지막 성공')
  })

  it('test_AC_3_all_active_no_false_degraded', async () => {
    // 모두 active → ready(region) + "2/2 소스 수집 중"
    const cov = {
      channels: [
        {
          name: 'daangn',
          tier: '3',
          status: 'active',
          last_success_at: '2026-06-07T01:00:00.000Z',
        },
        {
          name: 'coupang',
          tier: '1',
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
    const panel = screen.getByTestId('coverage-panel')
    expect(panel.getAttribute('data-state')).toBe('ready')
    expect(panel.textContent).toContain('2/2 소스 수집 중')
  })
})
