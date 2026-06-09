import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MaskingPreview } from '../components/MaskingPreview'
import { ResumeUpload } from '../components/ResumeUpload'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// T-034 응답 계약: masked_preview + evidence_summary(skills, experiences)
const MOCK_RESPONSE = {
  data: {
    resume_id: 1,
    masked: true,
    masked_preview:
      '이름: [MASKED_NAME]\n이메일: [MASKED_EMAIL]\n전화: [MASKED_PHONE]\n\n## 스킬\n- TypeScript\n- React\n\n## 경력\n회사A 2년\n회사B 1년',
    placeholders: 3,
    evidence_summary: { skills: 2, experiences: 2 },
  },
}

function txtFile(content = '이름: 홍길동\n이메일: hong@test.com'): File {
  return new File([content], 'resume.txt', { type: 'text/plain' })
}

// T-095 AC-1 — 파일 모드(기본): .txt/.md 업로드 → 기존 흐름(마스킹·preview)이 개선된 UI로 동작.
describe('ResumeUpload file mode (AC-1)', () => {
  it('test_AC_1_file_mode_flow', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => MOCK_RESPONSE }))

    render(<ResumeUpload />)
    // 기본 파일 모드 — 파일 input 노출
    expect(screen.getByTestId('file-input')).toBeTruthy()

    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [txtFile()] } })
    fireEvent.click(screen.getByText('업로드'))

    // 마스킹 preview + evidence 요약 표시
    await waitFor(() => expect(screen.getByTestId('masking-preview')).toBeTruthy())
    expect(screen.getByTestId('evidence-summary').textContent).toContain('스킬 2개')
    expect(screen.getByTestId('evidence-summary').textContent).toContain('경력 2건')
  })
})

describe('MaskingPreview (AC-2)', () => {
  it('test_AC_2_placeholders_highlighted_token_color_no_hex', () => {
    render(
      <MaskingPreview
        maskedText="이메일: [MASKED_EMAIL] 전화: [MASKED_PHONE]"
        evidenceSummary={{ skills: 1, experiences: 1 }}
      />,
    )

    const highlights = screen.getAllByTestId('placeholder-highlight')
    expect(highlights.length).toBeGreaterThanOrEqual(2)

    // raw hex 없음 — 색은 CSS 변수(var(--...))로만
    for (const el of highlights) {
      const style = el.getAttribute('style') ?? ''
      expect(style).not.toMatch(/#[0-9a-fA-F]{3,6}/)
    }
  })
})

// T-095 AC-3 — 두 모드 중 하나로 업로드 성공 시 MaskingPreview 표시 + "분석 시작" 활성.
describe('ResumeUpload preview & start (AC-3)', () => {
  it('test_AC_3_preview_and_start', async () => {
    let resolveFetch!: (v: unknown) => void
    const pendingFetch = new Promise((resolve) => {
      resolveFetch = resolve
    })
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(pendingFetch))

    render(<ResumeUpload />)

    // 업로드 전 — 시작 버튼 disabled
    const startBtn = screen.getByTestId('start-analysis-btn')
    expect(startBtn).toHaveProperty('disabled', true)

    // 파일 업로드
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [txtFile()] } })
    fireEvent.click(screen.getByText('업로드'))

    // 응답 대기 중에도 disabled
    expect(startBtn).toHaveProperty('disabled', true)

    // fetch resolve → preview 수신 → 시작 활성
    resolveFetch({ ok: true, json: async () => MOCK_RESPONSE })
    await waitFor(() => expect(startBtn).toHaveProperty('disabled', false))
    expect(screen.getByTestId('masking-preview')).toBeTruthy()
  })
})
