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
  evidence: unknown // ranking_runs.result — opaque(T-029가 펼침)
}

// JobCard (DESIGN §7-2) — source/role/co/meta + FitScoreRing + PassBand(적합도). 합격확률/% 금지.
export function JobCard({ item }: { item: FeedItem }) {
  const { posting, fit_level } = item
  return (
    <article
      data-testid="job-card"
      className="flex items-center gap-4 rounded-2xl border p-4"
      style={{ color: 'var(--ink)' }}
    >
      <FitScoreRing level={fit_level} />
      <div className="flex-1">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wide">
          <span>{posting.source}</span>
          {posting.role_family ? <span>· {posting.role_family}</span> : null}
        </div>
        <h2 className="font-semibold">{posting.title}</h2>
        <p className="text-sm">{posting.company}</p>
        <div className="mt-2">
          <PassBand level={fit_level} />
        </div>
      </div>
    </article>
  )
}
