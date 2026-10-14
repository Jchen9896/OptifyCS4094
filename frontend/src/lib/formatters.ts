/** Format a decimal return or rate as a percent string. */
export function formatPercent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`
}

/** Format an optimizer weight (0-1) as a percent string. */
export function formatWeight(value: number, digits = 1): string {
  return formatPercent(value, digits)
}
