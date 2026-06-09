import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CoveragePanel } from '../components/CoveragePanel'
import { GreetingCard } from '../components/GreetingCard'
import { type FeedItem, JobCard } from '../components/JobCard'
import { MaskingPreview } from '../components/MaskingPreview'
import { ResumeUpload } from '../components/ResumeUpload'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function scoredItem(): FeedItem {
  return {
    posting: { id: 7, source: 'toss', company: 'Toss', title: 'FE', role_family: 'frontend' },
    fit_level: 5,
    rank_position: 0,
    status: 'scored',
    evidence: {},
  }
}

describe('a11y — ARIA roles/labels + band ink (AC-1)', () => {
  it('test_AC_1_keyboard_and_aria_roles_and_band_ink_contrast', () => {
    // JobCard: article aria-label + EvidenceBlock aria-expanded + PassBand aria-label + band-5-ink
    const { unmount } = render(<JobCard item={scoredItem()} />)
    expect(screen.getByRole('article', { name: 'Toss FE' })).toBeTruthy()
    expect(screen.getByTestId('evidence-toggle').getAttribute('aria-expanded')).toBe('false')
    expect(screen.getByTestId('passband').getAttribute('aria-label')).toContain('적합도')
    // band 텍스트 = band-*-ink 토큰(AA 대비)
    expect(screen.getByText('적합도 매우 높음').getAttribute('style')).toContain(
      'var(--band-5-ink)',
    )
    unmount()

    // GreetingCard: 암묵 region
    render(<GreetingCard newCount={1} expiringCount={0} />)
    expect(screen.getByRole('region', { name: '오늘의 요약' })).toBeTruthy()
    cleanup()

    // MaskingPreview: 암묵 region (DSN-M3-003)
    render(
      <MaskingPreview
        maskedText="이메일 [MASKED_EMAIL]"
        evidenceSummary={{ skills: 1, experiences: 1 }}
      />,
    )
    expect(screen.getByRole('region', { name: '마스킹 미리보기' })).toBeTruthy()
    cleanup()

    // ResumeUpload: 파일 input 접근 가능한 label (DSN-M3-001)
    render(<ResumeUpload />)
    expect(screen.getByLabelText('이력서 파일 업로드')).toBeTruthy()
  })

  it('test_AC_1_coverage_panel_region_and_alert', async () => {
    // ready → 암묵 region
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          channels: [{ name: 'toss', status: 'success', last_success_at: null }],
          uncollected: [],
          degraded: false,
        }),
      }),
    )
    render(<CoveragePanel />)
    await waitFor(() => expect(screen.getByRole('region', { name: '수집 현황' })).toBeTruthy())
    cleanup()
    vi.unstubAllGlobals()

    // degraded → role=alert
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ channels: [], uncollected: ['toss'], degraded: true }),
      }),
    )
    render(<CoveragePanel />)
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
  })

  it('test_AC_1_resume_upload_aria_busy_on_loading', async () => {
    let resolveFetch!: (v: unknown) => void
    const pending = new Promise((r) => {
      resolveFetch = r
    })
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(pending))

    render(<ResumeUpload />)
    // T-095: 파일 모드(기본)에서 .txt 업로드 → 로딩 진입.
    const file = new File(['이름: 홍길동'], 'resume.txt', { type: 'text/plain' })
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [file] } })
    fireEvent.click(screen.getByText('업로드'))

    // 업로드 중 skeleton에 aria-busy (DSN-M3-002)
    await waitFor(() =>
      expect(screen.getByTestId('loading-skeleton').getAttribute('aria-busy')).toBe('true'),
    )
    resolveFetch({
      ok: true,
      json: async () => ({
        data: {
          resume_id: 1,
          masked: true,
          masked_preview: 'x',
          placeholders: 0,
          evidence_summary: { skills: 0, experiences: 0 },
        },
      }),
    })
  })
})
