import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import HomePage from '../app/page'
import { ResumeUpload } from '../components/ResumeUpload'
import { SessionProvider } from '../components/SessionProvider'

// AuthGate가 useRouter 사용 — authed 경로에선 replace 미호출.
const { replace } = vi.hoisted(() => ({ replace: vi.fn() }))
vi.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }))

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  replace.mockClear()
  localStorage.clear()
})

const UPLOAD_RESP = {
  data: {
    resume_id: 77,
    masked: true,
    masked_preview: '이름: [MASKED_NAME]\n\n## 소개\n프론트엔드 신입',
    placeholders: 1,
    evidence_summary: { skills: 1, experiences: 1 },
  },
}

const READY_META = {
  has_resume: true,
  scoring_status: 'done',
  diff_summary: { new_count: 1, expiring_count: 0 },
  total_pending_count: 0,
  visible_count: 1,
  resume_domains: null,
}

const FEED = {
  items: [
    {
      posting: { id: 1, source: 'toss', company: '토스', title: 'FE', closing_at: null },
      fit_level: 5,
      rank_position: 0,
      status: 'scored',
      evidence: { e: 1 },
    },
  ],
  nextCursor: null,
}

function routedFetch(routes: Array<[string, unknown]>) {
  return vi.fn((url: string | URL) => {
    const u = String(url)
    for (const [key, val] of routes) {
      if (u.includes(key)) {
        return Promise.resolve({ ok: true, json: async () => val })
      }
    }
    return Promise.resolve({ ok: true, json: async () => ({ items: [], nextCursor: null }) })
  })
}

// T-102 AC-1 — 골든패스(로그인 게이트 → 이력서 직접작성 입력 → 제출 → 채점 → 피드 분석결과)가
// 끊김 없이 이어진다. (UI 통합; full-stack 종단은 scripts/e2e.mjs.)
describe('Golden path: signup → resume → feed (AC-1)', () => {
  it('test_AC_1_signup_to_feed', async () => {
    // ── 1) /resume 입력(직접 작성 폼) → 제출 → 마스킹 preview → 분석 시작 → 채점 → 피드 이동 ──
    const onNav = vi.fn()
    const resumeFetch = vi.fn((url: string | URL, _init?: { body?: string }) => {
      const u = String(url)
      if (u.includes('/score'))
        return Promise.resolve({ ok: true, json: async () => ({ ok: true }) })
      return Promise.resolve({ ok: true, json: async () => UPLOAD_RESP })
    })
    vi.stubGlobal('fetch', resumeFetch)

    render(<ResumeUpload onNavigateFeed={onNav} />)
    fireEvent.click(screen.getByTestId('mode-form')) // 직접 작성 모드
    fireEvent.change(screen.getByTestId('field-intro'), { target: { value: '프론트엔드 신입' } })
    fireEvent.change(screen.getByTestId('field-experience'), { target: { value: '토스 FE 인턴' } })
    fireEvent.click(screen.getByTestId('form-submit-btn'))

    // 표준 헤딩 마크다운으로 {text} POST
    await waitFor(() => expect(screen.getByTestId('masking-preview')).toBeTruthy())
    const upload = resumeFetch.mock.calls.find((c) => !String(c[0]).includes('/score'))
    const body = JSON.parse(upload?.[1]?.body ?? '{}')
    expect(body.text).toContain('## 소개')
    expect(body.text).toContain('## 경력')

    // 분석 시작 → 채점 1회 → 피드 이동 + active 교체
    fireEvent.click(screen.getByTestId('start-analysis-btn'))
    await waitFor(() => expect(onNav).toHaveBeenCalledWith('/'))
    expect(localStorage.getItem('podo_active_resume_id')).toBe('77')

    cleanup()
    vi.unstubAllGlobals()

    // ── 2) 피드 진입 → 분석결과(적합도 배지) 렌더, 끊김(401/stale)·재채점 없음 ──
    vi.stubGlobal(
      'fetch',
      routedFetch([
        ['auth/me', { data: { userId: 'u1' } }],
        ['coverage', { channels: [], uncollected: [], degraded: false }],
        ['feed/meta', READY_META],
        ['feed', FEED],
      ]),
    )
    const feedFetch = global.fetch as ReturnType<typeof vi.fn>

    render(
      <SessionProvider>
        <HomePage />
      </SessionProvider>,
    )

    // 피드 분석결과: greeting + 적합도 배지(job-card) 렌더
    await waitFor(() => expect(screen.getByTestId('greeting-card')).toBeTruthy())
    expect(screen.getByTestId('job-card')).toBeTruthy()
    expect(screen.getByTestId('passband')).toBeTruthy()
    // 피드 탐색은 재채점 0 (T-096 보존) + 리다이렉트 없음
    expect(feedFetch.mock.calls.every((c) => !String(c[0]).includes('/score'))).toBe(true)
    expect(replace).not.toHaveBeenCalled()
  })

  it('test_AC_2_new_user_no_feed_flash', async () => {
    // 신규(이력서 없음) 진입 → meta 로드 전 게이트 skeleton(피드 미렌더) → /resume 리다이렉트.
    // 피드(coverage-panel)가 깜빡이지 않아야 함(T-102 통합 스윕 수정).
    vi.stubGlobal(
      'fetch',
      routedFetch([
        ['auth/me', { data: { userId: 'u1' } }],
        ['feed/meta', { has_resume: false }],
      ]),
    )

    render(
      <SessionProvider>
        <HomePage />
      </SessionProvider>,
    )

    await waitFor(() => expect(replace).toHaveBeenCalledWith('/resume'))
    // 리다이렉트 전/후 모두 피드 깜빡임 없음
    expect(screen.queryByTestId('coverage-panel')).toBeNull()
  })
})
