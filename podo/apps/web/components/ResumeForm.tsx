'use client'

import { useState } from 'react'

// 직접 작성 폼 — 항목 입력란을 작성 보조 scaffold로 제공(T-095 §2-C 모드 2).
// 제출 시 채워진 항목만 표준 헤딩 마크다운으로 조립 → 기존 단일 blob 흐름에 태운다(구조화 영속 X, 알고리즘 무변경).
// 헤딩은 워커 파싱(parse_resume.py / evidence-summary.ts: ## 경력 · ## 기술스택)과 정합하는 한글 표준 헤딩.
const SECTIONS = [
  {
    key: 'intro',
    heading: '소개',
    label: '소개',
    placeholder: '한두 문장으로 자신을 소개해주세요',
    rows: 2,
  },
  {
    key: 'experience',
    heading: '경력',
    label: '경력',
    placeholder: '회사 · 직무 · 기간 · 한 일',
    rows: 4,
  },
  { key: 'education', heading: '학력', label: '학력', placeholder: '학교 · 전공 · 기간', rows: 2 },
  {
    key: 'certifications',
    heading: '자격증',
    label: '자격증/수상',
    placeholder: '자격증 · 수상 내역',
    rows: 2,
  },
  {
    key: 'skills',
    heading: '기술스택',
    label: '기술스택',
    placeholder: '예: TypeScript, React, Node.js',
    rows: 2,
  },
] as const

// 채워진 항목만 `## {헤딩}\n{값}` 으로 join(빈 항목 헤딩 생략).
export function assembleMarkdown(values: Record<string, string>): string {
  return SECTIONS.filter((s) => values[s.key]?.trim())
    .map((s) => `## ${s.heading}\n${values[s.key].trim()}`)
    .join('\n\n')
}

export function ResumeForm({
  onSubmit,
  disabled,
}: {
  onSubmit: (markdown: string) => void
  disabled?: boolean
}) {
  const [values, setValues] = useState<Record<string, string>>({})
  const markdown = assembleMarkdown(values)

  return (
    <div data-testid="resume-form">
      {SECTIONS.map((s) => (
        <div key={s.key} style={{ marginBottom: '12px' }}>
          <label
            htmlFor={`resume-field-${s.key}`}
            style={{ display: 'block', marginBottom: '4px', fontWeight: 600, color: 'var(--ink)' }}
          >
            {s.label}
          </label>
          <textarea
            id={`resume-field-${s.key}`}
            data-testid={`field-${s.key}`}
            value={values[s.key] ?? ''}
            onChange={(e) => setValues((v) => ({ ...v, [s.key]: e.target.value }))}
            placeholder={s.placeholder}
            rows={s.rows}
            style={{
              display: 'block',
              width: '100%',
              padding: '8px 12px',
              borderRadius: '12px',
              border: '1px solid var(--line-strong)',
              background: 'var(--surface)',
              color: 'var(--ink)',
            }}
          />
        </div>
      ))}
      <button
        type="button"
        data-testid="form-submit-btn"
        disabled={disabled || markdown.length === 0}
        onClick={() => onSubmit(markdown)}
        style={{
          marginTop: '4px',
          padding: '8px 16px',
          borderRadius: '12px',
          border: 'none',
          background: 'var(--grape-600)',
          color: 'var(--surface)',
          opacity: disabled || markdown.length === 0 ? 0.45 : 1,
          cursor: disabled || markdown.length === 0 ? 'not-allowed' : 'pointer',
        }}
      >
        작성 완료
      </button>
    </div>
  )
}
