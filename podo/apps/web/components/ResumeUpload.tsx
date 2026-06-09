'use client'

import { useRef, useState } from 'react'
import { MaskingPreview } from './MaskingPreview'
import { ResumeForm } from './ResumeForm'

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

type Mode = 'file' | 'form'

// 허용 확장자 목록
const ALLOWED_EXTENSIONS = ['.txt', '.md']
// 클라이언트 사이드 파일 크기 상한: 100KB
const MAX_FILE_SIZE = 100 * 1024

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

// /resume 입력 — 두 모드(T-095 §2-C): ① 파일 업로드(.txt/.md) ② 직접 작성 폼(항목→표준 헤딩 마크다운).
// 두 모드 모두 *기존* 단일 blob 흐름(POST /api/v1/resumes)에 태운다 — 알고리즘·스키마 무변경(§2-H).
// 업로드 후 T-034 응답(masked_preview + evidence_summary)을 MaskingPreview에 전달 → "분석 시작"(T-039).
export function ResumeUpload({ onNavigateFeed }: { onNavigateFeed?: (path: string) => void } = {}) {
  const [mode, setMode] = useState<Mode>('file')
  const [preview, setPreview] = useState<PreviewState | null>(null)
  const [uploading, setUploading] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState(false)
  const [scoreError, setScoreError] = useState(false) // 채점 트리거 실패(T-096 AC-3)
  const [scoring, setScoring] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  // 이미 채점한 resume_id — 동일 이력서 재제출 시 중복 채점 방지(T-096 AC-1 "정확히 1회").
  const scoredRef = useRef<number | null>(null)

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

  // 공통 제출 — 파일(FormData) 또는 텍스트({text} JSON) 모두 기존 POST /api/v1/resumes 경로.
  async function submitResume(payload: { file: File } | { text: string }) {
    setUploadError(false)
    setScoreError(false) // 새 제출 시 이전 채점 실패 메시지 잔류 제거(QA-M7-005)
    setUploading(true)
    try {
      let res: Response
      if ('file' in payload) {
        const form = new FormData()
        form.append('file', payload.file)
        res = await fetch(`${API_BASE}/api/v1/resumes`, {
          method: 'POST',
          body: form,
          credentials: 'include', // 세션 쿠키 전송(소유자 user_id 결선 + SessionGuard)
        })
      } else {
        res = await fetch(`${API_BASE}/api/v1/resumes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: payload.text }),
          credentials: 'include',
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

  function handleFileUpload() {
    const file = fileInputRef.current?.files?.[0]
    if (!file) return
    void submitResume({ file })
  }

  // T-039/T-096: 신규·수정 제출 시에만 score 트리거(피드 탐색은 미트리거) → active 교체 → feed 이동.
  // 해석 확정(§8): POST /api/v1/resumes/:id/score (T-037 확정 트리거). append-only — 매 업로드가 새 resume_id.
  function navigateToFeed() {
    if (onNavigateFeed) onNavigateFeed('/')
    else window.location.assign('/')
  }

  async function handleStartAnalysis() {
    if (!preview || scoring) return
    const { resumeId } = preview

    // 동일 이력서 이미 채점됨 → 중복 채점 스킵, active 교체·이동만(T-096 AC-1 "정확히 1회").
    if (scoredRef.current === resumeId) {
      localStorage.setItem('podo_active_resume_id', String(resumeId))
      navigateToFeed()
      return
    }

    setScoreError(false)
    setScoring(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/resumes/${resumeId}/score`, {
        method: 'POST',
        credentials: 'include',
      })
      // res.ok 미검사 후 무조건 이동(회귀) 차단 — 실패 시 미이동 + 에러/재시도(T-096 AC-3).
      if (!res.ok) {
        setScoreError(true)
        return
      }
    } catch {
      setScoreError(true)
      return
    } finally {
      setScoring(false)
    }
    scoredRef.current = resumeId
    localStorage.setItem('podo_active_resume_id', String(resumeId))
    navigateToFeed()
  }

  function tabStyle(active: boolean): React.CSSProperties {
    return {
      flex: 1,
      padding: '8px 12px',
      borderRadius: '12px',
      border: active ? '1px solid var(--grape-600)' : '1px solid var(--line-strong)',
      background: active ? 'var(--grape-100)' : 'var(--surface)',
      color: active ? 'var(--grape-700)' : 'var(--muted)',
      fontWeight: active ? 700 : 500,
      cursor: 'pointer',
    }
  }

  return (
    <div>
      {/* 모드 토글 — 파일 업로드 / 직접 작성(T-095). */}
      <div
        role="tablist"
        aria-label="이력서 입력 방식"
        style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}
      >
        <button
          type="button"
          role="tab"
          data-testid="mode-file"
          aria-selected={mode === 'file'}
          onClick={() => setMode('file')}
          style={tabStyle(mode === 'file')}
        >
          파일 업로드
        </button>
        <button
          type="button"
          role="tab"
          data-testid="mode-form"
          aria-selected={mode === 'form'}
          onClick={() => setMode('form')}
          style={tabStyle(mode === 'form')}
        >
          직접 작성
        </button>
      </div>

      {/* 편집 안내(T-096) — content는 마스킹본이라 원문 prefill 불가. 새로 작성/업로드 = 기존 이력서 교체. */}
      <p
        data-testid="edit-guidance"
        style={{ color: 'var(--muted)', margin: '0 0 16px', fontSize: '13px' }}
      >
        새로 작성하거나 업로드하면 기존 이력서를 교체하고 다시 분석해요.
      </p>

      {mode === 'file' ? (
        <div>
          {/* 파일 입력 — .txt/.md only. label 연결(a11y). 드롭존 안내 UI. */}
          <label
            htmlFor="resume-file-input"
            style={{ display: 'block', marginBottom: '8px', fontWeight: 600, color: 'var(--ink)' }}
          >
            이력서 파일 (.txt / .md)
          </label>
          <div
            style={{
              border: '1px dashed var(--line-strong)',
              borderRadius: '16px',
              padding: '20px 16px',
              background: 'var(--surface)',
              marginBottom: '8px',
            }}
          >
            <input
              id="resume-file-input"
              ref={fileInputRef}
              data-testid="file-input"
              type="file"
              accept=".txt,.md"
              aria-label="이력서 파일 업로드"
              onChange={handleFileChange}
              style={{ display: 'block' }}
            />
            <p style={{ color: 'var(--muted)', margin: '8px 0 0', fontSize: '13px' }}>
              .txt 또는 .md 파일을 선택하세요 (최대 100KB).
            </p>
          </div>

          {/* 포맷/크기 안내 메시지 — AC-1 */}
          {fileError && (
            <p data-testid="format-error" style={{ color: 'var(--band-1-ink)', margin: '0 0 8px' }}>
              {fileError}
            </p>
          )}

          <button
            type="button"
            onClick={handleFileUpload}
            disabled={uploading}
            style={{
              padding: '8px 16px',
              borderRadius: '12px',
              border: '1px solid var(--line-strong)',
              background: 'var(--surface)',
              color: 'var(--grape-700)',
              cursor: uploading ? 'not-allowed' : 'pointer',
            }}
          >
            업로드
          </button>
        </div>
      ) : (
        // 직접 작성 폼 — 제출 시 표준 헤딩 마크다운 조립 → {text} POST(기존 경로).
        <ResumeForm
          onSubmit={(markdown) => void submitResume({ text: markdown })}
          disabled={uploading}
        />
      )}

      {/* 에러 toast — 업로드 실패 */}
      {uploadError && (
        <p data-testid="upload-error" style={{ color: 'var(--band-1-ink)', margin: '8px 0 0' }}>
          업로드 실패. 다시 시도해보세요.
        </p>
      )}

      {/* 로딩 skeleton — 가짜 점수/preview 미표시. shimmer는 reduced-motion에서 정적(globals.css). */}
      {uploading && (
        <div data-testid="loading-skeleton" aria-busy="true" style={{ marginTop: '12px' }}>
          <div
            className="shimmer"
            style={{ height: '16px', borderRadius: '4px', marginBottom: '8px' }}
          />
          <div className="shimmer" style={{ height: '16px', borderRadius: '4px', width: '60%' }} />
          <p style={{ color: 'var(--muted)', marginTop: '8px' }}>이력서 분석 중…</p>
        </div>
      )}

      {/* 마스킹 preview — 응답 수신 후 표시, 로딩 중에는 미표시 */}
      {!uploading && preview && (
        <MaskingPreview maskedText={preview.maskedText} evidenceSummary={preview.evidenceSummary} />
      )}

      {/* "이 이력서로 분석 시작" — preview 수신 후 활성(T-039 클릭 핸들러). primary CTA 1개. */}
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

      {/* 채점 트리거 실패 — 피드 미이동 + 재시도 안내(T-096 AC-3). */}
      {scoreError && (
        <p
          data-testid="score-error"
          role="alert"
          style={{ color: 'var(--band-1-ink)', margin: '8px 0 0' }}
        >
          분석 요청에 실패했어요. 위 버튼으로 다시 시도해주세요.
        </p>
      )}
    </div>
  )
}
