interface EvidenceRow {
  quote: string
  requirement: string
  matched: boolean
}

// result(opaque)에서 해당 공고의 매핑 행을 *표시 전용*으로 추출(비즈니스 분기 0, §7-4).
// 구조 결손은 방어적으로 빈 배열 → "근거 없음".
function extractRows(evidence: unknown, jobId: number): EvidenceRow[] {
  if (typeof evidence !== 'object' || evidence === null) return []
  const mt = (evidence as Record<string, unknown>).matching_tables
  if (typeof mt !== 'object' || mt === null) return []
  const table = (mt as Record<string, unknown>)[String(jobId)]
  if (typeof table !== 'object' || table === null) return []
  const rows = (table as Record<string, unknown>).rows
  if (!Array.isArray(rows)) return []

  const out: EvidenceRow[] = []
  for (const raw of rows) {
    if (typeof raw !== 'object' || raw === null) continue
    const r = raw as Record<string, unknown>
    const quotes = Array.isArray(r.evidence_quotes) ? r.evidence_quotes : []
    const quote = quotes.length > 0 ? String(quotes[0]) : ''
    const requirement = typeof r.requirement_text === 'string' ? r.requirement_text : ''
    const matched = r.match_level === 'direct' || r.match_level === 'adjacent'
    if (quote || requirement) out.push({ quote, requirement, matched })
  }
  return out
}

// EvidenceBlock (DESIGN §7-2) — JD 인용 + 이력서↔JD 매핑(✓/△). 색만 의존 금지: ✓/△ + 라벨.
export function EvidenceBlock({
  evidence,
  jobId,
}: {
  evidence: unknown
  jobId: number
}) {
  const rows = extractRows(evidence, jobId)
  if (rows.length === 0) {
    return (
      <p data-testid="evidence-block" className="mt-2 text-sm" style={{ color: 'var(--faint)' }}>
        근거 없음 — 보류
      </p>
    )
  }
  return (
    <div data-testid="evidence-block" className="mt-2 flex flex-col gap-2 text-sm">
      {rows.map((r) => (
        <div key={`${r.requirement}-${r.quote}`} className="border-l-2 pl-2">
          {r.quote ? <blockquote>“{r.quote}”</blockquote> : null}
          <span>
            {r.matched ? '✓' : '△'} {r.requirement}
          </span>
        </div>
      ))}
    </div>
  )
}
