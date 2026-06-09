'use client'

import { useEffect, useState } from 'react'

interface ActivityItem {
  id: number
  job_posting_id: number
  action: string
  job_posting: { company: string; title: string; url: string | null }
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

const EMPTY_COPY: Record<string, string> = {
  favorite: '아직 즐겨찾기한 공고가 없어요. 마음에 드는 공고를 별표로 모아보세요.',
  applied: '아직 지원 기록이 없어요. 지원한 공고가 여기에 모여요.',
}

// 활동 뷰(T-094) — 즐겨찾기/지원기록 목록. GET /api/v1/applications?filter= 소비(순수 프론트).
// 빈/로딩/에러를 일급으로 노출(빈 목록으로 삼키지 않음 — REV-M2-UI-001).
export function ActivityList({ filter }: { filter: 'favorite' | 'applied' }) {
  const [items, setItems] = useState<ActivityItem[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let alive = true
    setItems(null)
    setError(false)
    fetch(`${API_BASE}/api/v1/applications?filter=${filter}`, { credentials: 'include' })
      .then((r) => {
        if (!r.ok) throw new Error(`applications ${r.status}`)
        return r.json()
      })
      .then((body: { data: ActivityItem[] }) => {
        if (alive) setItems(body.data)
      })
      .catch(() => {
        if (alive) setError(true)
      })
    return () => {
      alive = false
    }
  }, [filter])

  if (error) {
    return (
      <section
        data-testid="activity-error"
        role="alert"
        className="text-sm"
        style={{ color: 'var(--band-1-ink)' }}
      >
        ⚠ 목록을 불러오지 못했어요. 잠시 후 다시 시도해주세요.
      </section>
    )
  }

  if (!items) {
    return (
      <section
        data-testid="activity-loading"
        aria-busy="true"
        style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}
      >
        <div className="shimmer" style={{ height: '56px', borderRadius: '16px' }} />
        <div className="shimmer" style={{ height: '56px', borderRadius: '16px' }} />
      </section>
    )
  }

  if (items.length === 0) {
    return (
      <section data-testid="activity-empty" className="text-sm" style={{ color: 'var(--muted)' }}>
        {EMPTY_COPY[filter]}
      </section>
    )
  }

  return (
    <ul
      data-testid="activity-list"
      style={{
        listStyle: 'none',
        padding: 0,
        margin: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      {items.map((it) => (
        <li
          key={it.id}
          data-testid="activity-item"
          style={{
            padding: '14px 16px',
            borderRadius: '16px',
            border: '1px solid var(--line)',
            background: 'var(--surface)',
            boxShadow: 'var(--shadow-soft)',
          }}
        >
          <p style={{ fontWeight: 600, color: 'var(--ink)' }}>{it.job_posting.title}</p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>
            {it.job_posting.company}
          </p>
          {it.job_posting.url ? (
            <a
              href={it.job_posting.url}
              target="_blank"
              rel="noreferrer"
              className="text-sm"
              style={{ color: 'var(--grape-700)' }}
            >
              공고 보기
            </a>
          ) : null}
        </li>
      ))}
    </ul>
  )
}
