import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  formatOptimizationRunLabel,
  type OptimizationRunSummary,
} from '@/features/optimization/optimizationApi.ts'
import { cn } from '@/lib/utils'

type RunSwitcherProps = {
  runs: OptimizationRunSummary[]
  selectedRunId: string
  /** Optional title shown above the dropdown. */
  label?: string
  busy?: boolean
  error?: string | null
  /** Show a "New analysis" row at the bottom. */
  allowNew?: boolean
  newValue?: string
  newLabel?: string
  emptyMessage?: string
  onSelect: (runId: string) => void
  onDelete?: (runId: string) => void | Promise<void>
  onOpen?: () => void
  className?: string
  align?: 'start' | 'end'
}

export default function RunSwitcher({
  runs,
  selectedRunId,
  label,
  busy = false,
  error = null,
  allowNew = false,
  newValue = 'new',
  newLabel = 'New analysis',
  emptyMessage = 'No saved runs yet.',
  onSelect,
  onDelete,
  onOpen,
  className,
  align = 'end',
}: RunSwitcherProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const selectedRun = runs.find((row) => row.id === selectedRunId)
  const triggerLabel =
    selectedRunId === newValue
      ? newLabel
      : selectedRun
        ? formatOptimizationRunLabel(selectedRun)
        : 'Select a saved run'

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [])

  function chooseRun(id: string) {
    setMenuOpen(false)
    onSelect(id)
  }

  async function handleDelete(run: OptimizationRunSummary) {
    if (!onDelete) return
    const name = formatOptimizationRunLabel(run)
    if (!window.confirm(`Delete saved run "${name}"? This cannot be undone.`)) return
    setMenuOpen(false)
    await onDelete(run.id)
  }

  return (
    <div
      className={cn(
        'flex w-full min-w-[20rem] max-w-xl flex-col items-stretch gap-2',
        align === 'end' ? 'sm:items-end' : 'sm:items-start',
        className,
      )}
    >
      {label && (
        <p className="w-full text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {label}
        </p>
      )}
      <div ref={menuRef} className="relative w-full min-w-0">
        <Button
          type="button"
          variant="outline"
          disabled={busy}
          aria-haspopup="listbox"
          aria-expanded={menuOpen}
          className="h-9 w-full min-w-0 justify-between gap-2 px-3 font-normal"
          onClick={() => {
            setMenuOpen((open) => !open)
            if (!menuOpen) onOpen?.()
          }}
        >
          <span className="min-w-0 flex-1 truncate text-left" title={triggerLabel}>
            {triggerLabel}
          </span>
          <span className="shrink-0 text-muted-foreground">▾</span>
        </Button>
        {menuOpen && (
          <div
            role="listbox"
            className={cn(
              'absolute z-20 mt-1 max-h-72 min-w-full overflow-auto rounded-lg border border-border bg-background py-1 shadow-md',
              'w-max max-w-[min(100vw-2rem,36rem)]',
              align === 'end' ? 'right-0' : 'left-0',
            )}
          >
            {runs.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">{emptyMessage}</p>
            )}
            {runs.map((row) => {
              const rowLabel = formatOptimizationRunLabel(row)
              return (
                <div
                  key={row.id}
                  className={cn(
                    'flex items-center gap-2 px-2 hover:bg-accent',
                    row.id === selectedRunId && 'bg-accent',
                  )}
                >
                  <button
                    type="button"
                    role="option"
                    aria-selected={row.id === selectedRunId}
                    title={rowLabel}
                    className="min-w-[14rem] flex-1 truncate px-1 py-2 text-left text-sm"
                    onClick={() => chooseRun(row.id)}
                  >
                    {rowLabel}
                  </button>
                  {onDelete && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-8 shrink-0 px-2.5 whitespace-nowrap text-destructive"
                      disabled={busy}
                      onClick={(event) => {
                        event.stopPropagation()
                        void handleDelete(row)
                      }}
                    >
                      Delete
                    </Button>
                  )}
                </div>
              )
            })}
            {allowNew && (
              <button
                type="button"
                role="option"
                aria-selected={selectedRunId === newValue}
                className={cn(
                  'flex w-full border-t border-border px-3 py-2 text-left text-sm hover:bg-accent',
                  selectedRunId === newValue && 'bg-accent',
                )}
                onClick={() => chooseRun(newValue)}
              >
                {newLabel}
              </button>
            )}
          </div>
        )}
      </div>
      {error && <p className="max-w-full truncate text-xs text-destructive">{error}</p>}
    </div>
  )
}
