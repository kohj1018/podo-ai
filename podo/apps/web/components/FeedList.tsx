'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrivalList } from './ArrivalList'
import { type FeedItem, JobCard } from './JobCard'

interface FeedPage {
  items: FeedItem[]
  nextCursor: number | null
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

// 단일 피드 — GET /api/v1/feed를 rank_position 커서로 무한 스크롤(중복제거 append).
// error/empty 상태를 일급으로 노출(REV-M2-UI-001 — 실패를 빈 목록으로 삼키지 않음).
export function FeedList() {
  const [items, setItems] = useState<FeedItem[]>([])
  const [cursor, setCursor] = useState<number | null>(-1) // 렌더용. -1=첫 페이지, null=끝
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false) // 첫 로드 완료 — empty 판별용
  const [error, setError] = useState(false)
  const cursorRef = useRef<number | null>(-1)
  const loadingRef = useRef(false)

  // cursorRef로 stable(deps []) — useEffect([loadMore])가 1회만 실행.
  const loadMore = useCallback(async () => {
    if (cursorRef.current === null || loadingRef.current) return
    loadingRef.current = true
    setLoading(true)
    setError(false)
    try {
      const res = await fetch(`${API_BASE}/api/v1/feed?cursor=${cursorRef.current}`)
      if (!res.ok) throw new Error(`feed ${res.status}`)
      const page = (await res.json()) as FeedPage
      setItems((prev) => {
        const seen = new Set(prev.map((i) => i.posting.id))
        const fresh = page.items.filter((i) => !seen.has(i.posting.id)) // 중복제거
        return [...prev, ...fresh]
      })
      cursorRef.current = page.nextCursor
      setCursor(page.nextCursor)
      setLoaded(true)
    } catch {
      setError(true) // 실패를 삼키지 않음(REV-M2-UI-001)
    } finally {
      loadingRef.current = false
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadMore()
  }, [loadMore])

  return (
    <main className="mx-auto max-w-2xl p-4">
      {/* 신규 공고 arrival 모션(stagger) + reduced-motion 분기는 ArrivalList가 담당(T-048). */}
      <ArrivalList
        items={items}
        keyOf={(item) => `${item.rank_position}-${item.posting.id}`}
        renderItem={(item) => <JobCard item={item} />}
      />

      {error ? (
        <div
          data-testid="feed-error"
          className="mt-4 text-sm"
          style={{ color: 'var(--band-1-ink)' }}
        >
          ⚠ 피드를 불러오지 못했습니다.{' '}
          <button type="button" onClick={() => void loadMore()} className="underline">
            다시 시도
          </button>
        </div>
      ) : loaded && items.length === 0 ? (
        <p data-testid="feed-empty" className="mt-4 text-sm" style={{ color: 'var(--faint)' }}>
          표시할 공고가 없습니다.
        </p>
      ) : cursor !== null ? (
        <button
          type="button"
          onClick={() => void loadMore()}
          disabled={loading}
          className="mt-4 w-full rounded-xl border py-2"
        >
          {loading ? '불러오는 중…' : '더 보기'}
        </button>
      ) : null}
    </main>
  )
}
