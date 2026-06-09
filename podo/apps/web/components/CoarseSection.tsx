'use client'

import { useEffect, useState } from 'react'

// T-065 coarse 섹션 — 후보 밖(deep 분석 전) 공고를 유사도순으로 노출.
// **fit 배지(FitScoreRing/PassBand) 없음** — 거짓 점수 금지(Guardrail 1, ADR-108 D3).
// JobCard는 본 task write_set 밖이라 섹션 wrapper가 배지 없는 최소 행으로 직접 렌더한다.
interface CoarsePosting {
  id: number
  company?: string
  title?: string
  url?: string
}

interface CoarseItem {
  posting: CoarsePosting
  similarity_rank: number
}

interface CoarsePage {
  items: CoarseItem[]
  nextCursor: number | null
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

export function CoarseSection() {
  const [page, setPage] = useState<CoarsePage | null>(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let alive = true
    // deep 피드와 별도 cursor — coarse 전용 쿼리(ADR-108 D3).
    fetch(`${API_BASE}/api/v1/feed?section=coarse`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { items: [], nextCursor: null }))
      .then((p: CoarsePage) => {
        if (alive) setPage(p)
      })
      .catch(() => {
        if (alive) setPage({ items: [], nextCursor: null })
      })
    return () => {
      alive = false
    }
  }, [])

  // 빈 coarse는 노출하지 않는다(섹션 자체 숨김).
  if (!page || page.items.length === 0) {
    return null
  }

  // 최하단 *접힌* 보조 진입(피로 최소 IA §2-A-1 ⑥). 기본 접힘 + 펼침 토글. 배지 0(ADR-108 D3).
  return (
    <section
      data-testid="coarse-section"
      aria-label="아직 깊이 안 본 공고"
      className="mx-auto max-w-[430px] rounded-xl border p-3 text-sm"
      style={{ borderColor: 'var(--faint)', color: 'var(--band-5-ink)' }}
    >
      <button
        type="button"
        data-testid="coarse-toggle"
        aria-expanded={expanded}
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-left font-medium"
        style={{
          background: 'none',
          border: 'none',
          padding: 0,
          color: 'inherit',
          cursor: 'pointer',
        }}
      >
        <span>아직 깊이 안 본 공고 {page.items.length}개 · 원하면 분석할게요</span>
        <span aria-hidden="true" style={{ color: 'var(--faint)' }}>
          {expanded ? '접기 ▲' : '펼치기 ▼'}
        </span>
      </button>
      {expanded ? (
        <ul className="mt-2">
          {page.items.map((it) => (
            <li key={it.posting?.id} data-testid="coarse-item" className="py-1">
              {it.posting?.company ?? ''} · {it.posting?.title ?? ''}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
