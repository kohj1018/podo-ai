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
  resumeId: number
}

// 허용 확장자 목록
const ALLOWED_EXTENSIONS = ['.txt', '.md']
// 클라이언트 사이드 파일 크기 상한: 100KB
const MAX_FILE_SIZE = 100 * 1024

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

// /resume 업로드 영역 — FeedList 패턴(API_BASE 환경변수) 차용.
// 파일 drag/drop(.txt/.md) + textarea paste 양쪽 지원.
// 업로드 후 T-034 응답(masked_preview + evidence_summary)을 MaskingPreview에 전달.
// T-041: 비허용 포맷 안내 + 100KB 초과 client pre-check + 로딩 skeleton + error toast.
// T-039: "분석 시작" onClick — score 트리거 후 feed 이동(onNavigateFeed). 주입 없으면 no-op.
export function ResumeUpload({ onNavigateFeed }: { onNavigateFeed?: (path: string) => void } = {}) {
  const [pasteText, setPasteText] = useState('')
  const [preview, setPreview] = useState<PreviewState | null>(null)
  const [uploading, setUploading] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 파일 선택 시 클라이언트 사이드 포맷/크기 검증
  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) {
      setFileError(null)
      return
    }

    const ext = `.${file.name.split('.').pop()?.toLowerCase()}`
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setFileError('현재 .txt / .md 파일 또는 텍스트 붙여넣기만 지원합니다.')
      // 파일 선택 초기화 — 업로드 전송 차단
      e.target.value = ''
      return
    }

    if (file.size > MAX_FILE_SIZE) {
      setFileError('파일이 너무 큽니다(최대 100KB).')
      e.target.value = ''
      return
    }

    setFileError(null)
  }

  async function handleUpload() {
    const file = fileInputRef.current?.files?.[0]
    const hasInput = file || pasteText.trim()
    if (!hasInput) return

    setUploadError(false)
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

      if (!res.ok) {
        setUploadError(true)
        return
      }
      const body = (await res.json()) as ResumeApiResponse
      setPreview({
        maskedText: body.data.masked_preview,
        evidenceSummary: body.data.evidence_summary,
        resumeId: body.data.resume_id,
      })
    } catch {
      setUploadError(true)
    } finally {
      setUploading(false)
    }
  }

  // T-039: score 트리거 → localStorage에 resume_id 저장 → feed 이동.
  // 해석 확정(§8): POST /api/v1/resumes/:id/score (T-037 확정 트리거).
  // resume_id 전달: localStorage('podo_active_resume_id') — 단일 사용자 M3 단순 옵션.
  async function handleStartAnalysis() {
    if (!preview) return
    const { resumeId } = preview
    await fetch(`${API_BASE}/api/v1/resumes/${resumeId}/score`, { method: 'POST' })
    localStorage.setItem('podo_active_resume_id', String(resumeId))
    // 실앱 기본 navigation: feed(/)로 이동(채점 후 fresh load). 테스트는 onNavigateFeed 주입으로 override.
    // useRouter 대신 window.location — top-level hook이 없어 router context 없는 다른 spec을 깨지 않음.
    if (onNavigateFeed) onNavigateFeed('/')
    else window.location.assign('/')
  }

  return (
    <div>
      {/* 파일 입력 — .txt/.md only. label 연결(a11y — DSN-M3-001 회수). */}
      <label htmlFor="resume-file-input" style={{ display: 'block', marginBottom: '4px' }}>
        이력서 파일 (.txt / .md)
      </label>
      <input
        id="resume-file-input"
        ref={fileInputRef}
        data-testid="file-input"
        type="file"
        accept=".txt,.md"
        aria-label="이력서 파일 업로드"
        onChange={handleFileChange}
        style={{ display: 'block', marginBottom: '8px' }}
      />

      {/* 포맷/크기 안내 메시지 — AC-1 */}
      {fileError && (
        <p data-testid="format-error" style={{ color: 'var(--band-1-ink)', margin: '0 0 8px' }}>
          {fileError}
        </p>
      )}

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

      {/* 에러 toast — 업로드 실패 */}
      {uploadError && (
        <p data-testid="upload-error" style={{ color: 'var(--band-1-ink)', margin: '8px 0 0' }}>
          업로드 실패. 다시 시도해보세요.
        </p>
      )}

      {/* 로딩 skeleton — AC-2.
          shimmer 애니메이션은 @media (prefers-reduced-motion: reduce)에서 비활성.
          CSS 클래스 방식으로 분기(globals.css 에 .shimmer 정의 필요 — T-041 범위).
          가짜 점수/preview는 로딩 중 표시하지 않는다. */}
      {uploading && (
        <div data-testid="loading-skeleton" aria-busy="true" style={{ marginTop: '12px' }}>
          <div
            className="shimmer"
            style={{
              height: '16px',
              borderRadius: '4px',
              marginBottom: '8px',
            }}
          />
          <div
            className="shimmer"
            style={{
              height: '16px',
              borderRadius: '4px',
              width: '60%',
            }}
          />
          <p style={{ color: 'var(--muted)', marginTop: '8px' }}>이력서 분석 중…</p>
        </div>
      )}

      {/* 마스킹 preview — 응답 수신 후 표시, 로딩 중에는 미표시(AC-2) */}
      {!uploading && preview && (
        <MaskingPreview maskedText={preview.maskedText} evidenceSummary={preview.evidenceSummary} />
      )}

      {/* "이 이력서로 분석 시작" — preview 수신 후 활성(T-039 클릭 핸들러 연결).
          Button.primary — DESIGN §2-3 button.primary.bg=color.accent(grape-600 CSS 변수).
          brand.gradient는 §2-4 FENCED(fit 링/로고/인사 strip만) — 버튼 사용 금지. */}
      <button
        type="button"
        data-testid="start-analysis-btn"
        disabled={!preview}
        onClick={() => void handleStartAnalysis()}
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
