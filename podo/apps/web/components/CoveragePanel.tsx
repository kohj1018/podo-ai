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

function hhmm(iso: string): string {
  return new Date(iso).toISOString().slice(11, 16)
}

// status taxonomy → 사용자 표시 라벨. login-required/no-korea-jobs/unsupported는 미수집을
// *사유와 함께* 정직하게 노출(거짓 완전성 차단, Fail #3).
function statusLabel(status: string | null): string {
  switch (status) {
    case 'active':
    case 'success': // 레거시 crawl_runs 값 호환
      return '수집 중'
    case 'blocked':
      return '차단'
    case 'captcha':
      return '캡차 차단'
    case 'login-required':
      return '로그인 필요(미수집)'
    case 'no-korea-jobs':
      return '한국 채용 없음'
    case 'unsupported':
      return '미지원'
    case 'failed': // 레거시
      return '수집 실패'
    case null:
      return '미수집'
    default:
      return status
  }
}

function activeCount(channels: ChannelCoverage[]): number {
  return channels.filter((c) => c.status === 'active' || c.status === 'success').length
}

// 가장 최근 성공 시각(HH:MM). 없으면 null.
function lastCollected(channels: ChannelCoverage[]): string | null {
  const times = channels
    .map((c) => c.last_success_at)
    .filter((t): t is string => Boolean(t))
    .sort()
  return times.length > 0 ? times[times.length - 1] : null
}

// 커버리지 투명성 패널 — "전부 수집" 인상 차단(Fail #3 / Charter G3). 상시 노출.
// 기본은 compact 1줄 strip(피로 최소 IA §2-A-1) + 펼침 토글로 채널 상세. degraded면 자동 펼침 + 경고(role=alert).
export function CoveragePanel() {
  const [cov, setCov] = useState<Coverage | null>(null)
  const [error, setError] = useState(false)
  const [expanded, setExpanded] = useState(false)

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
        className="mx-auto max-w-[430px] rounded-xl border p-3 text-sm"
        style={{ color: 'var(--band-1-ink)', borderColor: 'var(--band-1-ink)' }}
      >
        ⚠ 수집 현황을 불러오지 못했습니다
      </section>
    )
  }

  if (!cov) {
    // compact strip 로딩 skeleton(T-098) — shimmer 1줄. reduced-motion은 globals.css에서 정적 분기.
    return (
      <section
        data-testid="coverage-panel"
        data-state="loading"
        aria-busy="true"
        aria-label="수집 현황 불러오는 중"
        className="mx-auto max-w-[430px] rounded-xl border p-3"
      >
        <div className="shimmer" style={{ height: '14px', borderRadius: '8px', width: '70%' }} />
      </section>
    )
  }

  const total = cov.channels.length
  const summary =
    total > 0 ? `${activeCount(cov.channels)}/${total} 소스 수집 중` : '등록된 소스 없음'

  // 소스별 status 리스트(active=수집 중·시각, 그 외=사유 라벨). 펼침 시 노출.
  const detail = (
    <div data-testid="coverage-detail">
      <ul>
        {cov.channels.map((c) => (
          <li key={c.name}>
            {c.name}
            {c.tier ? ` (T${c.tier})` : ''}: {statusLabel(c.status)}
            {c.last_success_at ? ` · 마지막 성공 ${hhmm(c.last_success_at)}` : ''}
          </li>
        ))}
      </ul>
      {cov.uncollected.length > 0 ? (
        <p style={{ color: 'var(--faint)' }}>미수집: {cov.uncollected.join(', ')}</p>
      ) : null}
    </div>
  )

  // degraded(수집 실패/미수집/차단/로그인 등) → danger + role=alert + 자동 펼침. "전부 수집" 거짓 인상 차단.
  if (cov.degraded) {
    return (
      <section
        data-testid="coverage-panel"
        data-state="degraded"
        role="alert"
        className="mx-auto max-w-[430px] rounded-xl border p-3 text-sm"
        style={{ color: 'var(--band-1-ink)', borderColor: 'var(--band-1-ink)' }}
      >
        <h2 className="font-medium">수집 실패</h2>
        <p>{summary} · 일부 공고가 누락될 수 있어요.</p>
        {detail}
      </section>
    )
  }

  // ready — compact 1줄 strip + 펼침 토글. region(aria-label) 유지.
  const last = lastCollected(cov.channels)
  return (
    <section
      data-testid="coverage-panel"
      data-state="ready"
      aria-label="수집 현황"
      className="mx-auto max-w-[430px] rounded-xl border p-3 text-sm"
      style={{
        backgroundColor: 'var(--coverage-on-bg)',
        borderColor: 'var(--coverage-on-border)',
        color: 'var(--band-5-ink)',
      }}
    >
      <button
        type="button"
        data-testid="coverage-toggle"
        aria-expanded={expanded}
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-left"
        style={{
          background: 'none',
          border: 'none',
          padding: 0,
          color: 'inherit',
          cursor: 'pointer',
        }}
      >
        <span>
          📡 {summary}
          {last ? ` · 마지막 ${hhmm(last)}` : ''}
        </span>
        <span aria-hidden="true" style={{ color: 'var(--faint)' }}>
          {expanded ? '▲' : '▼'}
        </span>
      </button>
      {expanded ? <div className="mt-2">{detail}</div> : null}
    </section>
  )
}
