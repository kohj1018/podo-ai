import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CoveragePanel } from '../components/CoveragePanel'
import { FeedView } from '../components/FeedView'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// URL 기반 fetch mock — '/feed/meta'를 '/feed'보다 먼저 매칭(더 구체적 경로 우선).
function mockFetch(routes: Array<[string, unknown]>) {
  return vi.fn((url: string | URL) => {
    const u = String(url)
    for (const [key, val] of routes) {
      if (u.includes(key)) {
        if (val === '__reject__') return Promise.reject(new Error('network'))
        return Promise.resolve({ ok: true, json: async () => val })
      }
    }
    return Promise.resolve({ ok: true, json: async () => ({ items: [], nextCursor: null }) })
  })
}

const READY_ITEM = {
  posting: { id: 1, source: 'toss', company: 'Co', title: 'FE', role_family: 'frontend' },
  fit_level: 5,
  rank_position: 0,
  status: 'scored',
  evidence: { e: 1 },
}

describe('FeedView ready — GreetingCard (AC-1)', () => {
  it('test_AC_1_greeting_card_shows_new_count_with_region_role', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch([
        [
          'feed/meta',
          {
            has_resume: true,
            scoring_status: 'done',
            diff_summary: { new_count: 3, expiring_count: 1 },
            total_pending_count: 0,
            visible_count: 3,
          },
        ],
        ['feed', { items: [READY_ITEM], nextCursor: null }],
      ]),
    )

    render(<FeedView />)
    await waitFor(() => expect(screen.getByTestId('greeting-card')).toBeTruthy())

    // section + aria-label → 접근성 트리에서 암묵 role=region(getByRole로 단언 — biome a11y 정합)
    const card = screen.getByRole('region', { name: '오늘의 요약' })
    expect(card.getAttribute('data-testid')).toBe('greeting-card')
    expect(screen.getByTestId('new-count').textContent).toContain('신규 3건')
  })
})

describe('CoveragePanel degraded (AC-2)', () => {
  it('test_AC_2_coverage_panel_danger_on_degraded', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch([
        [
          'coverage',
          {
            channels: [{ name: 'toss', status: 'failed', last_success_at: null }],
            uncollected: ['daangn'],
            degraded: true,
          },
        ],
      ]),
    )

    render(<CoveragePanel />)
    await waitFor(() =>
      expect(screen.getByTestId('coverage-panel').getAttribute('data-state')).toBe('degraded'),
    )

    const panel = screen.getByTestId('coverage-panel')
    // 친근한 footer — 알람(role=alert·"수집 실패") 아님, 미수집은 정직하게 고지(Fail#3 유지)
    expect(panel.getAttribute('role')).not.toBe('alert')
    expect(panel.textContent).not.toContain('수집 실패')
    expect(panel.textContent).not.toContain('전부')
    expect(screen.getByTestId('coverage-uncollected')).toBeTruthy()
  })
})

describe('FeedView scoring (AC-3)', () => {
  it('test_AC_3_scoring_running_shows_skeleton_no_score', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch([
        [
          'feed/meta',
          {
            has_resume: true,
            scoring_status: 'running',
            diff_summary: { new_count: 0, expiring_count: 0 },
            total_pending_count: 0,
            visible_count: 0,
          },
        ],
      ]),
    )

    render(<FeedView />)
    await waitFor(() => expect(screen.getByTestId('feed-scoring')).toBeTruthy())

    const skeleton = screen.getByTestId('feed-scoring')
    expect(skeleton.getAttribute('aria-busy')).toBe('true')
    expect(screen.getByText('포도가 공고를 분석하고 있어요')).toBeTruthy()
    // 가짜 점수 없음 — GreetingCard·JobCard 미렌더
    expect(screen.queryByTestId('greeting-card')).toBeNull()
    expect(screen.queryByTestId('job-card')).toBeNull()
  })
})

describe('FeedView empty / error (AC-4)', () => {
  it('test_AC_4_empty_state', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch([
        [
          'feed/meta',
          {
            has_resume: true,
            scoring_status: 'done',
            diff_summary: { new_count: 0, expiring_count: 0 },
            total_pending_count: 0,
            visible_count: 0,
          },
        ],
      ]),
    )

    render(<FeedView />)
    await waitFor(() => expect(screen.getByTestId('feed-empty-state')).toBeTruthy())
    expect(screen.getByText('오늘은 신규가 적어요')).toBeTruthy()
  })

  it('test_AC_4_error_state', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network')))

    render(<FeedView />)
    await waitFor(() => expect(screen.getByTestId('feed-state-error')).toBeTruthy())

    const err = screen.getByTestId('feed-state-error')
    expect(err.getAttribute('role')).toBe('alert')
    expect(screen.getByText('다시 시도')).toBeTruthy()
  })
})
