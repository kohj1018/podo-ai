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

describe('ResumeUpload (AC-1)', () => {
  it('test_AC_1_upload_renders_masking_preview_with_evidence_summary', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => MOCK_RESPONSE }))

    render(<ResumeUpload />)

    // paste 텍스트 입력
    const textarea = screen.getByRole('textbox')
    fireEvent.change(textarea, { target: { value: '이름: 홍길동\n이메일: hong@test.com' } })

    // 업로드 버튼 클릭
    fireEvent.click(screen.getByText('업로드'))

    // 마스킹 preview 패널 표시
    await waitFor(() => expect(screen.getByTestId('masking-preview')).toBeTruthy())

    // evidence 요약("스킬 N개, 경력 M건") 표시
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

    // 플레이스홀더 강조 노드 존재
    const highlights = screen.getAllByTestId('placeholder-highlight')
    expect(highlights.length).toBeGreaterThanOrEqual(2)

    // raw hex 없음 — 색은 CSS 변수(var(--...))로만
    for (const el of highlights) {
      const style = el.getAttribute('style') ?? ''
      expect(style).not.toMatch(/#[0-9a-fA-F]{3,6}/)
    }
  })
})

describe('ResumeUpload 시작 버튼 (AC-3)', () => {
  it('test_AC_3_start_button_disabled_until_response', async () => {
    // 응답 지연 시뮬레이션 — fetch가 resolve되기 전까지 pending 유지
    let resolveFetch!: (v: unknown) => void
    const pendingFetch = new Promise((resolve) => {
      resolveFetch = resolve
    })
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(pendingFetch))

    render(<ResumeUpload />)

    // 업로드 전 — 시작 버튼 disabled
    const startBtn = screen.getByTestId('start-analysis-btn')
    expect(startBtn).toHaveProperty('disabled', true)

    // paste 입력 후 업로드
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: '이름: 홍길동' },
    })
    fireEvent.click(screen.getByText('업로드'))

    // 응답 대기 중에도 여전히 disabled
    expect(startBtn).toHaveProperty('disabled', true)

    // fetch resolve — preview 수신 후 enabled
    resolveFetch({ ok: true, json: async () => MOCK_RESPONSE })
    await waitFor(() => expect(startBtn).toHaveProperty('disabled', false))
  })
})
