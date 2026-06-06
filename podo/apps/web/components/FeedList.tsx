'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { type FeedItem, JobCard } from './JobCard'

interface FeedPage {
  items: FeedItem[]
  nextCursor: number | null
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001'

// 단일 피드 — GET /api/v1/feed를 rank_position 커서로 무한 스크롤(중복제거 append).
export function FeedList() {
  const [items, setItems] = useState<FeedItem[]>([])
  const [cursor, setCursor] = useState<number | null>(-1) // 렌더(버튼)용. -1=첫 페이지, null=끝
  const [loading, setLoading] = useState(false)
  const cursorRef = useRef<number | null>(-1)
  const loadingRef = useRef(false)

  // cursorRef로 stable(deps []) — useEffect([loadMore])가 1회만 실행.
  const loadMore = useCallback(async () => {
    if (cursorRef.current === null || loadingRef.current) return
    loadingRef.current = true
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/feed?cursor=${cursorRef.current}`)
      const page = (await res.json()) as FeedPage
      setItems((prev) => {
        const seen = new Set(prev.map((i) => i.posting.id))
        const fresh = page.items.filter((i) => !seen.has(i.posting.id)) // 중복제거
        return [...prev, ...fresh]
      })
      cursorRef.current = page.nextCursor
      setCursor(page.nextCursor)
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
      <ul className="flex flex-col gap-3">
        {items.map((item) => (
          <li key={`${item.rank_position}-${item.posting.id}`}>
            <JobCard item={item} />
          </li>
        ))}
      </ul>
      {cursor !== null ? (
        <button
          type="button"
          onClick={() => void loadMore()}
          disabled={loading}
          className="mt-4 w-full rounded-xl border py-2"
        >
          더 보기
        </button>
      ) : null}
    </main>
  )
}
