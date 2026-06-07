'use client'

import { useEffect, useState } from 'react'

interface ChannelCoverage {
  name: string
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

// 커버리지 투명성 패널 — "전부 수집" 인상 차단(Fail #3 / Charter G3). 상시 노출.
// 실패를 삼키지 않고 노출(REV-M2-UI-001) — 투명성 패널이 거짓 완전성을 보이면 존재 이유와 충돌.
export function CoveragePanel() {
  const [cov, setCov] = useState<Coverage | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let alive = true
    fetch(`${API_BASE}/api/v1/coverage`)
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
        className="mx-auto max-w-2xl rounded-xl border p-3 text-sm"
        style={{ color: 'var(--band-1-ink)', borderColor: 'var(--band-1-ink)' }}
      >
        ⚠ 수집 현황을 불러오지 못했습니다
      </section>
    )
  }

  if (!cov) {
    return (
      <section
        data-testid="coverage-panel"
        data-state="loading"
        className="mx-auto max-w-2xl p-3 text-sm"
      >
        수집 현황 불러오는 중…
      </section>
    )
  }

  // degraded(수집 실패/미수집) → danger + role=alert. "전부 수집" 거짓 인상 차단(Fail #3, AC-2).
  if (cov.degraded) {
    return (
      <section
        data-testid="coverage-panel"
        data-state="degraded"
        role="alert"
        className="mx-auto max-w-2xl rounded-xl border p-3 text-sm"
        style={{ color: 'var(--band-1-ink)', borderColor: 'var(--band-1-ink)' }}
      >
        <h2 className="font-medium">수집 실패</h2>
        <p>일부 공고가 누락될 수 있어요.</p>
        <ul>
          {cov.channels.map((c) => (
            <li key={c.name}>
              {c.name}: {c.status ?? '미수집'}
            </li>
          ))}
        </ul>
      </section>
    )
  }

  return (
    <section
      data-testid="coverage-panel"
      data-state="ready"
      aria-label="수집 현황"
      className="mx-auto max-w-2xl rounded-xl border p-3 text-sm"
      style={{
        backgroundColor: 'var(--coverage-on-bg)',
        borderColor: 'var(--coverage-on-border)',
        color: 'var(--band-5-ink)',
      }}
    >
      <h2 className="font-medium">수집 현황</h2>
      <ul>
        {cov.channels.map((c) => (
          <li key={c.name}>
            {c.name}: {c.status ?? '미수집'}
            {c.last_success_at ? ` · 마지막 성공 ${hhmm(c.last_success_at)}` : ''}
          </li>
        ))}
      </ul>
      {cov.uncollected.length > 0 ? (
        <p style={{ color: 'var(--faint)' }}>미수집: {cov.uncollected.join(', ')}</p>
      ) : null}
    </section>
  )
}
