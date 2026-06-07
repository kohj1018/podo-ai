// DeadlineRow (DESIGN §7-2) — 마감 D-day. D-1 이하 긴급(danger)·D-7 이하 주의(warning).
// 색만 의존 금지: 항상 텍스트 라벨 동반. raw hex 0(토큰만).
export function DeadlineRow({ daysLeft }: { daysLeft: number }) {
  const urgent = daysLeft <= 1
  const soon = daysLeft <= 7
  const color = urgent ? 'var(--band-1-ink)' : soon ? 'var(--band-2-ink)' : 'var(--muted)'
  const label =
    daysLeft < 0
      ? '마감됨'
      : daysLeft === 0
        ? '오늘 마감'
        : urgent
          ? `마감 D-${daysLeft} 긴급`
          : `마감 D-${daysLeft}`

  return (
    <p data-testid="deadline-row" className="mt-1 text-sm" style={{ color }}>
      {label}
    </p>
  )
}
