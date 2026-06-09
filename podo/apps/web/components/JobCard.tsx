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
      style={{
        color: 'var(--ink)',
        background: 'var(--surface)',
        border: '1px solid var(--line)',
        borderRadius: '24px',
        padding: '18px',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      {/* 헤더: 회사·직무(좌) + fit 링·강추 배지(우, mockup §추천). fit 링은 1~5 정직 표기(가짜 % 금지). */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide">
            <span>{posting.source}</span>
            {posting.role_family ? <span>· {posting.role_family}</span> : null}
            {/* crawler(단일 writer)가 쓰는 실제 값은 한글: "신규"/"유지"/"마감". */}
            {posting.diff_status === '신규' ? (
              <span data-testid="diff-new" style={{ color: 'var(--band-5-ink)' }}>
                · NEW
              </span>
            ) : null}
            {posting.diff_status === '마감' ? (
              <span data-testid="diff-closed" style={{ color: 'var(--band-2-ink)' }}>
                · 마감
              </span>
            ) : null}
          </div>
          <h2 className="font-semibold">{posting.title}</h2>
          <p className="text-sm">{posting.company}</p>
        </div>

        {held ? null : (
          <div className="flex shrink-0 flex-col items-center gap-1">
            <FitScoreRing level={fit_level} />
            {fit_level !== null && fit_level >= 5 ? (
              <span
                data-testid="podo-pick"
                style={{
                  padding: '2px 8px',
                  borderRadius: '999px',
                  fontSize: '11px',
                  fontWeight: 700,
                  background: 'var(--grape-100)',
                  color: 'var(--grape-700)',
                  whiteSpace: 'nowrap',
                }}
              >
                podo 강추!
              </span>
            ) : null}
          </div>
        )}
      </div>

      {held ? (
        <div className="mt-2">
          <PendingState url={posting.url} />
        </div>
      ) : (
        <div className="mt-3">
          <PassBand level={fit_level} />
          {days !== null ? <DeadlineRow daysLeft={days} /> : null}
          <EvidenceBlock evidence={evidence} jobId={posting.id} />
          <JobCardActions
            jobId={posting.id}
            url={posting.url}
            onProcessed={onProcessed}
            onRestore={onRestore}
          />
        </div>
      )}
    </article>
  )
}
