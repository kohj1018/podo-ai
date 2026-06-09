import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import HomePage from '../app/page'
import { SessionProvider } from '../components/SessionProvider'

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }))
vi.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }))

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  replace.mockClear()
})

function mockFetch(routes: Array<[string, unknown]>) {
  return vi.fn((url: string | URL) => {
    const u = String(url)
    for (const [key, val] of routes) {
      if (u.includes(key)) {
        return Promise.resolve({ ok: true, json: async () => val })
      }
    }
    return Promise.resolve({ ok: true, json: async () => ({ items: [], nextCursor: null }) })
  })
}

// T-097 — 신규 사용자(이력서 없음) /resume 직행, 이력서 있으면 피드 정상.
describe('New-user resume redirect (AC-1)', () => {
  it('test_AC_1_no_resume_redirects', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch([
        ['auth/me', { data: { userId: 'u1' } }],
        ['feed/meta', { has_resume: false }],
      ]),
    )

    render(
      <SessionProvider>
        <HomePage />
      </SessionProvider>,
    )

    // 이력서 없음 → /resume 리다이렉트(client 가드). 루프 방지(정확히 /resume 1회).
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/resume'))
    expect(replace).not.toHaveBeenCalledWith('/')
    // 리다이렉트 placeholder(피드 미렌더 — 깜빡임 최소)
    expect(screen.getByTestId('resume-redirect')).toBeTruthy()
    expect(screen.queryByTestId('coverage-panel')).toBeNull()
  })
})

describe('Existing-resume user feed (AC-2)', () => {
  it('test_AC_2_with_resume_feed', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch([
        ['auth/me', { data: { userId: 'u1' } }],
        [
          'feed/meta',
          {
            has_resume: true,
            scoring_status: 'done',
            diff_summary: { new_count: 1, expiring_count: 0 },
            total_pending_count: 0,
            visible_count: 1,
            resume_domains: null,
          },
        ],
        ['coverage', { channels: [], uncollected: [], degraded: false }],
        [
          'feed',
          {
            items: [
              {
                posting: { id: 1, source: 'toss', company: 'Co', title: 'FE', closing_at: null },
                fit_level: 5,
                rank_position: 0,
                status: 'scored',
                evidence: { e: 1 },
              },
            ],
            nextCursor: null,
          },
        ],
      ]),
    )

    render(
      <SessionProvider>
        <HomePage />
      </SessionProvider>,
    )

    // 이력서 있음 → 리다이렉트 없이 피드(커버리지 패널) 렌더
    await waitFor(() => expect(screen.getByTestId('coverage-panel')).toBeTruthy())
    expect(replace).not.toHaveBeenCalledWith('/resume')
    expect(screen.queryByTestId('resume-redirect')).toBeNull()
  })
})
