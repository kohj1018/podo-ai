'use client'

import { useEffect, useState } from 'react'

interface ChannelCoverage {
  name: string
  tier?: string | null
  status: string | null
  last_success_at: string | null
}

interface Coverage {
  channels: ChannelCoverage[]
  uncollected: string[]
  degraded?: boolean
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

// 주요 소스 한글 표시명(없으면 원 slug). 차단/미지원 등은 친근한 footer에서 "그 외 미수집"으로 묶음.
const DISPLAY_NAME: Record<string, string> = {
  toss: '토스',
  daangn: '당근',
  coupang: '쿠팡',
  kakao: '카카오',
  naver: '네이버',
  line: '라인',
  'line-plus': '라인',
  woowahan: '우아한형제들',
  baemin: '배민',
  greeting: '그리팅',
}

function display(name: string): string {
  return DISPLAY_NAME[name] ?? name
}

function hhmm(iso: string): string {
  return new Date(iso).toISOString().slice(11, 16)
}

function isActive(c: ChannelCoverage): boolean {
  return c.status === 'active' || c.status === 'success'
}

// 가장 최근 성공 시각(HH:MM). 없으면 null.
function lastCollected(channels: ChannelCoverage[]): string | null {
  const times = channels
    .map((c) => c.last_success_at)
    .filter((t): t is string => Boolean(t))
    .sort()
  return times.length > 0 ? times[times.length - 1] : null
}

const chip = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '4px',
  padding: '4px 10px',
  borderRadius: '999px',
  fontSize: '12px',
  fontWeight: 600,
} as const

// 커버리지 투명성 footer(DESIGN §7-3, Fail#3) — "지금 수집 중인 채널"을 친근한 chip으로.
// 수집 실패 채널을 알람처럼 나열하지 않고, 활성 채널 + "그 외 채널 미수집"으로 정직하게 압축 노출
// (거짓 완전성 차단은 유지하되 사용자 경험을 해치지 않음).
export function CoveragePanel() {
  const [cov, setCov] = useState<Coverage | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let alive = true
    fetch(`${API_BASE}/api/v1/coverage`, { credentials: 'include' })
      .then((r) => {
        if (!r.ok) throw new Error(`coverage ${r.status}`)
        return r.json()
      })
      .then((c: Coverage) => {
        if (alive) setCov(c)
      })
      .catch(() => {
        if (alive) setError(true)
      })
    return () => {
      alive = false
    }
  }, [])

  if (error) {
    return (
      <section
        data-testid="coverage-panel"
        data-state="error"
        className="mx-auto max-w-[430px] p-3 text-sm"
        style={{ color: 'var(--faint)' }}
      >
        수집 현황을 잠시 불러오지 못했어요.
      </section>
    )
  }

  if (!cov) {
    return (
      <section
        data-testid="coverage-panel"
        data-state="loading"
        aria-busy="true"
        aria-label="수집 현황 불러오는 중"
        className="mx-auto max-w-[430px] rounded-2xl border p-4"
        style={{ borderColor: 'var(--line)' }}
      >
        <div
          className="shimmer"
          style={{ height: '14px', borderRadius: '8px', width: '40%', marginBottom: '10px' }}
        />
        <div className="shimmer" style={{ height: '24px', borderRadius: '12px', width: '70%' }} />
      </section>
    )
  }

  const active = cov.channels.filter(isActive)
  const hasUncollected = active.length < cov.channels.length || cov.uncollected.length > 0
  const last = lastCollected(cov.channels)

  return (
    <section
      data-testid="coverage-panel"
      data-state={cov.degraded ? 'degraded' : 'ready'}
      aria-label="수집 현황"
      className="mx-auto max-w-[430px] rounded-2xl p-4 text-sm"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--line)',
        boxShadow: 'var(--shadow-soft)',
      }}
    >
      <p style={{ fontWeight: 700, color: 'var(--ink)', margin: '0 0 10px' }}>
        🍇 지금 수집 중인 채널
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {active.map((c) => (
          <span
            key={c.name}
            data-testid="coverage-chip-active"
            style={{ ...chip, background: 'var(--coverage-on-bg)', color: 'var(--band-5-ink)' }}
          >
            {display(c.name)} ✓
          </span>
        ))}
        {hasUncollected ? (
          <span
            data-testid="coverage-uncollected"
            style={{ ...chip, background: 'var(--grape-100)', color: 'var(--muted)' }}
          >
            그 외 채널 미수집
          </span>
        ) : null}
      </div>
      <p style={{ color: 'var(--faint)', margin: '10px 0 0', fontSize: '12px' }}>
        {last ? `마지막 성공 ${hhmm(last)} · ` : ''}미수집 채널은 추천에 포함되지 않아요.
      </p>
    </section>
  )
}
