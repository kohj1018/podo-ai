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
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

function hhmm(iso: string): string {
  return new Date(iso).toISOString().slice(11, 16)
}

// 커버리지 투명성 패널 — "전부 수집" 인상 차단(Fail #3). 상시 노출. coverage.* 토큰(§2-3).
export function CoveragePanel() {
  const [cov, setCov] = useState<Coverage | null>(null)

  useEffect(() => {
    let alive = true
    fetch(`${API_BASE}/api/v1/coverage`)
      .then((r) => r.json())
      .then((c: Coverage) => {
        if (alive) setCov(c)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [])

  if (!cov) {
    return (
      <section data-testid="coverage-panel" className="mx-auto max-w-2xl p-3 text-sm">
        수집 현황 불러오는 중…
      </section>
    )
  }

  return (
    <section
      data-testid="coverage-panel"
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
