'use client'

import { useRef, useState } from 'react'
import { Toast } from './Toast'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

type Action = 'applied' | 'skipped' | 'favorite' | 'unskip'

const FAIL_MSG = '기록에 실패했어요. 다시 시도해주세요.'

// JobCardActions (DESIGN §7) — 지원/스킵/즐겨찾기 액션 + Toast(role=status). 기록은 T-050 API.
// 낙관적 정리(onProcessed) + 실패 롤백(onRestore). 지원 = 원본 채널 링크 새 탭(자동지원 아님, Charter §5).
export function JobCardActions({
  jobId,
  url,
  onProcessed,
  onRestore,
}: {
  jobId: number
  url?: string
  onProcessed?: (jobId: number) => void
  onRestore?: (jobId: number) => void
}) {
  // toast를 {text, seq}로 — 동일 메시지 연속 알림도 seq 변경으로 재렌더 + Toast key 재마운트해
  // auto-dismiss 후 동일 메시지가 다시 뜬다(QA-M7-003: 연속 동일 실패 시 두 번째 toast 누락 회귀 차단).
  const [toast, setToast] = useState<{ text: string; seq: number } | null>(null)
  const seqRef = useRef(0)
  function notify(text: string) {
    seqRef.current += 1
    setToast({ text, seq: seqRef.current })
  }
  const [skipped, setSkipped] = useState(false)
  const [applied, setApplied] = useState(false)
  const [busy, setBusy] = useState(false)

  async function record(action: Action): Promise<boolean> {
    setBusy(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/applications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ job_posting_id: jobId, action }),
      })
      return res.ok
    } catch {
      return false
    } finally {
      setBusy(false)
    }
  }

  // 지원하기는 공고를 피드에서 제거하지 않는다(사용자 결정) — 원본 채널로 이동 + 기록 + "지원함" 표시만.
  // 서버엔 applied로 기록되므로 다음 피드 로드에선 정리됨(CLEARED_ACTIONS). 실패해도 카드 유지(복원 불필요).
  async function apply() {
    if (url) window.open(url, '_blank', 'noopener') // 원본 채널 이동(자동지원 아님)
    const ok = await record('applied')
    if (ok) {
      setApplied(true)
      notify('지원 기록됐어요')
    } else {
      notify(FAIL_MSG)
    }
  }

  async function toggleSkip() {
    const next = !skipped
    setSkipped(next) // 낙관적 토글
    const ok = await record(next ? 'skipped' : 'unskip')
    if (!ok) {
      setSkipped(!next) // 롤백
      notify(FAIL_MSG)
      return
    }
    if (next) {
      onProcessed?.(jobId)
      notify('스킵했어요')
    } else {
      onRestore?.(jobId)
      notify('되돌렸어요')
    }
  }

  async function favorite() {
    const ok = await record('favorite')
    notify(ok ? '즐겨찾기에 담았어요' : FAIL_MSG)
  }

  const btn = {
    padding: '6px 12px',
    borderRadius: '12px',
    border: '1px solid var(--line-strong)',
    background: 'var(--surface)',
    color: 'var(--ink)',
    cursor: 'pointer',
  } as const

  return (
    <div className="mt-3 flex items-center gap-2">
      <button
        type="button"
        data-testid="action-apply"
        disabled={busy || applied}
        onClick={() => void apply()}
        style={{
          ...btn,
          background: applied ? 'var(--coverage-on-bg)' : 'var(--grape-600)',
          color: applied ? 'var(--band-5-ink)' : 'var(--surface)',
          border: 'none',
          cursor: applied ? 'default' : 'pointer',
        }}
      >
        {applied ? '지원함 ✓' : '지원하기'}
      </button>
      <button
        type="button"
        data-testid="action-skip"
        disabled={busy}
        onClick={() => void toggleSkip()}
        style={btn}
      >
        {skipped ? '되돌리기' : '스킵'}
      </button>
      <button
        type="button"
        data-testid="action-favorite"
        disabled={busy}
        onClick={() => void favorite()}
        style={btn}
      >
        즐겨찾기
      </button>
      {/* 공용 Toast(role=status, aria-live=polite) — 인라인 markup 대체(T-100). key=seq로 동일 메시지 재노출. */}
      <Toast key={toast?.seq} message={toast?.text ?? null} testId="action-toast" />
    </div>
  )
}
