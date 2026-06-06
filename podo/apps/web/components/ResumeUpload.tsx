'use client'

import { useRef, useState } from 'react'
import { MaskingPreview } from './MaskingPreview'

interface EvidenceSummary {
  skills: number
  experiences: number
}

interface ResumeApiResponse {
  data: {
    resume_id: number
    masked: boolean
    masked_preview: string
    placeholders: number
    evidence_summary: EvidenceSummary
  }
}

interface PreviewState {
  maskedText: string
  evidenceSummary: EvidenceSummary
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

// /resume 업로드 영역 — FeedList 패턴(API_BASE 환경변수) 차용.
// 파일 drag/drop(.txt/.md) + textarea paste 양쪽 지원.
// 업로드 후 T-034 응답(masked_preview + evidence_summary)을 MaskingPreview에 전달.
export function ResumeUpload() {
  const [pasteText, setPasteText] = useState('')
  const [preview, setPreview] = useState<PreviewState | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleUpload() {
    const file = fileInputRef.current?.files?.[0]
    const hasInput = file || pasteText.trim()
    if (!hasInput) return

    setUploading(true)
    try {
      let res: Response
      if (file) {
        const form = new FormData()
        form.append('file', file)
        res = await fetch(`${API_BASE}/api/v1/resumes`, { method: 'POST', body: form })
      } else {
        res = await fetch(`${API_BASE}/api/v1/resumes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: pasteText }),
        })
      }

      if (!res.ok) return
      const body = (await res.json()) as ResumeApiResponse
      setPreview({
        maskedText: body.data.masked_preview,
        evidenceSummary: body.data.evidence_summary,
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      {/* 파일 입력 — .txt/.md only */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.md"
        style={{ display: 'block', marginBottom: '8px' }}
      />

      {/* paste 텍스트 영역 */}
      <textarea
        value={pasteText}
        onChange={(e) => setPasteText(e.target.value)}
        placeholder="이력서를 붙여넣거나 파일을 선택하세요"
        rows={6}
        style={{ display: 'block', width: '100%', marginBottom: '8px' }}
      />

      <button type="button" onClick={() => void handleUpload()} disabled={uploading}>
        업로드
      </button>

      {/* 마스킹 preview — 응답 수신 후 표시 */}
      {preview && (
        <MaskingPreview maskedText={preview.maskedText} evidenceSummary={preview.evidenceSummary} />
      )}

      {/* "이 이력서로 분석 시작" — preview 수신 전 disabled (T-039가 클릭 핸들러 연결) */}
      {/* Button.primary — DESIGN §2-3 button.primary.bg=color.accent(grape-600 CSS 변수).
          brand.gradient는 §2-4 FENCED(fit 링/로고/인사 strip만) — 버튼 사용 금지. */}
      <button
        type="button"
        data-testid="start-analysis-btn"
        disabled={!preview}
        style={{
          marginTop: '12px',
          background: 'var(--grape-600)',
          color: 'var(--surface)',
          opacity: preview ? 1 : 0.45,
          cursor: preview ? 'pointer' : 'not-allowed',
        }}
      >
        이 이력서로 분석 시작
      </button>
    </div>
  )
}
