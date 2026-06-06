// PassBand (DESIGN §7-2) — 적합도 5단계 meter. 색만 의존 금지: 라벨 텍스트 필수(§9).
// "합격가능성" → "적합도"로 relabel(M2 명칭 결정). fit_level 1:1 직결(별도 calibration X).

const BAND_LABELS: Record<number, string> = {
  1: '매우 낮음',
  2: '낮음',
  3: '보통',
  4: '높음',
  5: '매우 높음',
}

export function PassBand({ level }: { level: number | null }) {
  // held(null) — 보류(가짜 점수 금지). 상세 보류 렌더는 T-029.
  if (level === null) {
    return (
      <span data-testid="passband" data-level="held" className="text-sm font-medium">
        적합도 보류
      </span>
    )
  }

  const label = BAND_LABELS[level] ?? '보통'
  return (
    <div data-testid="passband" data-level={level} className="flex items-center gap-2">
      <span className="text-sm font-medium" style={{ color: `var(--band-${level}-ink)` }}>
        적합도 {label}
      </span>
      <span className="flex gap-0.5" aria-hidden>
        {[1, 2, 3, 4, 5].map((seg) => (
          <span
            key={seg}
            className="h-2 w-3 rounded-full"
            style={{
              backgroundColor: `var(--band-${level}-fill)`,
              opacity: seg <= level ? 1 : 0.2,
            }}
          />
        ))}
      </span>
    </div>
  )
}
