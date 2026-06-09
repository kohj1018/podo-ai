'use client'

import { useState } from 'react'

interface EvidenceRow {
  requirement: string
  matched: boolean
}

// result(opaque)에서 해당 공고의 매핑 행을 *표시 전용*으로 추출(비즈니스 분기 0, §7-4).
// 이력서 원문(evidence_quotes)은 표시하지 않는다 — JD 요구사항(requirement_text) + 충족 여부만(사용자 결정·PII 보호).
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
    const requirement = typeof r.requirement_text === 'string' ? r.requirement_text : ''
    const matched = r.match_level === 'direct' || r.match_level === 'adjacent'
    if (requirement) out.push({ requirement, matched })
  }
  return out
}

// EvidenceBlock (DESIGN §7-2) — 근거 펼침 토글(키보드 접근) + JD 요구사항별 충족(✓)/부족(△) 정리.
// 이력서 원문은 인용하지 않는다 — JD 문구 기준으로만(색만 의존 금지: ✓/△ + 라벨).
export function EvidenceBlock({
  evidence,
  jobId,
}: {
  evidence: unknown
  jobId: number
}) {
  const [open, setOpen] = useState(false)
  const panelId = `evidence-${jobId}`
  const rows = extractRows(evidence, jobId)

  return (
    <div>
      <button
        type="button"
        data-testid="evidence-toggle"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        className="mt-2 text-sm underline"
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink)' }}
      >
        {open ? '근거 접기' : '근거 보기'}
      </button>
      {open ? (
        <div id={panelId} data-testid="evidence-block" className="mt-2 flex flex-col gap-2 text-sm">
          <p style={{ color: 'var(--muted)', fontWeight: 600, margin: 0 }}>🔍 podo가 본 근거</p>
          {rows.length === 0 ? (
            <p style={{ color: 'var(--faint)' }}>근거 없음 — 보류</p>
          ) : (
            rows.map((r) => (
              <div
                key={`${r.requirement}-${r.matched}`}
                data-testid="evidence-row"
                className="border-l-2 pl-2"
                style={{ borderColor: r.matched ? 'var(--band-5-fill)' : 'var(--band-2-fill)' }}
              >
                <span style={{ color: r.matched ? 'var(--band-5-ink)' : 'var(--band-2-ink)' }}>
                  {r.matched ? '✓ 충족' : '△ 부족'}
                </span>
                <span style={{ color: 'var(--ink)' }}> · {r.requirement}</span>
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  )
}
