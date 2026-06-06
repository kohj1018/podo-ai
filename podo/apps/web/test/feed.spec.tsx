import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FeedList } from '../components/FeedList'
import { type FeedItem, JobCard } from '../components/JobCard'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function item(id: number, rank: number, fit: number | null): FeedItem {
  return {
    posting: {
      id,
      source: 'toss',
      company: `Co${id}`,
      title: `Job ${id}`,
      role_family: 'frontend',
    },
    fit_level: fit,
    rank_position: rank,
    status: fit === null ? 'held' : 'scored',
    evidence: { e: id },
  }
}

describe('JobCard (AC-1)', () => {
  it('test_AC_1_renders_sorted_with_fit_band_no_percent', () => {
    const { container } = render(<JobCard item={item(1, 0, 5)} />)
    // 적합도 5단계 배지(fit_level 직결) + 라벨
    expect(screen.getByText(/적합도 매우 높음/)).toBeTruthy()
    expect(screen.getByTestId('passband').getAttribute('data-level')).toBe('5')
    // fit 배지
    expect(screen.getByTestId('fitring').textContent).toContain('5')
    // 합격확률/% 텍스트 없음
    expect(container.textContent).not.toContain('%')
  })
})

describe('FeedList cursor infinite scroll (AC-2)', () => {
  it('test_AC_2_cursor_infinite_scroll_appends', async () => {
    const page1 = { items: [item(1, 0, 5), item(2, 1, 4)], nextCursor: 1 }
    const page2 = { items: [item(3, 2, 3)], nextCursor: null }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ json: async () => page1 })
      .mockResolvedValueOnce({ json: async () => page2 })
    vi.stubGlobal('fetch', fetchMock)

    render(<FeedList />)
    // 첫 페이지 (rank_position 순)
    await waitFor(() => expect(screen.getByText('Job 1')).toBeTruthy())
    expect(screen.getByText('Job 2')).toBeTruthy()
    expect(screen.queryByText('Job 3')).toBeNull()

    // 스크롤 끝 = "더 보기" → 다음 페이지 cursor로 append
    fireEvent.click(screen.getByText('더 보기'))
    await waitFor(() => expect(screen.getByText('Job 3')).toBeTruthy())
    expect(screen.getByText('Job 1')).toBeTruthy() // 기존 유지(append)

    expect(String(fetchMock.mock.calls[0][0])).toContain('cursor=-1')
    expect(String(fetchMock.mock.calls[1][0])).toContain('cursor=1')
  })
})
