import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CoveragePanel } from '../components/CoveragePanel'
import { type FeedItem, JobCard } from '../components/JobCard'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const EVIDENCE = {
  matching_tables: {
    '7': {
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

function scored(): FeedItem {
  return {
    posting: { id: 7, source: 'toss', company: 'Toss', title: 'FE', role_family: 'frontend' },
    fit_level: 4,
    rank_position: 0,
    status: 'scored',
    evidence: EVIDENCE,
  }
}

function held(): FeedItem {
  return {
    posting: { id: 8, source: 'daangn', company: 'Daangn', title: 'BE', role_family: 'backend' },
    fit_level: null,
    rank_position: 1,
    status: 'held',
    evidence: {},
  }
}

describe('EvidenceBlock expand (AC-1)', () => {
  it('test_AC_1_evidence_expand_shows_citation_mapping', () => {
    render(<JobCard item={scored()} />)
    // 펼침 전 — 근거 미표시
    expect(screen.queryByText(/React 개발 경험/)).toBeNull()
    fireEvent.click(screen.getByText('근거 보기'))
    // 이력서 원문(evidence_quotes)은 표시하지 않는다 — JD 요구사항 + 충족 여부만(PII 보호).
    expect(screen.queryByText(/React 18 프로젝트 3년/)).toBeNull()
    expect(screen.getByText(/React 개발 경험/)).toBeTruthy()
    expect(screen.getByTestId('evidence-block').textContent).toContain('충족')
  })
})

describe('CoveragePanel (AC-2)', () => {
  it('test_AC_2_coverage_panel_renders', async () => {
    const cov = {
      channels: [
        { name: 'toss', status: 'success', last_success_at: '2026-06-06T01:00:00.000Z' },
        { name: 'daangn', status: null, last_success_at: null },
      ],
      uncollected: ['daangn'],
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => cov }))
    render(<CoveragePanel />)
    // 친근한 footer — 활성 채널 chip(토스) + "그 외 채널 미수집" + 정직 고지.
    await waitFor(() => expect(screen.getByTestId('coverage-panel')).toBeTruthy())
    const panel = screen.getByTestId('coverage-panel')
    expect(panel.textContent).toContain('토스') // toss(success) → 활성 chip(한글 표시명)
    expect(screen.getByTestId('coverage-uncollected')).toBeTruthy() // daangn null → 미수집
    expect(panel.textContent).toContain('미수집 채널은 추천에 포함되지 않아요') // 정직 고지
  })
})

describe('CoveragePanel error state (REV-M2-UI-001)', () => {
  it('test_coverage_error_surfaces_not_silent', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network')))
    render(<CoveragePanel />)
    // 실패를 삼키지 않고(Fail#3) 에러 노출 — 영구 "불러오는 중" 금지
    await waitFor(() =>
      expect(screen.getByTestId('coverage-panel').getAttribute('data-state')).toBe('error'),
    )
    expect(screen.getByTestId('coverage-panel').textContent).toContain('불러오지 못')
  })
})

describe('Held state (AC-3)', () => {
  it('test_AC_3_held_shows_pending_not_fake', () => {
    render(<JobCard item={held()} />)
    // 보류 상태 = PendingState(T-047) — 가짜 점수 대신 정직한 보류
    expect(screen.getByTestId('pending-state').textContent).toContain('보류했어요')
    // 가짜 점수/band 미표시 (fit 링·PassBand 없음)
    expect(screen.queryByTestId('fitring')).toBeNull()
    expect(screen.queryByTestId('passband')).toBeNull()
  })
})
