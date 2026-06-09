import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FeedView } from '../components/FeedView'
import { ResumeUpload } from '../components/ResumeUpload'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  localStorage.clear()
})

function uploadResp(id: number) {
  return {
    data: {
      resume_id: id,
      masked: true,
      masked_preview: '이름: [MASKED_NAME]',
      placeholders: 1,
      evidence_summary: { skills: 1, experiences: 1 },
    },
  }
}

function txtFile(): File {
  return new File(['이름: 홍길동'], 'resume.txt', { type: 'text/plain' })
}

// T-096 AC-1 — 수정 제출 시 새 resume를 정확히 1회 채점하고 active 교체.
describe('Resume edit lifecycle (AC-1)', () => {
  it('test_AC_1_edit_creates_new_and_scores_once', async () => {
    const onNav = vi.fn()
    const fetchMock = vi.fn((url: string | URL) => {
      const u = String(url)
      if (u.includes('/score'))
        return Promise.resolve({ ok: true, json: async () => ({ ok: true }) })
      return Promise.resolve({ ok: true, json: async () => uploadResp(50) })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<ResumeUpload onNavigateFeed={onNav} />)
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [txtFile()] } })
    fireEvent.click(screen.getByText('업로드'))
    await waitFor(() =>
      expect(screen.getByTestId('start-analysis-btn')).toHaveProperty('disabled', false),
    )

    fireEvent.click(screen.getByTestId('start-analysis-btn'))
    await waitFor(() => expect(onNav).toHaveBeenCalledWith('/'))

    const scoreCalls = () =>
      fetchMock.mock.calls.filter((c) => String(c[0]).includes('/resumes/50/score'))
    expect(scoreCalls()).toHaveLength(1) // 정확히 1회
    expect(localStorage.getItem('podo_active_resume_id')).toBe('50') // active 교체

    // 동일 이력서 재클릭 → 중복 채점 없음(여전히 1회)
    fireEvent.click(screen.getByTestId('start-analysis-btn'))
    await waitFor(() => expect(onNav).toHaveBeenCalledTimes(2))
    expect(scoreCalls()).toHaveLength(1)
  })
})

// T-096 AC-2 — 피드 재진입·탐색은 채점을 트리거하지 않는다(score 호출 0).
describe('Feed browsing no rescore (AC-2)', () => {
  it('test_AC_2_browsing_no_rescore', async () => {
    const fetchMock = vi.fn((url: string | URL) => {
      const u = String(url)
      if (u.includes('feed/meta')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            has_resume: true,
            scoring_status: 'done',
            diff_summary: { new_count: 1, expiring_count: 0 },
            total_pending_count: 0,
            visible_count: 1,
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
              evidence: { e: 1 },
            },
          ],
          nextCursor: null,
        }),
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<FeedView />)
    await waitFor(() => expect(screen.getByTestId('greeting-card')).toBeTruthy())

    // 피드 탐색 중 score POST 0건
    const scoreCalls = fetchMock.mock.calls.filter((c) => String(c[0]).includes('/score'))
    expect(scoreCalls).toHaveLength(0)
  })
})

// T-096 AC-3 — score 실패(non-2xx) 시 피드 미이동 + 에러/재시도(현 res.ok 미검사 회귀 차단).
describe('Score failure no nav (AC-3)', () => {
  it('test_AC_3_score_failure_no_nav_shows_error', async () => {
    const onNav = vi.fn()
    let scoreOk = false
    const fetchMock = vi.fn((url: string | URL) => {
      const u = String(url)
      if (u.includes('/score')) {
        return Promise.resolve({ ok: scoreOk, status: scoreOk ? 200 : 500, json: async () => ({}) })
      }
      return Promise.resolve({ ok: true, json: async () => uploadResp(60) })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<ResumeUpload onNavigateFeed={onNav} />)
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [txtFile()] } })
    fireEvent.click(screen.getByText('업로드'))
    await waitFor(() =>
      expect(screen.getByTestId('start-analysis-btn')).toHaveProperty('disabled', false),
    )

    // 채점 실패 → 미이동 + 에러
    fireEvent.click(screen.getByTestId('start-analysis-btn'))
    await waitFor(() => expect(screen.getByTestId('score-error')).toBeTruthy())
    expect(onNav).not.toHaveBeenCalled()
    expect(localStorage.getItem('podo_active_resume_id')).toBeNull()

    // 재시도 성공 → 이동
    scoreOk = true
    fireEvent.click(screen.getByTestId('start-analysis-btn'))
    await waitFor(() => expect(onNav).toHaveBeenCalledWith('/'))
    expect(localStorage.getItem('podo_active_resume_id')).toBe('60')
  })
})
