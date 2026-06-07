'use client'

import { DeadlineRow } from './DeadlineRow'
import { EvidenceBlock } from './EvidenceBlock'
import { FitScoreRing } from './FitScoreRing'
import { JobCardActions } from './JobCardActions'
import { PassBand } from './PassBand'
import { PendingState } from './PendingState'

export interface Posting {
  id: number
  source: string
  company: string
  title: string
  role_family?: string | null
  url?: string
  closing_at?: string | null
  diff_status?: string | null
}

export interface FeedItem {
  posting: Posting
  fit_level: number | null
  rank_position: number
  status: string
  evidence: unknown // ranking_runs.result — opaque(EvidenceBlock가 표시 전용 해석)
}

// closing_at(ISO) → D-day. null이면 null(마감 정보 없음).
function daysUntil(closingAt: string | null | undefined): number | null {
  if (!closingAt) return null
  const ms = new Date(closingAt).getTime() - Date.now()
  return Math.ceil(ms / (1000 * 60 * 60 * 24))
}

// JobCard (DESIGN §7-2) — source/role/co + FitScoreRing + PassBand(적합도) + 마감 + 신규 표식 + 근거 펼침.
// held(LLM 보류)는 가짜 점수/배지 대신 PendingState(Charter thesis). 합격확률/% 금지.
// onProcessed/onRestore: 지원/스킵 처리완료 정리·롤백(F-019, JobCardActions 경유).
export function JobCard({
  item,
  onProcessed,
  onRestore,
}: {
  item: FeedItem
  onProcessed?: (jobId: number) => void
  onRestore?: (jobId: number) => void
}) {
  const { posting, fit_level, status, evidence } = item
  const held = status === 'held'
  const days = daysUntil(posting.closing_at)

  return (
    <article
      data-testid="job-card"
      aria-label={`${posting.company} ${posting.title}`}
      className="flex items-start gap-4 rounded-2xl border p-4"
      style={{ color: 'var(--ink)' }}
    >
      {held ? null : <FitScoreRing level={fit_level} />}

      <div className="flex-1">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wide">
          <span>{posting.source}</span>
          {posting.role_family ? <span>· {posting.role_family}</span> : null}
          {posting.diff_status === 'new' ? (
            <span data-testid="diff-new" style={{ color: 'var(--band-5-ink)' }}>
              · NEW
            </span>
          ) : null}
          {posting.diff_status === 'expiring' ? (
            <span data-testid="diff-expiring" style={{ color: 'var(--band-2-ink)' }}>
              · 마감 임박
            </span>
          ) : null}
        </div>
        <h2 className="font-semibold">{posting.title}</h2>
        <p className="text-sm">{posting.company}</p>

        {held ? (
          <div className="mt-2">
            <PendingState url={posting.url} />
          </div>
        ) : (
          <>
            <div className="mt-2">
              <PassBand level={fit_level} />
            </div>
            {days !== null ? <DeadlineRow daysLeft={days} /> : null}
            <EvidenceBlock evidence={evidence} jobId={posting.id} />
            <JobCardActions
              jobId={posting.id}
              url={posting.url}
              onProcessed={onProcessed}
              onRestore={onRestore}
            />
          </>
        )}
      </div>
    </article>
  )
}
