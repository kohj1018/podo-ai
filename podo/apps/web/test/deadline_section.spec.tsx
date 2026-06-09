import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { DeadlineSection } from '../components/DeadlineSection'
import type { FeedItem } from '../components/JobCard'

afterEach(cleanup)

function makeItem(id: number, closingAt: string | null): FeedItem {
  return {
    posting: {
      id,
      source: 'toss',
      company: '토스',
      title: `공고 ${id}`,
      closing_at: closingAt,
    },
    fit_level: 3,
    rank_position: id,
    status: 'ready',
    evidence: null,
  }
}

function daysFromNow(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString()
}

describe('DeadlineSection (AC-1)', () => {
  it('test_AC_1_expiring_section_renders_or_hidden — 임박 있으면 섹션 렌더', () => {
    const items: FeedItem[] = [
      makeItem(1, daysFromNow(3)), // 임박 (≤7일)
      makeItem(2, daysFromNow(10)), // 임박 아님
      makeItem(3, null), // closing_at 없음
    ]
    render(<DeadlineSection items={items} />)
    // 임박 섹션이 렌더돼야 함
    const section = screen.getByRole('region', { name: '마감 임박' })
    expect(section).toBeTruthy()
    // 임박 공고 회사/직무 포함
    expect(section.textContent).toContain('토스')
  })

  it('test_AC_1_expiring_section_renders_or_hidden — 임박 0이면 DOM 미렌더', () => {
    const items: FeedItem[] = [
      makeItem(1, daysFromNow(10)), // 임박 아님
      makeItem(2, null), // closing_at 없음
    ]
    const { container } = render(<DeadlineSection items={items} />)
    // 빈 헤더 금지 — 섹션 DOM 자체 없어야 함
    expect(container.firstChild).toBeNull()
  })

  it('test_AC_1_expiring_section_renders_or_hidden — closing_at 전부 null이면 미렌더', () => {
    const items: FeedItem[] = [makeItem(1, null), makeItem(2, null)]
    const { container } = render(<DeadlineSection items={items} />)
    expect(container.firstChild).toBeNull()
  })

  it('test_AC_1_expiring_section_renders_or_hidden — 최대 5개만 렌더', () => {
    const items: FeedItem[] = Array.from({ length: 8 }, (_, i) =>
      makeItem(i + 1, daysFromNow(i + 1)),
    ) // 전부 임박(D-1~D-8, 8개)
    render(<DeadlineSection items={items} />)
    const cards = screen.getAllByTestId('deadline-item')
    expect(cards.length).toBeLessThanOrEqual(5)
  })
})
