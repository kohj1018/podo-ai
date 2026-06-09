/**
 * T-039 AC-1: "이 이력서로 분석 시작" 클릭 → score 호출 → feed 이동 → 적합도 배지 렌더
 * 해석 확정(§8): POST /api/v1/resumes/:id/score → router.push('/') → FeedList가 배지 렌더.
 * resume_id 전달: localStorage (단순 옵션 — M3 단일 사용자).
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FeedList } from '../components/FeedList'
import { type FeedItem } from '../components/JobCard'
import { ResumeUpload } from '../components/ResumeUpload'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  localStorage.clear()
})

// 업로드 응답 mock (T-034 계약)
const UPLOAD_RESPONSE = {
  data: {
    resume_id: 42,
    masked: true,
    masked_preview: '이름: [MASKED_NAME]',
    placeholders: 1,
    evidence_summary: { skills: 2, experiences: 1 },
  },
}

function makeFeedItem(id: number, fitLevel: number): FeedItem {
  return {
    posting: { id, source: 'toss', company: `Co${id}`, title: `Job ${id}`, role_family: null },
    fit_level: fitLevel,
    rank_position: 0,
    status: 'scored',
    evidence: {},
  }
}

describe('T-039 AC-1: 분석 시작 → feed 적합도 배지', () => {
  it('test_AC_1_start_navigates_feed_renders_fit_band', async () => {
    // --- 업로드 mock: 첫 POST는 resume 업로드, 두 번째 POST는 score 트리거 ---
    const feedPage = { items: [makeFeedItem(1, 4)], nextCursor: null }
    const fetchMock = vi
      .fn()
      // 1) 업로드 POST /api/v1/resumes
      .mockResolvedValueOnce({ ok: true, json: async () => UPLOAD_RESPONSE })
      // 2) 채점 POST /api/v1/resumes/42/score
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ok: true }) })
      // 3) FeedList GET /api/v1/feed?cursor=-1
      .mockResolvedValueOnce({ ok: true, json: async () => feedPage })
    vi.stubGlobal('fetch', fetchMock)

    // navigation mock — ResumeUpload onNavigateFeed prop로 주입(실앱 기본은 window.location)
    const pushMock = vi.fn()

    // ResumeUpload 렌더 → 업로드 → preview 수신 → 분석 시작 클릭
    render(<ResumeUpload onNavigateFeed={pushMock} />)

    // T-095: 파일 모드(기본)에서 .txt 업로드(이전 paste textarea 대체).
    const file = new File(['이름: 홍길동'], 'resume.txt', { type: 'text/plain' })
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [file] } })
    fireEvent.click(screen.getByText('업로드'))

    // preview 수신 후 "이 이력서로 분석 시작" 버튼 활성
    await waitFor(() =>
      expect(screen.getByTestId('start-analysis-btn')).toHaveProperty('disabled', false),
    )

    // 분석 시작 클릭
    fireEvent.click(screen.getByTestId('start-analysis-btn'))

    // score POST가 호출됐는지 확인
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/resumes/42/score'),
        expect.objectContaining({ method: 'POST' }),
      ),
    )

    // navigation 호출 확인
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith('/'))

    // resume_id가 localStorage에 저장됐는지 확인
    expect(localStorage.getItem('podo_active_resume_id')).toBe('42')

    // --- FeedList가 적합도 배지를 렌더하는지 별도 렌더로 확인 ---
    // (navigation 후 feed 페이지 진입 시뮬레이션)
    cleanup()
    render(<FeedList />)
    await waitFor(() => expect(screen.getByText('Job 1')).toBeTruthy())

    // 적합도 배지(PassBand) 렌더 확인
    const passband = screen.getByTestId('passband')
    expect(passband.getAttribute('data-level')).toBe('4')
    expect(screen.getByText(/적합도 높음/)).toBeTruthy()
  })
})
