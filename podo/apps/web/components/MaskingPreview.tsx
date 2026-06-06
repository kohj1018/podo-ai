'use client'

interface EvidenceSummary {
  skills: number
  experiences: number
}

interface MaskingPreviewProps {
  maskedText: string
  evidenceSummary: EvidenceSummary
}

// 플레이스홀더 패턴: [MASKED_XXX] — PII 제거 확인용 강조
const PLACEHOLDER_RE = /(\[MASKED_[A-Z_]+\])/g

// 마스킹본 텍스트를 렌더하고 플레이스홀더를 토큰 색으로 강조.
// 색은 DESIGN §2 토큰(var(--...))만 참조 — raw hex 금지.
export function MaskingPreview({ maskedText, evidenceSummary }: MaskingPreviewProps) {
  const parts = maskedText.split(PLACEHOLDER_RE)
  // 안정 key: split 파트의 누적 시작 오프셋 — 동일 플레이스홀더 반복 시에도 고유(array index key 금지).
  let offset = 0
  const segments = parts.map((part) => {
    const seg = { part, key: `${offset}-${part}`, masked: PLACEHOLDER_RE.test(part) }
    offset += part.length
    return seg
  })

  return (
    <div data-testid="masking-preview" style={{ color: 'var(--ink)' }}>
      <p data-testid="evidence-summary" style={{ color: 'var(--faint)', fontSize: '13px' }}>
        스킬 {evidenceSummary.skills}개, 경력 {evidenceSummary.experiences}건 인식
      </p>
      <pre
        style={{
          whiteSpace: 'pre-wrap',
          fontFamily: 'inherit',
          marginTop: '8px',
        }}
      >
        {segments.map((seg) =>
          seg.masked ? (
            // 플레이스홀더 강조 — band-3-ink(중간 톤 경고 색) 토큰만 사용
            <mark
              key={seg.key}
              data-testid="placeholder-highlight"
              style={{
                background: 'var(--band-3-fill)',
                color: 'var(--band-3-ink)',
                borderRadius: '3px',
                padding: '0 2px',
              }}
            >
              {seg.part}
            </mark>
          ) : (
            <span key={seg.key}>{seg.part}</span>
          ),
        )}
      </pre>
    </div>
  )
}
