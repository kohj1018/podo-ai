import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import HomePage from '../app/page'
import { SessionProvider } from '../components/SessionProvider'

// next/navigation의 useRouter는 AuthGate가 호출 — authed 경로에선 replace 미호출.
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

function daysFromNow(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString()
}

// el2가 DOM에서 el1 뒤에 오는가(문서 순서) — 세로 IA 순서 단언.
function isAfter(el1: Element, el2: Element): boolean {
  return Boolean(el1.compareDocumentPosition(el2) & Node.DOCUMENT_POSITION_FOLLOWING)
}

// T-090 AC-2 — 피드 세로 순서: 커버리지 strip → (직군 탭) → greeting → 마감 임박 → 추천.
describe('피드 세로 IA 순서 (AC-2)', () => {
  it('test_AC_2_feed_vertical_order', async () => {
    const meta = {
      has_resume: true,
      scoring_status: 'done',
      diff_summary: { new_count: 2, expiring_count: 1 },
      total_pending_count: 0,
      visible_count: 2,
      resume_domains: {
        primary_domains: ['frontend'],
        secondary_domains: [],
        confidence: 'high',
      },
    }
    const feed = {
      items: [
        {
          posting: {
            id: 1,
            source: 'toss',
            company: '토스',
            title: 'FE',
            closing_at: daysFromNow(3),
          },
          fit_level: 5,
          rank_position: 0,
          status: 'scored',
          evidence: { e: 1 },
        },
        {
          posting: { id: 2, source: 'daangn', company: '당근', title: 'BE', closing_at: null },
          fit_level: 4,
          rank_position: 1,
          status: 'scored',
          evidence: { e: 1 },
        },
      ],
      nextCursor: null,
    }
    vi.stubGlobal(
      'fetch',
      mockFetch([
        ['auth/me', { data: { userId: 'u1' } }],
        [
          'coverage',
          {
            channels: [{ name: 'toss', status: 'active', last_success_at: daysFromNow(0) }],
            uncollected: [],
            degraded: false,
          },
        ],
        ['feed/meta', meta],
        ['feed', feed],
      ]),
    )

    render(
      <SessionProvider>
        <HomePage />
      </SessionProvider>,
    )

    // 마감 임박 섹션 + greeting + 추천 카드가 모두 떠야 순서 단언 가능
    await waitFor(() => expect(screen.getByTestId('deadline-section')).toBeTruthy())

    const coverage = screen.getByTestId('coverage-panel')
    const tablist = screen.getByRole('tablist', { name: '직군 분리' })
    const greeting = screen.getByTestId('greeting-card')
    const deadline = screen.getByTestId('deadline-section')
    const firstCard = screen.getAllByTestId('job-card')[0]

    // 커버리지 → 탭 → greeting → 마감 임박 → 추천(첫 카드)
    expect(isAfter(coverage, tablist)).toBe(true)
    expect(isAfter(tablist, greeting)).toBe(true)
    expect(isAfter(greeting, deadline)).toBe(true)
    expect(isAfter(deadline, firstCard)).toBe(true)
  })
})
