import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { type FeedItem, JobCard } from '../components/JobCard'

afterEach(() => cleanup())

const HEX = /#[0-9a-fA-F]{3,6}/

const EVIDENCE = {
  matching_tables: {
    7: {
      rows: [
        {
          requirement_text: 'React 개발 경험',
          evidence_quotes: ['React 18 프로젝트 3년'],
          match_level: 'direct',
        },
      ],
    },
  },
}

function scored(level: number, evidence: unknown = EVIDENCE): FeedItem {
  return {
    posting: { id: 7, source: 'toss', company: 'Toss', title: 'FE', role_family: 'frontend' },
    fit_level: level,
    rank_position: 0,
    status: 'scored',
    evidence,
  }
}

function held(url?: string): FeedItem {
  return {
    posting: {
      id: 8,
      source: 'daangn',
      company: 'Daangn',
      title: 'BE',
      role_family: 'backend',
      url,
    },
    fit_level: null,
    rank_position: 1,
    status: 'held',
    evidence: {},
  }
}

describe('JobCard PassBand + FitScoreRing (AC-1)', () => {
  it('test_AC_1_pass_band_token_color_no_hex_ring_fenced_gradient', () => {
    render(<JobCard item={scored(5)} />)

    // PassBand: 5단계 텍스트 라벨 + band-5 토큰(DESIGN canonical "매우 높음")
    expect(screen.getByTestId('passband').getAttribute('data-level')).toBe('5')
    const label = screen.getByText('적합도 매우 높음')
    expect(label.getAttribute('style') ?? '').toContain('var(--band-5-ink)')

    // FitScoreRing: fenced gradient(토큰) + raw hex 0
    const ring = screen.getByTestId('fitring')
    const style = ring.getAttribute('style') ?? ''
    expect(style).toContain('var(--brand-gradient)')
    expect(style).not.toMatch(HEX)
  })
})

describe('JobCard EvidenceBlock toggle (AC-2)', () => {
  it('test_AC_2_evidence_block_keyboard_toggle_aria_expanded', () => {
    render(<JobCard item={scored(4)} />)

    const toggle = screen.getByTestId('evidence-toggle')
    // 토글은 네이티브 button(Enter/Space 활성) + aria-expanded
    expect(toggle.tagName).toBe('BUTTON')
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByTestId('evidence-block')).toBeNull()

    fireEvent.click(toggle) // 버튼 활성(키보드 Enter/Space와 동일 동작)
    expect(toggle.getAttribute('aria-expanded')).toBe('true')

    // JD 요구사항 + 충족(✓) 렌더 — 이력서 원문(evidence_quotes)은 미표시(PII 보호)
    const block = screen.getByTestId('evidence-block')
    expect(block.getAttribute('id')).toBe(toggle.getAttribute('aria-controls'))
    expect(screen.queryByText(/React 18 프로젝트 3년/)).toBeNull()
    expect(screen.getByText(/React 개발 경험/)).toBeTruthy()
  })
})

describe('JobCard held → PendingState (AC-3)', () => {
  it('test_AC_3_held_job_pending_state_no_fake_score', () => {
    render(<JobCard item={held('https://daangn.test/8')} />)

    // dashed 보류 카드 + 원문 링크
    expect(screen.getByTestId('pending-state')).toBeTruthy()
    expect(screen.getByText('원문 보기').getAttribute('href')).toBe('https://daangn.test/8')

    // 어떤 숫자 점수도 없음 — FitScoreRing·PassBand 미렌더
    expect(screen.queryByTestId('fitring')).toBeNull()
    expect(screen.queryByTestId('passband')).toBeNull()
  })
})
