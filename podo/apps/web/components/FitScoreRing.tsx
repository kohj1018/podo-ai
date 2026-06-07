// FitScoreRing (DESIGN §7-2) — fit 배지. arc = brand.gradient(FENCED §2-4 — fit 링만 허용).
// 합격확률/% 금지: fit_level 숫자만 표시(없으면 "—"). raw hex 0(토큰만).
// indeterminate(채점 중): 숫자 대신 분석 표시 — 가짜 점수 금지. reduced-motion은 globals.css.

export function FitScoreRing({
  level,
  indeterminate = false,
}: {
  level: number | null
  indeterminate?: boolean
}) {
  if (indeterminate) {
    return (
      <div
        data-testid="fitring"
        aria-label="분석 중"
        aria-busy="true"
        className="shimmer flex h-12 w-12 shrink-0 items-center justify-center rounded-full"
        style={{ color: 'var(--muted)' }}
      >
        <span className="text-xs">분석</span>
      </div>
    )
  }
  return (
    <div
      data-testid="fitring"
      aria-label={level === null ? '적합도 보류' : `적합도 ${level}/5`}
      className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full"
      style={{ background: 'var(--brand-gradient)' }}
    >
      <span className="text-lg font-bold" style={{ color: 'var(--paper)' }}>
        {level ?? '—'}
      </span>
    </div>
  )
}
