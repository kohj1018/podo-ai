import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ResumeForm, assembleMarkdown } from '../components/ResumeForm'

afterEach(cleanup)

// T-095 AC-2 — 채워진 항목만 표준 헤딩 마크다운으로 조립(빈 항목 헤딩 생략) → onSubmit 전달.
describe('ResumeForm sections → markdown (AC-2)', () => {
  it('test_AC_2_sections_to_markdown', () => {
    const onSubmit = vi.fn()
    render(<ResumeForm onSubmit={onSubmit} />)

    // 빈 폼 → 제출 버튼 비활성
    const submit = screen.getByTestId('form-submit-btn') as HTMLButtonElement
    expect(submit.disabled).toBe(true)

    // 소개 · 경력만 입력(학력/자격증/기술스택 비움)
    fireEvent.change(screen.getByTestId('field-intro'), {
      target: { value: '프론트엔드 신입입니다' },
    })
    fireEvent.change(screen.getByTestId('field-experience'), {
      target: { value: '토스 · FE 인턴 · 6개월' },
    })

    fireEvent.click(submit)

    // 채워진 항목만 표준 한글 헤딩으로 조립, 빈 항목(학력/자격증/기술스택) 헤딩 생략
    expect(onSubmit).toHaveBeenCalledTimes(1)
    const md = onSubmit.mock.calls[0][0] as string
    expect(md).toBe('## 소개\n프론트엔드 신입입니다\n\n## 경력\n토스 · FE 인턴 · 6개월')
    expect(md).not.toContain('## 학력')
    expect(md).not.toContain('## 자격증')
    expect(md).not.toContain('## 기술스택')
  })

  it('test_assemble_skips_blank_and_trims', () => {
    // 순수 조립 함수 — 공백만 있는 항목은 생략, 값은 trim.
    const md = assembleMarkdown({ intro: '  안녕  ', experience: '   ', skills: 'React, TS' })
    expect(md).toBe('## 소개\n안녕\n\n## 기술스택\nReact, TS')
  })
})
