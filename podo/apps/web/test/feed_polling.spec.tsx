import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FeedView } from '../components/FeedView'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

// 채점 중(queued/running) 정지 버그 회귀 — meta를 폴링해 worker 완료 시 자동으로 피드 전환.
describe('FeedView scoring polling', () => {
  it('test_scoring_polls_until_done', async () => {
    vi.useFakeTimers()
    let metaCalls = 0
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string | URL) => {
        const u = String(url)
        if (u.includes('feed/meta')) {
          metaCalls += 1
          const scoring_status = metaCalls >= 2 ? 'done' : 'running'
          return Promise.resolve({
            ok: true,
            json: async () => ({
              has_resume: true,
              scoring_status,
              diff_summary: { new_count: 1, expiring_count: 0 },
              total_pending_count: 0,
              visible_count: scoring_status === 'done' ? 1 : 0,
            }),
          })
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({
            items: [
              {
                posting: { id: 1, source: 'toss', company: 'Co', title: 'FE', closing_at: null },
                fit_level: 5,
                rank_position: 0,
                status: 'scored',
                evidence: {},
              },
            ],
            nextCursor: null,
          }),
        })
      }),
    )

    render(<FeedView />)
    // 첫 meta(running) → "분석 중" skeleton
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(screen.getByTestId('feed-scoring')).toBeTruthy()
    expect(metaCalls).toBe(1)

    // 폴링 interval(3.5s) 경과 → 두 번째 meta(done) → 피드 자동 전환(수동 새로고침 불필요)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3600)
    })
    expect(screen.queryByTestId('feed-scoring')).toBeNull()
    expect(screen.getByTestId('greeting-card')).toBeTruthy()
    expect(metaCalls).toBeGreaterThanOrEqual(2)
  })
})
