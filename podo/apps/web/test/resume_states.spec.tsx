import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ResumeUpload } from '../components/ResumeUpload'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// AC-1: 비허용 포맷(.pdf 등) 선택 시 안내 + 업로드 미전송
// AC-1: 100KB 초과 파일 선택 시 안내 + 업로드 미전송
describe('ResumeUpload 상태 매트릭스 (AC-1)', () => {
  it('test_AC_1_non_txt_and_oversize_show_message_no_upload', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<ResumeUpload />)

    const input = screen.getByTestId('file-input')

    // .pdf 파일 선택 — 비허용 포맷
    const pdfFile = new File(['content'], 'resume.pdf', { type: 'application/pdf' })
    fireEvent.change(input, { target: { files: [pdfFile] } })

    // 포맷 안내 메시지 표시
    expect(screen.getByTestId('format-error')).toBeTruthy()
    expect(screen.getByTestId('format-error').textContent).toContain(
      '현재 .txt / .md 파일 또는 텍스트 붙여넣기만 지원합니다.',
    )

    // fetch 미호출 — 업로드 전송 없음
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('test_AC_1_oversize_shows_size_message_no_upload', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<ResumeUpload />)

    const input = screen.getByTestId('file-input')

    // 100KB 초과 .txt 파일
    const bigContent = 'a'.repeat(101 * 1024)
    const bigFile = new File([bigContent], 'resume.txt', { type: 'text/plain' })
    fireEvent.change(input, { target: { files: [bigFile] } })

    // 크기 안내 메시지 표시
    expect(screen.getByTestId('format-error')).toBeTruthy()
    expect(screen.getByTestId('format-error').textContent).toContain(
      '파일이 너무 큽니다(최대 100KB).',
    )

    // fetch 미호출
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

// AC-2: 로딩 중 skeleton 표시, 가짜 점수/preview 미표시
// AC-2: prefers-reduced-motion 분기
describe('ResumeUpload 상태 매트릭스 (AC-2)', () => {
  it('test_AC_2_loading_skeleton_no_fake_score', async () => {
    // fetch가 resolve되지 않는 상태 유지
    let resolveFetch!: (v: unknown) => void
    const pendingFetch = new Promise((resolve) => {
      resolveFetch = resolve
    })
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(pendingFetch))

    render(<ResumeUpload />)

    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: '이력서 내용' } })
    fireEvent.click(screen.getByText('업로드'))

    // 로딩 중 skeleton 존재
    const skeleton = screen.getByTestId('loading-skeleton')
    expect(skeleton).toBeTruthy()

    // skeleton 막대가 .shimmer 클래스 보유 — globals.css @media (prefers-reduced-motion) 규칙의 hook
    expect(skeleton.querySelectorAll('.shimmer').length).toBeGreaterThan(0)

    // "이력서 분석 중…" 텍스트 표시
    expect(screen.getByText('이력서 분석 중…')).toBeTruthy()

    // 가짜 점수/preview 미표시 — masking-preview 없음
    expect(screen.queryByTestId('masking-preview')).toBeNull()

    // cleanup
    resolveFetch({ ok: false })
  })
})
