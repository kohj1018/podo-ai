'use client'

import { type ReactNode, useEffect, useState } from 'react'

// prefers-reduced-motion JS 감지 — matchMedia 부재(jsdom 기본) 시 false(모션 on). 테스트는 stub.
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

// ArrivalList (DESIGN §8) — 신규 공고 '도착' 모션. full=fade+translateY+stagger(≤200ms),
// reduced=opacity fade(≤120ms)만(transform/stagger 제거). JS reduced-motion 분기(AC-1).
export function ArrivalList<T>({
  items,
  keyOf,
  renderItem,
}: {
  items: T[]
  keyOf: (item: T) => string | number
  renderItem: (item: T) => ReactNode
}) {
  const reduced = usePrefersReducedMotion()
  return (
    <ul className="flex flex-col gap-3">
      {items.map((item, i) => (
        <li
          key={keyOf(item)}
          data-testid="arrival-item"
          data-reduced={reduced}
          style={
            reduced
              ? { animation: 'arrival-fade 120ms ease-out both' }
              : { animation: 'arrival-rise 200ms ease-out both', animationDelay: `${i * 40}ms` }
          }
        >
          {renderItem(item)}
        </li>
      ))}
    </ul>
  )
}
