import { DeadlineRow } from './DeadlineRow'
import type { FeedItem } from './JobCard'

// closing_at(ISO) → D-day까지 남은 일수. null이면 null. (JobCard.daysUntil 동일 파생 — T-090 §3 3번)
function daysUntil(closingAt: string | null | undefined): number | null {
  if (!closingAt) return null
  const ms = new Date(closingAt).getTime() - Date.now()
  return Math.ceil(ms / (1000 * 60 * 60 * 24))
}

// DeadlineSection (AC-1) — 추천 items에서 closing_at ≤7일인 공고를 상위 5개 캡으로 분리 노출.
// 임박 0이면 return null(빈 헤더 금지 — F-028 §9, §메모). fit 점수/배지 없음(회사·직무 + DeadlineRow만).
export function DeadlineSection({ items }: { items: FeedItem[] }) {
  const expiring = items
    .map((item) => ({ item, days: daysUntil(item.posting.closing_at) }))
    .filter((e): e is { item: FeedItem; days: number } => e.days !== null && e.days <= 7)
    .slice(0, 5)

  if (expiring.length === 0) return null

  return (
    <section
      aria-label="마감 임박"
      data-testid="deadline-section"
      style={{
        maxWidth: '430px',
        margin: '0 auto 8px',
        padding: '12px 16px',
        background: 'var(--surface)',
        borderRadius: '16px',
        border: '1px solid var(--line)',
        boxShadow: 'var(--shadow-soft)',
      }}
    >
      <h2
        className="text-sm font-semibold"
        style={{ color: 'var(--band-2-ink)', marginBottom: '8px' }}
      >
        ⏰ 마감 임박
      </h2>
      <ul
        style={{
          listStyle: 'none',
          padding: 0,
          margin: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}
      >
        {expiring.map(({ item, days }) => (
          <li key={item.posting.id} data-testid="deadline-item">
            <span className="text-sm font-medium" style={{ color: 'var(--ink)' }}>
              {item.posting.company} · {item.posting.title}
            </span>
            <DeadlineRow daysLeft={days} />
          </li>
        ))}
      </ul>
    </section>
  )
}
