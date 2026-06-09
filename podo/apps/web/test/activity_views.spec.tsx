import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ActivityList } from '../components/ActivityList'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function mockData(items: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ data: items }) }),
  )
}

const FAV = {
  id: 1,
  job_posting_id: 9,
  action: 'favorite',
  job_posting: { company: '토스', title: '프론트엔드 엔지니어', url: 'https://toss/job/9' },
}
const APP = {
  id: 2,
  job_posting_id: 10,
  action: 'applied',
  job_posting: { company: '당근', title: '백엔드 엔지니어', url: null },
}

// T-094 — 즐겨찾기/지원기록 뷰가 실 API 목록을 공고 정보와 함께 렌더, 빈/에러 일급 노출.
describe('ActivityList (AC-1, AC-2, AC-3)', () => {
  it('test_AC_1_favorites_list', async () => {
    mockData([FAV])
    render(<ActivityList filter="favorite" />)
    await waitFor(() => expect(screen.getByTestId('activity-list')).toBeTruthy())
    const item = screen.getByTestId('activity-item')
    expect(item.textContent).toContain('토스')
    expect(item.textContent).toContain('프론트엔드 엔지니어')
    expect(screen.getByText('공고 보기').getAttribute('href')).toBe('https://toss/job/9')
  })

  it('test_AC_2_applications_list', async () => {
    mockData([APP])
    render(<ActivityList filter="applied" />)
    await waitFor(() => expect(screen.getByTestId('activity-list')).toBeTruthy())
    expect(screen.getByTestId('activity-item').textContent).toContain('당근')
    // url 없으면 "공고 보기" 링크 미렌더
    expect(screen.queryByText('공고 보기')).toBeNull()
  })

  it('test_AC_3_empty_and_error', async () => {
    // 빈 목록 → 빈 상태(빈 목록으로 삼키지 않음)
    mockData([])
    const { unmount } = render(<ActivityList filter="favorite" />)
    await waitFor(() => expect(screen.getByTestId('activity-empty')).toBeTruthy())
    expect(screen.queryByTestId('activity-list')).toBeNull()
    unmount()
    vi.unstubAllGlobals()

    // fetch 실패 → 에러 상태
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network')))
    render(<ActivityList filter="applied" />)
    await waitFor(() => expect(screen.getByTestId('activity-error')).toBeTruthy())
    expect(screen.getByTestId('activity-error').getAttribute('role')).toBe('alert')
  })
})
