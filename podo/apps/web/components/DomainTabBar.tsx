'use client'

import { type KeyboardEvent, useRef, useState } from 'react'

// 직군(도메인) → 한국어 라벨. T-066 분류 어휘(ROLE_FAMILY_TO_DOMAINS) 기준.
const DOMAIN_LABELS: Record<string, string> = {
  all: '전체',
  backend: '백엔드',
  data: '데이터',
  frontend: '프론트엔드',
  web: '프론트엔드',
  fullstack: '풀스택',
  ml_ai: 'ML/AI',
  ai: 'ML/AI',
  android: '안드로이드',
  ios: 'iOS',
  mobile: '모바일',
  devops: '데브옵스',
  cloud: '클라우드',
  infra: '인프라',
  security: '보안',
}

function label(d: string): string {
  return DOMAIN_LABELS[d] ?? d
}

interface DomainTabBarProps {
  domains: string[]
  active: string
  onChange: (domain: string) => void
  confidence?: string
  isEmpty?: boolean
}

// T-067 직군 분리 탭 — 이력서 자동 분류(T-066) 기반 동적 탭. ARIA tablist + 화살표 roving focus.
// 저신뢰(confidence=low) → "직군이 섞여 있어요" 배너 + 전체 탭만(정직한 안내, F-022 FAC-3).
export function DomainTabBar({
  domains,
  active,
  onChange,
  confidence,
  isEmpty,
}: DomainTabBarProps) {
  const lowConfidence = confidence === 'low'
  // 'unknown'·중복 제거. 저신뢰면 직군 탭 숨기고 '전체'만(혼재 신호 정직 노출).
  const domainTabs = lowConfidence
    ? []
    : domains.filter((d, i) => d && d !== 'unknown' && domains.indexOf(d) === i)
  const tabs = [
    { value: 'all', label: '전체' },
    ...domainTabs.map((d) => ({ value: d, label: label(d) })),
  ]

  const activeIdx = tabs.findIndex((t) => t.value === active)
  const [focusedIdx, setFocusedIdx] = useState(activeIdx < 0 ? 0 : activeIdx)
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>): void {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') {
      return
    }
    e.preventDefault()
    const delta = e.key === 'ArrowRight' ? 1 : -1
    const next = Math.min(Math.max(focusedIdx + delta, 0), tabs.length - 1)
    setFocusedIdx(next)
    refs.current[next]?.focus()
  }

  return (
    <div className="mx-auto max-w-[430px]">
      {lowConfidence ? (
        <p
          data-testid="low-confidence-banner"
          role="note"
          className="px-3 py-1 text-sm"
          style={{ color: 'var(--faint)' }}
        >
          직군이 섞여 있어요 — 전체에서 확인해 보세요
        </p>
      ) : null}
      <div
        role="tablist"
        aria-label="직군 분리"
        onKeyDown={onKeyDown}
        className="flex gap-2 px-3 py-2 text-sm"
      >
        {tabs.map((t, i) => (
          <button
            key={t.value}
            ref={(el) => {
              refs.current[i] = el
            }}
            type="button"
            role="tab"
            aria-selected={t.value === active}
            tabIndex={i === focusedIdx ? 0 : -1}
            onClick={() => onChange(t.value)}
            className="rounded-full border px-3 py-1"
            style={{
              borderColor: t.value === active ? 'var(--band-5-ink)' : 'var(--faint)',
              fontWeight: t.value === active ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      {isEmpty ? (
        <p
          data-testid="domain-empty-state"
          className="px-3 py-4 text-sm"
          style={{ color: 'var(--faint)' }}
        >
          이 직군은 오늘 공고가 없어요
        </p>
      ) : null}
    </div>
  )
}
