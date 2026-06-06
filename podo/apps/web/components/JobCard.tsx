'use client'

import { useState } from 'react'
import { EvidenceBlock } from './EvidenceBlock'
import { FitScoreRing } from './FitScoreRing'
import { PassBand } from './PassBand'

export interface Posting {
  id: number
  source: string
  company: string
  title: string
  role_family?: string | null
}

export interface FeedItem {
  posting: Posting
  fit_level: number | null
  rank_position: number
  status: string
  evidence: unknown // ranking_runs.result — opaque(EvidenceBlock가 표시 전용 해석)
}

// JobCard (DESIGN §7-2) — source/role/co + FitScoreRing + PassBand(적합도) + 근거 펼침.
// held(LLM 보류)는 가짜 점수/배지 대신 보류 상태(Charter thesis). 합격확률/% 금지.
export function JobCard({ item }: { item: FeedItem }) {
  const { posting, fit_level, status, evidence } = item
  const held = status === 'held'
  const [open, setOpen] = useState(false)

  return (
    <article
      data-testid="job-card"
      className="flex items-start gap-4 rounded-2xl border p-4"
      style={{ color: 'var(--ink)' }}
    >
      {held ? (
        <div
          data-testid="held-ring"
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border text-sm"
          style={{ color: 'var(--faint)' }}
        >
          보류
        </div>
      ) : (
        <FitScoreRing level={fit_level} />
      )}

      <div className="flex-1">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wide">
          <span>{posting.source}</span>
          {posting.role_family ? <span>· {posting.role_family}</span> : null}
        </div>
        <h2 className="font-semibold">{posting.title}</h2>
        <p className="text-sm">{posting.company}</p>

        <div className="mt-2">
          {held ? (
            <span
              data-testid="held-badge"
              className="text-sm font-medium"
              style={{ color: 'var(--faint)' }}
            >
              ⏳ 점수 보류 — 재시도 예정
            </span>
          ) : (
            <PassBand level={fit_level} />
          )}
        </div>

        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="mt-2 text-sm underline"
        >
          {open ? '근거 접기' : '근거 보기'}
        </button>
        {open ? <EvidenceBlock evidence={evidence} jobId={posting.id} /> : null}
      </div>
    </article>
  )
}
