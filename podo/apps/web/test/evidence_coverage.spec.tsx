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
    expect(screen.queryByText(/React 18 프로젝트 3년/)).toBeNull()
    fireEvent.click(screen.getByText('근거 보기'))
    // JD 인용 + 매핑 requirement (표시 전용)
    expect(screen.getByText(/React 18 프로젝트 3년/)).toBeTruthy()
    expect(screen.getByText(/React 개발 경험/)).toBeTruthy()
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
    // T-090: 기본 compact strip → 채널 상세는 펼침 토글 후 노출.
    await waitFor(() =>
      expect(screen.getByTestId('coverage-panel').getAttribute('data-state')).toBe('ready'),
    )
    fireEvent.click(screen.getByTestId('coverage-toggle'))
    const panel = screen.getByTestId('coverage-panel')
    expect(panel.textContent).toContain('toss')
    expect(panel.textContent).toContain('daangn') // 수집/미수집 채널
    expect(panel.textContent).toContain('마지막 성공') // 마지막 성공 시각
    expect(panel.textContent).toContain('미수집') // 미수집 명시
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
    expect(screen.getByTestId('pending-state').textContent).toContain('분석하지 못했어요')
    // 가짜 점수/band 미표시 (fit 링·PassBand 없음)
    expect(screen.queryByTestId('fitring')).toBeNull()
    expect(screen.queryByTestId('passband')).toBeNull()
  })
})
