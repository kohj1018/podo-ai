'use client'

import { useCallback, useEffect, useState } from 'react'
import { FeedList } from './FeedList'
import { GreetingCard } from './GreetingCard'
import { Onboarding } from './Onboarding'
import { PodoMascot } from './PodoMascot'

interface FeedMeta {
  has_resume: boolean
  scoring_status: 'queued' | 'running' | 'done' | 'failed' | null
  diff_summary: { new_count: number; expiring_count: number }
  total_pending_count: number
  visible_count: number
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

// 분석 중 skeleton — .shimmer는 globals.css에서 reduced-motion 분기(정적). 가짜 점수 미표시.
function ScoringSkeleton({ label }: { label: string }) {
  return (
    <section
      data-testid="feed-scoring"
      aria-busy="true"
      aria-label={label}
      style={{ maxWidth: '430px', margin: '0 auto', padding: '16px' }}
    >
      <div
        className="shimmer"
        style={{ height: '64px', borderRadius: '16px', marginBottom: '12px' }}
      />
      <div className="shimmer" style={{ height: '88px', borderRadius: '16px' }} />
      <p style={{ color: 'var(--muted)', marginTop: '12px' }}>{label}</p>
    </section>
  )
}

// 피드 진입 8-상태 분기(F-018, DESIGN §7-4). meta(/api/v1/feed/meta)로 상태 결정.
// ready/pending에서만 FeedList(items 커서 페이지네이션)로 위임 — 기존 FeedList 재사용.
export function FeedView({ domain }: { domain?: string } = {}) {
  const [meta, setMeta] = useState<FeedMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [resurface, setResurface] = useState(false) // 신규 적은 날 최근 7일 재노출(T-092)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const res = await fetch(`${API_BASE}/api/v1/feed/meta`, { credentials: 'include' })
      if (!res.ok) throw new Error(`meta ${res.status}`)
      setMeta((await res.json()) as FeedMeta)
    } catch {
      setError(true) // 실패를 삼키지 않음(REV-M2-UI-001)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  // 1) loading
  if (loading) {
    return <ScoringSkeleton label="불러오는 중…" />
  }

  // 2) error — 수집/채점 상태 로드 실패(숨기지 않음)
  if (error || !meta) {
    return (
      <section
        data-testid="feed-state-error"
        role="alert"
        style={{
          maxWidth: '430px',
          margin: '0 auto',
          padding: '24px 16px',
          color: 'var(--band-1-ink)',
        }}
      >
        <PodoMascot size={52} />
        <p style={{ fontWeight: 600 }}>아침 배달이 늦어요. 잠시 후 다시 시도해주세요.</p>
        <button
          type="button"
          onClick={() => void load()}
          style={{
            marginTop: '8px',
            textDecoration: 'underline',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--band-1-ink)',
          }}
        >
          다시 시도
        </button>
      </section>
    )
  }

  // 5) no-resume → 온보딩. T-097부터 page 레벨이 /resume로 직행시키므로 보통 도달 안 함(fallback).
  if (!meta.has_resume) {
    return <Onboarding />
  }

  // error(채점 실패)
  if (meta.scoring_status === 'failed') {
    return (
      <section
        data-testid="feed-state-error"
        role="alert"
        style={{
          maxWidth: '430px',
          margin: '0 auto',
          padding: '24px 16px',
          color: 'var(--band-1-ink)',
        }}
      >
        <p style={{ fontWeight: 600 }}>채점에 실패했어요. 다시 시도해주세요.</p>
        <button
          type="button"
          onClick={() => void load()}
          style={{
            marginTop: '8px',
            textDecoration: 'underline',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--band-1-ink)',
          }}
        >
          다시 시도
        </button>
      </section>
    )
  }

  // 6) scoring(분석 중)
  if (meta.scoring_status === 'queued' || meta.scoring_status === 'running') {
    return <ScoringSkeleton label="포도가 공고를 분석하고 있어요" />
  }

  // 3)/8) 보이는 공고 0 → empty(신규 적음) 또는 all-processed(다 처리)
  if (meta.visible_count === 0) {
    if (meta.diff_summary.new_count > 0) {
      return (
        <section
          data-testid="feed-all-processed"
          style={{ maxWidth: '430px', margin: '0 auto', padding: '24px 16px', color: 'var(--ink)' }}
        >
          <PodoMascot size={52} />
          <p style={{ fontWeight: 600 }}>오늘 처리할 공고를 다 봤어요</p>
        </section>
      )
    }
    // 재노출 모드 — "다시 보기" 클릭 시 최근 7일 미처리(+최근 처리분) 공고 피드(T-092 AC-2).
    if (resurface) {
      return (
        <div>
          <p
            data-testid="resurface-banner"
            style={{
              maxWidth: '430px',
              margin: '8px auto 0',
              padding: '0 16px',
              color: 'var(--muted)',
            }}
          >
            최근 7일 미처리 공고를 다시 보여드려요.
          </p>
          <FeedList domain={domain} resurface />
        </div>
      )
    }
    return (
      <section
        data-testid="feed-empty-state"
        style={{ maxWidth: '430px', margin: '0 auto', padding: '24px 16px', color: 'var(--ink)' }}
      >
        <PodoMascot size={52} />
        <p style={{ fontWeight: 600 }}>오늘은 신규가 적어요</p>
        <p style={{ color: 'var(--muted)' }}>최근 7일 미처리 공고를 다시 볼 수 있어요.</p>
        <button
          type="button"
          data-testid="resurface-button"
          onClick={() => setResurface(true)}
          style={{
            marginTop: '12px',
            padding: '8px 16px',
            borderRadius: '12px',
            border: '1px solid var(--line-strong)',
            background: 'var(--surface)',
            color: 'var(--grape-700)',
            cursor: 'pointer',
          }}
        >
          최근 7일 미처리 다시 보기
        </button>
      </section>
    )
  }

  // 4) pending(전 공고 보류) — held만 남음. GreetingCard + FeedList(JobCard가 보류 렌더).
  const allHeld = meta.visible_count > 0 && meta.visible_count === meta.total_pending_count

  // 7) ready (또는 pending)
  return (
    <div>
      <GreetingCard
        newCount={meta.diff_summary.new_count}
        expiringCount={meta.diff_summary.expiring_count}
      />
      {allHeld && (
        <p
          data-testid="feed-pending-banner"
          style={{
            maxWidth: '430px',
            margin: '8px auto 0',
            padding: '0 16px',
            color: 'var(--faint)',
          }}
        >
          포도가 아직 분석하지 못한 공고만 있어요.
        </p>
      )}
      <FeedList domain={domain} />
    </div>
  )
}
