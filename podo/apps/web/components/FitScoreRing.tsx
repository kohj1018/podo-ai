// FitScoreRing (DESIGN §7-2) — fit 배지. arc = brand.gradient(FENCED §2-4 — fit 링만 허용).
// 합격확률/% 금지: fit_level 숫자만 표시(없으면 "—").

export function FitScoreRing({ level }: { level: number | null }) {
  return (
    <div
      data-testid="fitring"
      className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full"
      style={{ background: 'var(--brand-gradient)' }}
    >
      <span className="text-lg font-bold" style={{ color: 'var(--paper)' }}>
        {level ?? '—'}
      </span>
    </div>
  )
}
