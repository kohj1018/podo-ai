import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FeedView } from '../components/FeedView'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const META_EMPTY = {
  has_resume: true,
  scoring_status: 'done',
  diff_summary: { new_count: 0, expiring_count: 0 },
  total_pending_count: 0,
  visible_count: 0,
}

// T-092 AC-1 — 신규 적은 날 EmptyState에 "최근 7일 미처리 다시 보기" 버튼 노출 + 클릭 시 재노출 fetch.
describe('Recent-unprocessed resurface (AC-1)', () => {
  it('test_AC_1_resurface_button_visible', async () => {
    const calls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string | URL) => {
        const u = String(url)
        calls.push(u)
        if (u.includes('feed/meta')) {
          return Promise.resolve({ ok: true, json: async () => META_EMPTY })
        }
        return Promise.resolve({ ok: true, json: async () => ({ items: [], nextCursor: null }) })
      }),
    )

    render(<FeedView />)
    // 신규 적은 날(new_count 0, visible 0) → EmptyState + 재노출 버튼
    await waitFor(() => expect(screen.getByTestId('feed-empty-state')).toBeTruthy())
    expect(screen.getByTestId('resurface-button')).toBeTruthy()

    // 클릭 → 재노출 모드 → FeedList가 include_recent_processed=7d로 재요청(AC-2 프론트 배선)
    fireEvent.click(screen.getByTestId('resurface-button'))
    await waitFor(() =>
      expect(calls.some((u) => u.includes('include_recent_processed=7d'))).toBe(true),
    )
    expect(screen.getByTestId('resurface-banner')).toBeTruthy()
  })
})
