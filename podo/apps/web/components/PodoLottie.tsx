'use client'

import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'
import { PodoMascot } from './PodoMascot'

// dotLottie는 클라이언트 전용(canvas/wasm) → dynamic ssr:false(DESIGN §8-1).
const DotLottieReact = dynamic(
  () => import('@lottiefiles/dotlottie-react').then((m) => m.DotLottieReact),
  { ssr: false },
)

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if (!mq) return
    setReduced(mq.matches)
    const onChange = (): void => setReduced(mq.matches)
    mq.addEventListener?.('change', onChange)
    return () => mq.removeEventListener?.('change', onChange)
  }, [])
  return reduced
}

// PodoLottie (DESIGN §8-1) — 포도 마스코트 lottie(의미 전달 한정, 장식).
// reduced-motion·미마운트·src 부재·로드 실패 → 정적 포스터(마스코트 PNG)로 graceful fallback(F-018 §10).
export function PodoLottie({ src, size = 56 }: { src?: string; size?: number }) {
  const reduced = usePrefersReducedMotion()
  const [mounted, setMounted] = useState(false)
  const [failed, setFailed] = useState(false)
  useEffect(() => setMounted(true), [])

  // 정적 포스터 — autoplay 금지 경로(reduced 등). 마스코트는 보임(무렌더 아님).
  if (reduced || !mounted || failed || !src) {
    return (
      <span data-testid="podo-lottie" data-static="true" style={{ display: 'inline-block' }}>
        <PodoMascot size={size} />
      </span>
    )
  }

  return (
    <span data-testid="podo-lottie" aria-hidden="true" style={{ display: 'inline-block' }}>
      {/* loop 금지(DESIGN §8-1/§9 — 무한 장식 루프 X): '도착' 의미 전달 1회 재생만. */}
      <DotLottieReact
        src={src}
        autoplay
        loop={false}
        style={{ width: size, height: size }}
        onError={() => setFailed(true)}
      />
    </span>
  )
}
